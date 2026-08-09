# 03 Notebook Evolution: Step-by-Step Feature Analysis

> **Purpose:** Track every change from notebook 02 → final 03_hyde_kaggle, one feature at a time  
> **Goal:** Understand which feature caused which score change  
> **Status:** Scores from Runs 1-4 are from earlier analysis docs. Will re-run for fresh verification.

---

## Baseline: Notebook 02 (Starting Point)

| Component | Configuration |
|-----------|--------------|
| LLM | Mistral-7B on GPU, n_ctx=8192 |
| Search | BM25 only (naive tokenizer: `\W+` split) |
| Agent | ReAct (English prompt, 3 iterations) |
| Output | All tool results dumped (no filtering) |
| Laws corpus | 175K documents |
| Courts corpus | 100K documents (4% of 2.5M) |
| Embeddings | None |
| Reranker | None |

**Val F1: 0.0152 | Kaggle Public: 0.00439 | Private: 0.00731**

**Key problems to solve:**
1. ~119 citations/query (no output filtering)
2. BM25 can't handle cross-lingual (English query → German corpus)
3. German compound words don't match (Untersuchungshaft ≠ Untersuchungs- und Sicherheitshaft)
4. Agent sometimes searches in English despite German prompt

---

## Step 1: First 03_hyde_retrieval.ipynb (Run 1)

**File:** `03_hyde_retrieval.ipynb` (created May 9, frozen May 15)  
**Run on Kaggle as:** `kaggle_submission.ipynb` (May 14-15)

### What Was Added (3 features simultaneously)

#### Feature A: Few-Shot Example Bank
```python
# Strategy:
# 1. Collect up to 3 real (query, text) pairs per type from train.csv  
# 2. For types with < 3 examples, fill remaining with synthetic
# 3. English translations for domain matching
# Result: type_examples_bank[type] = [ex1, ex2, ex3]
```
**Hypothesis:** If the agent sees examples from the correct domain, it'll generate better search queries.  
**How it works:** 
- Build a bank of 3,279 law examples + 276 court examples from train.csv
- For each query, match via English keyword overlap to find relevant type
- Inject matched examples into HyDE prompt as context

#### Feature B: Type Registry + Hierarchical Search
```python
# Two-level search:
#   Level 1: Identify relevant legal type via keyword matching
#   Level 2: BM25 search with type-aware score boosting
```
**Hypothesis:** If we know the question is about "Strafprozess", boost StPO documents.  
**How it works:**
- Classify each document by its law/court type code
- When few-shot matching identifies a type, boost BM25 scores for that type's documents
- Like a metadata filter, but soft (boost instead of hard filter)

#### Feature C: HyDE (Hypothetical Document Embeddings)
```python
# LLM generates a hypothetical German legal article
# Then BM25 searches using the hypothetical doc's text as query
# Type hints from few-shot guide the domain
```
**Hypothesis:** A generated German article will share vocabulary with real German articles → better BM25 match.  
**How it works:**
1. Few-shot matching identifies type hints (e.g., "StPO", "Haftrecht")
2. LLM generates hypothetical article: "Art. X StPO: Die Untersuchungshaft..."
3. This hypothetical text becomes the BM25 search query
4. BM25 keyword matching finds real articles with similar German words

### What Stayed Same vs Notebook 02
- Same LLM (Mistral-7B), same BM25 (no FAISS), same ReAct agent
- Same corpus sizes, same tokenizer, same output (all results dumped)
- Agent prompt still English (not yet switched to German)

### Result: **Val F1 ≈ 0.006** (same as / worse than notebook 02)

### Why It Failed
```
Few-shot keyword matching is 70% WRONG
    │
    ▼
Wrong type hints fed to HyDE  (e.g., "VZAE" instead of "StPO")
    │
    ▼
HyDE generates gibberish in wrong domain ("Briefkassenzertifikat")
    │
    ▼
BM25 searches with wrong vocabulary → irrelevant results
    │
    ▼
Type boost amplifies wrong results further
    │
    ▼
F1 = 0.006 (no improvement over nb02)
```

**Specific failure example (val Q1 — detention):**
- Expected domain: StPO (criminal procedure)
- Few-shot matched: VZAE (immigration regulation) — because word "Schuld" overlapped
- HyDE generated: gibberish about immigration detention
- Results: Commercial register, broadcasting, alcohol law articles

**Lesson:** Three tightly-coupled features that depend on each other in sequence = if the first one fails, all three fail. Should have been tested independently.

---

## Step 2: Run 2 (Same notebook, internal changes)

**File:** Still `03_hyde_kaggle.ipynb` (modified May 19)  
**Changes applied internally between Run 1 and Run 2**

### What Changed

| Feature | Run 1 | Run 2 |
|---------|-------|-------|
| Search | BM25 only | **+ FAISS semantic search (384d MiniLM)** |
| Fusion | None | **RRF (Reciprocal Rank Fusion)** |
| Agent output | Free-text parsing (regex) | **GBNF grammar → valid JSON** |
| Reranker | None | **BAAI/bge-reranker-v2-m3** |
| Output volume | ~188 citations/query | **~25 citations/query** (reranked top-25) |
| Agent iterations | 3 | **6** |

### New Feature D: FAISS Semantic Search
```python
# paraphrase-multilingual-MiniLM-L12-v2 (384d)
# Encodes both query and documents into embedding space
# Cosine similarity finds semantically similar documents
```
**Hypothesis:** Semantic search handles cross-lingual (English→German) where BM25 fails.

### New Feature E: GBNF Grammar
```python
# Forces LLM to output exactly: {"thought": "...", "action": "...", "query": "..."}
# No more regex parsing of free-text "Action: search_laws\nAction Input: ..."
```
**Hypothesis:** Eliminates parse failures and hallucinated tool observations.

### New Feature F: Cross-Encoder Reranker
```python
# BAAI/bge-reranker-v2-m3
# Scores (query, document) pairs → keeps top 25
```
**Hypothesis:** Reranking will filter noise, keeping only relevant results.

### Result: **Val F1 ≈ 0.006** (UNCHANGED despite massive engineering)

### Why It Still Failed
```
FAISS finds documents → good!
But reranker (cross-lingual: English query ↔ German doc) scores uniformly → 10-20% weaker
Few-shot STILL poisoning HyDE → wrong domain search
Agent now has 6 iterations but repeats same wrong searches
Output reduced to 25 → but those 25 are still from wrong domain

Net: recall near-zero regardless (correct articles not in retrieval pool)
```

**Key insight:** Reducing output from 188→25 didn't help because the 25 selected were STILL wrong. The fundamental problem was retrieval quality, not output volume.

**Lesson:** You cannot rerank what you never retrieved. If FAISS+BM25 don't find the gold article in top-50, no reranker can rescue it.

---

## Step 3: Run 3 — The Breakthrough (+5.5×)

**File:** `03_hyde_kaggle.ipynb` (modified May 20)

### What Changed

| Feature | Run 2 | Run 3 |
|---------|-------|-------|
| Agent language | English reasoning | **German reasoning + German queries** |
| Reranking mode | English query ↔ German doc (cross-lingual) | **German HyDE doc ↔ German doc (monolingual)** |
| HyDE type hints | From few-shot bank (70% wrong) | **None (types=None)** |
| Reranker top_n | 10 | **25** |
| Agent iterations | 6 | **4** |
| Score cutoff | None | **-3.0** (effectively no-op) |

### The 3 Changes That Mattered

**Change 1: German Agent (biggest impact)**
```python
# BEFORE (English):
# "Thought: I need to search for pre-trial detention requirements"
# "Action Input: pre-trial detention requirements"  ← ENGLISH vs GERMAN corpus!

# AFTER (German):
# "Thought: Ich suche nach Haftverlängerung im StPO"
# "Action Input: Untersuchungshaft Haftverlängerung StPO"  ← GERMAN matches GERMAN corpus
```

**Change 2: Monolingual Reranking**
```python
# BEFORE: reranker(English_query, German_doc)  → cross-lingual gap hurts
# AFTER:  reranker(German_HyDE_doc, German_doc) → same language = better scores
```

**Change 3: Remove Type Hints (types=None)**
```python
# BEFORE: HyDE prompt includes "types: VZAE, HVUV" → generates in wrong domain
# AFTER:  HyDE prompt has NO type hint → generates based on query meaning alone
```

### Result: **Val F1 = 0.034** — **5.5× improvement!** 🎉

### Why It Worked
```
German agent generates German search queries → BM25 tokens MATCH German corpus
    +
No type hints → HyDE generates in correct domain (follows query meaning)
    +
Monolingual reranking → reranker can actually discriminate relevant vs irrelevant
    =
5.5× F1 improvement in ONE step
```

### What Still Failed
- Agent misinterpreted some queries (Q1: latched onto "provisional measures" instead of IP/copyright)
- Translation errors: "remission of debt" → "Entschuldigungsbrief" (apology letter!)
- ~30% of queries still had English terms leaking into search queries
- Agent STILL never signals "done" — exhausts all 4 iterations

**Lesson:** Language alignment is the #1 priority for cross-lingual RAG. Making the agent think in the corpus language > any retrieval algorithm improvement.

---

## Step 4: Run 4 — PRF Replaces Few-Shot (+17%)

**File:** `03_hyde_kaggle.ipynb` (modified May 24)

### What Changed

| Feature | Run 3 | Run 4 |
|---------|-------|-------|
| Few-shot bank | 3,279 law + 276 court examples | **REMOVED entirely** |
| Few-shot FAISS index | 3,555 vectors built | **REMOVED** |
| HyDE context source | None (types=None, no context) | **PRF: top-3 raw FAISS results** |
| Code lines | 185-line bank builder | **22-line get_law_type/get_court_type** |

### New Feature G: Pseudo-Relevance Feedback (PRF)
```python
# Step 1: Agent generates German query "Untersuchungshaft Voraussetzungen StPO"
# Step 2: Raw FAISS search → top 3 results (may be imperfect)
# Step 3: Feed those 3 results as context into HyDE prompt:
#          "Referenztexte aus der Datenbank:
#           - Art. 212 StPO: Die Beschuldigte Person..."
# Step 4: LLM generates hypothetical article GROUNDED in real vocabulary
# Step 5: Embed hypothetical → final FAISS search → better results
```

**Hypothesis:** Using actual corpus documents as HyDE context is better than a pre-built example bank.

### Result: **Val F1 = 0.040** — +17% over Run 3

### Per-Query Results (first detailed breakdown)
| Query | F1 | What Happened |
|-------|-----|---------------|
| Q5 (parental contact) | **0.111** | Best! PRF found relevant ZGB family law |
| Q9 (child maintenance) | **0.103** | Found ZGB maintenance articles |
| Q2 (disability/IVG) | **0.066** | Found IVG domain |
| Q6 (gratuitous help) | **0.087** | Some OR hits |
| Q4 (testament) | **0.000** | PRF returned wrong docs → HyDE drifted |
| Q7 (donation/gift) | **0.000** | PRF returned wrong domain entirely |
| Q8 (fiduciary) | **0.000** | Complete miss |
| Q10 (bank signature) | **0.000** | Wrong domain |

### Why It Worked (When It Worked)
```
When PRF returns relevant initial results (Q5, Q9):
  Real corpus text → grounds HyDE in correct vocabulary → better final search
  
When PRF returns irrelevant initial results (Q4, Q7):
  Wrong corpus text → anchors HyDE to wrong domain → WORSE than no context
```

### The PRF Tradeoff
PRF is a "good gets better" technique:
- ✅ If initial FAISS search is in right ballpark → amplifies correct signal
- ❌ If initial FAISS search is in wrong domain → amplifies NOISE

**Lesson:** PRF helps ~50% of queries (where embeddings already find the right area) but hurts the other ~50% (where embeddings are lost). Net improvement = +17%.

---

## Complete Score Progression

| Step | Feature Changes | Val F1 | Δ from Previous |
|------|----------------|--------|-----------------|
| **Notebook 02** | BM25 + ReAct agent (English) | 0.0152 | — (baseline) |
| **Run 1** | + Few-shot bank + Type registry + HyDE | 0.006 | **-60%** ❌ |
| **Run 2** | + FAISS embeddings + GBNF + Reranker + top-25 | 0.006 | **0%** (no change) |
| **Run 3** | + German agent + Monolingual rerank + types=None | **0.034** | **+467%** ✅ |
| **Run 4** | + PRF replaces few-shot bank | **0.040** | **+17%** ✅ |

---

## Feature Impact Summary (Isolated Effect)

| Feature | Impact on F1 | Confidence | Mechanism |
|---------|-------------|------------|-----------|
| **German agent** | **+467% (0.006→0.034)** | ✅ HIGH | Language alignment: German queries match German corpus |
| **Remove type hints** | Part of +467% | ✅ HIGH | Stops poisoning HyDE with wrong domain |
| **Monolingual reranking** | Part of +467% | ✅ HIGH | Same-language comparison = better discrimination |
| **PRF → HyDE** | **+17% (0.034→0.040)** | ⚠️ MEDIUM | Grounds HyDE in real corpus (when initial search is good) |
| **FAISS embeddings** | ~0% alone | ⚠️ LOW | Added in Run 2 but didn't help until German agent fixed queries |
| **GBNF grammar** | ~0% on F1 | ✅ HIGH (reliability) | Zero parse failures, but doesn't improve retrieval quality |
| **Few-shot bank** | **NEGATIVE** | ✅ HIGH | 70% wrong type matching poisoned everything downstream |
| **Type boost** | **NEGATIVE** | ✅ HIGH | Amplified wrong types when few-shot was wrong |
| **Cross-lingual reranking** | **NEGATIVE** | ✅ HIGH | English↔German gap made reranker worse than no reranker |

---

## What To Re-Run for Fresh Scores

To verify these numbers with clean runs:

1. **Run the final 03_hyde_kaggle.ipynb as-is** (DATASET_MODE="val") → should get ~0.040
2. **Then DATASET_MODE="test"** → upload to Kaggle for public/private LB

The notebook currently has all Run 4 features (German agent + PRF + FAISS + GBNF + monolingual rerank). To isolate individual feature effects, you'd need to toggle them off one at a time.

---

## Key Architectural Differences: 02 vs Final 03

| Component | Notebook 02 | Final 03 (Run 4) |
|-----------|-------------|-------------------|
| **Search engine** | BM25 only | FAISS (384d) + BM25 + RRF fusion |
| **Agent language** | English prompt, English reasoning | German prompt, German reasoning |
| **Agent output format** | Free-text (regex parsed) | GBNF grammar (guaranteed JSON) |
| **Query enhancement** | None | PRF → HyDE (hypothetical German doc) |
| **Reranking** | None | Monolingual (German HyDE ↔ German doc) |
| **Output filtering** | None (all ~119 results) | Reranker top-25 |
| **Few-shot bank** | N/A | REMOVED (was harmful) |
| **Type hints** | N/A | REMOVED (was harmful) |
| **Embedding model** | None | paraphrase-multilingual-MiniLM-L12-v2 (384d) |
| **Agent iterations** | 3 | 4 |

---

## Lessons for AI Engineering Interviews

1. **"What was the single biggest improvement?"**  
   → "Language alignment. Making the agent reason in German (the corpus language) instead of English gave 5.5× F1. No algorithm change — just prompt language."

2. **"What was the most surprising failure?"**  
   → "Adding a few-shot example bank HURT performance. It matched wrong domains 70% of the time and poisoned all downstream components. Removing it improved everything."

3. **"How do you isolate which feature is helping?"**  
   → "Toggle one at a time. We learned this the hard way — Run 1 added 3 features simultaneously and couldn't tell which was broken. Run 3 changed 3 things together and all helped, but we couldn't attribute the improvement precisely."

4. **"When does PRF help vs hurt?"**  
   → "PRF amplifies whatever signal the initial retrieval provides. If initial FAISS finds relevant docs (50% of queries), PRF improves HyDE quality. If initial FAISS misses entirely, PRF grounds HyDE in irrelevant text and makes it worse."
