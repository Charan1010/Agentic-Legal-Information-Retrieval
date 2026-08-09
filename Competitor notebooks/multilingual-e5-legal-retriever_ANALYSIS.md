# Competitor Notebook Analysis: multilingual-e5-legal-retriever.ipynb

# EASY-TO-UNDERSTAND BREAKDOWN

---

## What Is This Notebook Doing? (The Big Picture)

This is a competitor's solution to our same Kaggle competition: **Swiss Legal Citation Retrieval**.

**The task**: Given a legal query (a paragraph from a court decision), predict which law articles and court cases are being cited.

**Their approach in one sentence**: They use an embedding model (BGE-M3) to find similar passages, then stack **8+ layers of rules, statistics, and a machine learning reranker** on top to improve the results.

**Their best leaderboard score**: ~0.10249

**Key philosophy**: They do NOT use any LLM (no Mistral, no GPT). Everything is embeddings + statistics + regex rules + a small tree-based ML model. It's a **"feature engineering heavy"** approach.

---

## Step-by-Step: How Their Pipeline Works

Think of it like a funnel with many filters:

```
QUERY (e.g., "The court must consider Art. 221 Abs. 1 StPO regarding detention...")
    │
    ▼
[Step 1] Shrink the search space (only look at citations that appeared in training data)
    │
    ▼
[Step 2] Use BGE-M3 embeddings to find top 150 similar passages
    │
    ▼
[Step 3] Add scores from 6+ different "feature" signals (TF-IDF, regex, frequency, etc.)
    │
    ▼
[Step 4] Boost exact citation matches found in the query text via regex
    │
    ▼
[Step 5] Expand: add law articles from full database that weren't in Step 1
    │
    ▼
[Step 6] Rescue: add back high-confidence citations that might have been missed
    │
    ▼
[Step 7] LightGBM reranker: ML model learns which candidates are correct
    │
    ▼
[Step 8] Safe tail replacement: only fix the last few positions in the output
    │
    ▼
FINAL OUTPUT: Top 25 predicted citations
```

---

## Detailed Explanation of Each Step

---

### STEP 1: Smart Corpus Filtering ("Gold-Core" Trick)

**What it does**: Instead of encoding ALL passages from the database (which would be huge and slow), they ONLY encode passages whose citations appeared in the training/validation gold labels.

**Why this is smart**:
- The full `laws_de.csv` has thousands of law articles
- But the training data only references maybe ~2000 unique citations
- By only encoding those ~2000, FAISS search is much faster and uses less GPU memory
- Most test queries will reference the same citations anyway

**The trade-off**: What about citations that NEVER appeared in training? They solve this later in Step 5 (law expansion).

**Code logic**:
```python
# Collect all citations that appear in training/validation answers
all_citations = set()
for df in [train, val]:
    for s in df["gold_citations"]:
        all_citations.update(split_citations(s))

# Only keep laws/court passages that match these citations
laws = laws_all[laws_all["citation"].isin(all_citations)]
court = court_all[court_all["citation"].isin(all_citations)]
corpus = concat([laws, court])  # This is the "gold-core" corpus
```

---

### STEP 2: BGE-M3 Embedding Search (The Core Engine)

**What is BGE-M3?**
- A multilingual embedding model from Beijing Academy of AI (BAAI)
- It's similar to our Qwen3-Embedding but designed specifically for multilingual tasks
- Special feature: it produces BOTH dense vectors AND sparse (keyword-like) scores at the same time

**How retrieval works**:

1. **Encode all corpus passages** → get a 1024-dim dense vector + sparse word weights for each
2. **Build a FAISS index** from the dense vectors (cosine similarity via normalized inner product)
3. **For each query**:
   - Encode query → get dense vector + sparse weights
   - Search FAISS for top 150 most similar passages (by dense cosine)
   - For those 150 candidates, also compute a **sparse/lexical score** (keyword overlap)
   - Final score = **80% dense similarity + 20% lexical similarity**
   - Return top K by final score

**Why both dense + sparse?**
- Dense catches semantic meaning ("detention requirements" matches "conditions for arrest")
- Sparse catches exact keywords ("Art. 221" matches "Art. 221" — embeddings might confuse 221 vs 222)

**Important settings**:
- Documents encoded with max 1024 tokens
- Queries encoded with max 512 tokens
- Batch size 32, chunks of 2000 docs at a time

---

### STEP 3: Feature Engineering Layer (The "Secret Sauce")

This is where they add **6 different signals** on top of the BGE retrieval. Each signal gives every candidate citation a score, and they're all combined with different weights.

#### Signal A: Regex Direct Extraction (Weight: 10.0 — HIGHEST)

**What it does**: Use regex patterns to literally parse citation references from the query text.

**Example**: If the query says "gemäss Art. 221 Abs. 1 StPO", the regex extracts:
- Article number: 221
- Paragraph (Absatz): 1  
- Law code: StPO

Then it looks up `"Art. 221 Abs. 1 StPO"` in the corpus. If it exists → massive score boost.

**Why weight 10.0?** Because if the query literally mentions a citation, that citation is almost certainly in the gold answer. This is the strongest signal.

#### Signal B: Abbreviation Expansion (Weight: 3.0)

**What it does**: Swiss law uses German AND French abbreviations for the same law. For example:
- French "CO" = German "OR" (Code des Obligations = Obligationenrecht)
- French "LAI" = German "IVG" (Loi sur l'assurance-invalidité = Invalidenversicherungsgesetz)

They maintain a translation table and normalize all abbreviations to German before matching.

Then for each law code found in the query, they retrieve the top 25 articles from that law, ranked by how often they co-occur with the directly-extracted citations.

#### Signal C: Domain Keyword Mapping (Weight: 1.5)

**What it does**: A hand-built dictionary mapping legal topics to law codes.

```python
DOMAIN_KW = {
    "testament": ["ZGB", "IPRG"],     # inheritance law
    "divorce": ["ZGB", "ZPO", "IPRG"], # family law
    "accident": ["UVG", "ATSG", "SVG"], # insurance law
    "criminal": ["StGB", "StPO", "BGG"], # criminal law
    "tax": ["DBG", "MWSTG", "VStG"],   # tax law
    "asylum": ["AsylG", "AIG", "VwVG"], # asylum law
    ...
}
```

If the query mentions "accident", it adds articles from UVG, ATSG, SVG with a small boost.

#### Signal D: Query-to-Query Transfer (Weight: 1.5)

**THIS IS ONE OF THEIR BEST IDEAS.**

**The intuition**: If a test query is very similar to a training query, they probably have similar gold citations.

**How it works**:
1. Build TF-IDF vectors for ALL queries (train + val + test) using:
   - Word-level TF-IDF (1-2 grams, 80K features)
   - Character-level TF-IDF (3-5 char n-grams, 60K features)
2. For each test query, find the top 50 most similar training queries
3. Collect all gold citations from those similar training queries
4. Score each citation by: `sum(similarity² for each training query that has this citation)`

**Example**:
- Test query: "The defendant's detention under Art. 221 StPO must be reviewed..."
- Most similar training query: "Review of detention conditions under Art. 221 Abs. 1 StPO..."
- That training query's gold citations: ["Art. 221 Abs. 1 StPO", "Art. 227 StPO", ...]
- → Those citations get boosted for the test query

**Why this works**: Legal queries about the same topic tend to cite the same articles. This is like a nearest-neighbor approach using the training data as a lookup table.

#### Signal E: Law Document TF-IDF (Weight: 3.5)

**What it does**: Builds a TF-IDF index over ALL law article texts (not just gold-core). For each query, retrieves the top 50 most text-similar law articles.

This is like BM25 but using scikit-learn's TF-IDF + cosine similarity. It helps find articles that have similar wording to the query even if the embedding model missed them.

#### Signal F: Court Document TF-IDF (Weight: 2.8)

Same as Signal E but for court consideration passages. Retrieves top 50 similar court texts.

#### How Signals are Combined:

```python
# Each signal adds to a running score for each candidate citation
score_map = {}
add(bge_results, weight=1.00)          # Step 2 results
add(regex_hits, weight=10.0)           # Signal A
add(abbreviation_expansion, weight=3.0) # Signal B
add(domain_keywords, weight=1.5)       # Signal C
add(query_transfer, weight=1.5)        # Signal D
add(law_tfidf_hits, weight=3.5)        # Signal E
add(court_tfidf_hits, weight=2.8)      # Signal F
add(global_frequency, weight=0.03)     # How popular each citation is overall
add(co_citation_expansion, weight=small) # Citations that often appear together
```

Final output: top 100-180 candidates sorted by combined score.

---

### STEP 4: Citation Rule Boost

**Problem**: Even after Step 3, the model might rank "Art. 222 StPO" above "Art. 221 StPO" because their embeddings are nearly identical.

**Solution**: If the query explicitly mentions "Art. 221", give that citation a HARD numerical boost that's difficult to overcome.

**Boost levels** (graduated — more specific = bigger boost):
| Match Type | Boost | Example |
|-----------|-------|---------|
| Exact art + paragraph + law | +1.25 | Query says "Art. 221 Abs. 1 StPO" → candidate IS "Art. 221 Abs. 1 StPO" |
| Same art + paragraph + law | +0.85 | Query says "Art. 221 Abs. 1 StPO" → candidate is "Art. 221 Abs. 2 StPO" |
| Same art + law (any paragraph) | +0.55 | Query says "Art. 221 StPO" → candidate is any "Art. 221 ... StPO" |
| Just same law code | +0.05 | Query mentions "StPO" → candidate is from StPO |

**Also**: A soft boost for candidates already in the pool — if the candidate's article number or law code appears anywhere in the query text, give +0.12 to +0.25.

---

### STEP 5: Query-Aware Law Expansion

**Problem**: Step 1 filtered the corpus to only gold-core citations. But what about law articles that exist in `laws_de.csv` but never appeared in training data? The test set might reference them!

**Solution**: For each query, dynamically add relevant articles from the FULL `laws_de` database:

- **Exact match** (same article + law from query): +1.05
- **Same article, different paragraph**: +0.78
- **Sibling articles** (±3 articles away in the same law): +0.22 (decays with distance)
  - e.g., if query mentions Art. 221 StPO, also consider Art. 220 and Art. 222
- **Domain prior** (law code detected from query keywords): +0.025

**For court cases**: Only add exact case IDs that are literally mentioned in the query text (conservative — courts are noisy).

---

### STEP 6: Conservative Citation Rescue + Safe Tail Replacement

**The philosophy**: "Don't break what's already working. Only fix the tail."

#### Part A: Conservative Rescue (v4-safe)

Rules for this layer:
- NO broad semantic expansion (don't add random related articles)
- NO multi-query dense retrieval (don't re-run BGE with modified queries)
- ONLY use explicit citation signals already in the query

It adds a small set of high-confidence candidates that the previous steps might have ranked too low.

#### Part B: Safe Tail Replacement (v5/v6)

**Key insight**: The top 20 predictions are usually good. It's the last 5 positions (positions 21-25) that are the weakest and most improvable.

**How it works**:
1. **Protect the head**: Keep positions 1-20 (or 1-21) exactly as they are
2. **Replace the tail**: Only modify positions 21-25 with "rescue" candidates
3. **Only fire when confident**: Only replaces tail when the query has explicit citation patterns

**v6 additions**:
- If query says "Abs. 1" and candidate has "Abs. 2" → PENALIZE (-0.50)
- Adjacent articles (±1) can enter tail only with high confidence
- Co-citation from the protected head: if your top-10 predictions often co-occur with citation X, add X to tail
- Restrict tail candidates to only the same law codes as the head (don't introduce random new laws)

---

### STEP 7: LightGBM Reranker (Machine Learning Layer)

**What is LightGBM?** A gradient-boosted tree model (like XGBoost). Very fast, works on tabular features.

**The idea**: Use Steps 1-6 as a **candidate generator** (produce top 180 candidates per query), then train a binary classifier: "Is this candidate citation correct (1) or not (0)?"

**Features fed to LightGBM** (for each query-candidate pair):

| Feature | What it means |
|---------|---------------|
| `rank` | Position in the Step 1-6 output (lower = was ranked higher) |
| `rank_score` | 1/(rank+1) — smooth version of rank |
| `is_top25` | Was this in the top 25 before reranking? |
| `same_law` | Does the candidate's law code appear in the query? |
| `same_article` | Does the candidate's article number match one in the query? |
| `same_abs` | Does the candidate's paragraph number match one in the query? |
| `wrong_abs` | Same article but DIFFERENT paragraph (bad signal!) |
| `adjacent_article` | Article number is ±1 from a query article |
| `query_has_case` | Does the query mention a court case ID? |
| `transfer_score` | From Signal D: how much do similar training queries cite this? |
| `transfer_hit_count` | How many similar training queries cite this? |
| `transfer_best_sim` | Highest similarity among training queries that cite this |
| `cocit_score` | Co-citation graph: how often does this appear alongside our other candidates? |
| `freq_score` | How often does this citation appear in ALL training answers? |

**Training setup**:
- Trained on training set gold labels
- Validated on validation set
- 650 trees, learning rate 0.03, max depth 5
- Balanced class weights (because most candidates are negatives)

**Why this helps**: The model learns dataset-specific patterns like:
- "If a candidate is in the top 5 AND matches the query law code, it's almost always correct"
- "If a candidate has wrong_abs=1, it's probably wrong even if ranked high"
- "If transfer_score > 0.8 and transfer_hit_count >= 3, it's very likely correct"

---

### STEP 8: Law Family Rescue (Final Touch)

**What it does**: Hard-coded "family groups" of related law articles.

Example families:
```python
ZGB Art. 965 → related to: ZGB Art. 656, 216, 839, 973, 968
IPRG Art. 86 → related to: IPRG Art. 17, 18, 90, 63
```

If the top predictions include an article from a known family, check if any of its family members should also be included. Only modifies the very last position (1 slot).

Also uses dynamic co-citation: if the top-8 predictions frequently co-occur with citation X in training data, add X.

---

## What Makes This Approach Different From Ours

| | Their Approach | Our Approach |
|---|---|---|
| **Brain** | No LLM — purely statistics + rules | Mistral-7B reasons about the query |
| **Embedding** | BGE-M3 (dense + sparse in one model) | Qwen3-Embedding-0.6B |
| **Reranker** | LightGBM (tabular tree model) | Qwen3-Reranker-0.6B (neural cross-encoder) |
| **Search** | FAISS only (sparse is from BGE-M3) | FAISS + BM25 (separate systems) |
| **Citation matching** | Heavy regex parsing + graduated boosts | Metadata filtering |
| **Expansion** | Statistical (co-citation, frequency, sibling) | LLM-driven multi-hop reasoning |
| **Corpus strategy** | Only encode gold-core (fast, small) | Encode everything (slower, complete) |
| **Post-processing** | 3 layers of tail repair + parameter sweep | None |

---

## The 5 Best Ideas We Should Steal

### Idea 1: Query-to-Query Transfer (EASIEST WIN)

**What**: Find training queries similar to our test query, then steal their gold citations.

**Why it works**: Legal queries about the same topic cite the same articles. A training query about "detention review under StPO" will have the same gold citations as a test query about the same topic.

**How to implement in our pipeline**:
```
1. Pre-compute embeddings for all training queries (using our Qwen3-Embedding)
2. For each test query, find top 20 most similar training queries
3. Collect their gold citations
4. Add those citations to our candidate pool with a boosted score
```

**Cost**: Zero additional GPU at inference time (pre-computed). Just a FAISS search over ~200 training queries.

---

### Idea 2: Citation Regex Parsing + Hard Boost (FREE PRECISION)

**What**: If the query literally says "Art. 221 Abs. 1 StPO", parse that with regex and give that exact citation an enormous score boost.

**Why it works**: Embedding models are bad at distinguishing "Art. 221" from "Art. 222" — they're 99% similar in embedding space. But if the query SAYS "221", then 221 is the answer, not 222. Regex is 100% reliable here.

**How to implement**:
```python
# Simple version:
pattern = r"Art\.\s*(\d+[a-z]*)\s*(?:Abs\.\s*(\d+))?\s*([A-Z]{2,10})"
matches = re.findall(pattern, query)
for art, abs, law in matches:
    candidate = f"Art. {art} Abs. {abs} {law}" if abs else f"Art. {art} {law}"
    if candidate in our_corpus:
        score_map[candidate] += 5.0  # Big boost
```

---

### Idea 3: Co-Citation Expansion (CHEAP RECALL)

**What**: Build a matrix: "when citation A appears in a training answer, citation B also appears X times." At inference, if your predictions include A, add B as a candidate.

**Example**: In training data, "Art. 221 Abs. 1 StPO" and "Art. 227 StPO" always appear together. So if you find Art. 221, also predict Art. 227.

**How to implement**:
```python
# Build co-occurrence matrix from training gold labels
co_occur = defaultdict(Counter)
for gold_list in train["gold_citations"]:
    citations = gold_list.split(";")
    for a in citations:
        for b in citations:
            if a != b:
                co_occur[a][b] += 1

# At inference: expand from top predictions
for top_prediction in my_top_10:
    for neighbor, count in co_occur[top_prediction].most_common(5):
        score_map[neighbor] += 0.3 * min(count / 5, 1.0)
```

---

### Idea 4: Safe Tail Replacement (CONSERVATIVE POST-PROCESSING)

**What**: After your pipeline produces 25 predictions, ONLY modify the last 3-5 positions. Never touch positions 1-20.

**Why it works**: Your top predictions are usually correct (high precision). The tail is where you lose F1 (low recall). By replacing weak tail items with high-confidence rescue candidates, you can only improve.

**How to implement**:
```python
def safe_tail_replace(predictions, rescue_candidates, keep_top=20, add_n=5):
    head = predictions[:keep_top]  # NEVER TOUCH THESE
    
    # Only add rescue candidates that are high confidence
    rescue = [c for c in rescue_candidates if c not in head and confidence(c) > 0.6]
    
    return head + rescue[:add_n]  # Replace tail with rescue items
```

---

### Idea 5: LightGBM on Top of Everything (LEARN PATTERNS)

**What**: After your pipeline produces candidates with scores, train a tiny ML model to learn which candidates are actually correct based on tabular features.

**Why it works**: It can learn non-obvious patterns like "candidates with high transfer_score AND same_law are 10x more likely to be correct" — something hard to hand-tune with weights.

**Cost**: LightGBM trains in seconds and infers in milliseconds. Nearly free.

---

## Summary Table: What Each Step Contributes

| Step | What it adds | Rough contribution |
|------|-------------|-------------------|
| BGE-M3 dense+sparse | Semantic understanding | The base (~60% of correct predictions) |
| Feature engineering | Statistical patterns | +15-20% recall improvement |
| Citation regex boost | Exact citation matching | +5-10% precision improvement |
| Law expansion | Missing citations recovery | +5% recall for unseen citations |
| LightGBM reranker | Learns dataset patterns | +3-5% F1 improvement |
| Tail replacement | Conservative recall fix | +1-2% F1 on edge cases |

---

## Weaknesses of This Approach (Where WE Can Beat Them)

1. **No understanding of legal reasoning** — They can't understand WHY a citation is relevant, only that it statistically co-occurs. Our LLM can actually read and reason.

2. **Regex-dependent** — If a query doesn't explicitly mention "Art. 221 StPO" (e.g., it just says "the detention provision"), their boost layers don't fire. Our LLM can infer this.

3. **Overfitting to training patterns** — They use val labels for feature building, then test on val. Their real-world performance might be lower.

4. **No multi-hop reasoning** — If finding citation A requires first understanding citation B, they can't do it. Our Planner-Director can.

5. **Hard-coded law families** — Their final rescue layer has literally hard-coded article groups. Won't generalize to novel legal areas.
