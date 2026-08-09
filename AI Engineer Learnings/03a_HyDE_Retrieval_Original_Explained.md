# 03_hyde_retrieval.ipynb — Complete Cell-by-Cell Breakdown

> **Notebook:** `03_hyde_retrieval.ipynb` (cleaned version — 36 cells)  
> **Architecture:** BM25 + 3 toggleable features (HyDE, Few-Shot Bank, Type Boost + CCH)  
> **Base:** Same BM25 agent as notebook 02 (no FAISS, no embeddings)  
> **Upgrade from 02:** Adds HyDE, Few-Shot Bank, Type Boost with CCH labeling  
> **NOT included here:** FAISS embeddings, RRF fusion, GBNF grammar, German agent (→ those go to `03_hyde_kaggle`)

---

## What This Notebook Adds Over Notebook 02

| Feature | Toggle | What It Does | Hypothesis |
|---------|--------|-------------|------------|
| **A: HyDE** | `hyde_enabled` | LLM generates a fake German article → BM25 searches with it | Bridges English→German vocabulary gap |
| **B: Few-Shot Bank** | `few_shot_enabled` | Domain-matched examples from train.csv guide HyDE | Better domain targeting for generated text |
| **C: Type Boost + CCH** | `type_boost_enabled` | 1.5× BM25 score boost for matching types + `[TYPE]` labels in results | Prioritize correct legal area |

**What stays from notebook 02:** BM25 keyword search, ReAct agent (English), Mistral-7B, same corpus (175K laws + 100K courts)

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│              03_hyde_retrieval PIPELINE (per tool call)                  │
│                                                                        │
│  English Query ("Under what conditions can detention be extended?")     │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────┐                  │
│  │ STEP 1: FEW-SHOT SELECTION (if few_shot_enabled) │                  │
│  │                                                   │                  │
│  │ For EVERY example in the bank (~3,555 total):     │                  │
│  │   score = |query_words ∩ example_query_en_words|  │                  │
│  │                                                   │                  │
│  │ Group scores by type → per-type aggregate:        │                  │
│  │   type_scores = {OR: 5, StPO: 0, VZAE: 3, ...}   │                  │
│  │                                                   │                  │
│  │ If top_type ≥ 1.5× runner_up:                     │                  │
│  │   type_hints = [top_type]  (dominant)              │                  │
│  │ Else:                                              │                  │
│  │   type_hints = [top_type, runner_up]  (ambiguous)  │                  │
│  │                                                   │                  │
│  │ Select 3 examples FROM the winning type(s)        │                  │
│  │ (not top-3 across all types!)                     │                  │
│  └──────────────────┬──────────────────────────────┘                  │
│                      │ matched_examples, type_hints                     │
│                      ▼                                                  │
│  ┌─────────────────────────────────────────────────┐                  │
│  │ STEP 2: HyDE GENERATION (if hyde_enabled)        │                  │
│  │                                                   │                  │
│  │ Prompt (GERMAN instruction, English query):       │                  │
│  │                                                   │                  │
│  │   [INST] Du bist ein Schweizer Rechtsexperte.    │                  │
│  │   Schreibe einen hypothetischen Gesetzesartikel   │                  │
│  │   auf Deutsch, der diese Frage beantworten würde. │                  │
│  │   Der Text soll ca. 300 Zeichen lang sein.        │                  │
│  │   Wenn die Frage auf Englisch ist, schreibe       │                  │
│  │   trotzdem auf Deutsch.                           │                  │
│  │                                                   │                  │
│  │   Beispiele:                                      │                  │
│  │   Frage (EN): What is duty of care?               │                  │
│  │   Frage (DE): Was ist die Sorgfaltspflicht?       │                  │
│  │   Hypothetischer Text: Art. X OR: Der Schuldner..│                  │
│  │   [... 2 more examples ...]                       │                  │
│  │                                                   │                  │
│  │   Frage: {actual English query}                   │                  │
│  │   Hypothetischer Text: [/INST]                    │                  │
│  │                                                   │                  │
│  │ → LLM generates ~300 chars of German legal text   │                  │
│  │ → Cached by hash(query+type) for reuse            │                  │
│  │                                                   │                  │
│  │ If hyde_enabled=False: returns raw query instead   │                  │
│  └──────────────────┬──────────────────────────────┘                  │
│                      │ hyde_doc (German text)                            │
│                      ▼                                                  │
│  ┌─────────────────────────────────────────────────┐                  │
│  │ STEP 3: BM25 SEARCH + TYPE BOOST                 │                  │
│  │                                                   │                  │
│  │ BM25 search using hyde_doc as query               │                  │
│  │ (German text → German corpus = token overlap!)    │                  │
│  │                                                   │                  │
│  │ If type_boost_enabled AND type_hints:             │                  │
│  │   For each result doc:                            │                  │
│  │     if doc.type ∈ type_hints:                     │                  │
│  │       score *= 1.5  (soft boost, not hard filter) │                  │
│  │                                                   │                  │
│  │ If type_boost_enabled=False:                      │                  │
│  │   type_hints cleared → no boosting                │                  │
│  └──────────────────┬──────────────────────────────┘                  │
│                      │ ranked results                                   │
│                      ▼                                                  │
│  ┌─────────────────────────────────────────────────┐                  │
│  │ STEP 4: CCH FORMATTING                            │                  │
│  │                                                   │                  │
│  │ Each result labeled with its type:                │                  │
│  │   - [StPO] Art. 221 Abs. 1 StPO: Die Unter...    │                  │
│  │   - [OR] Art. 1 OR: Zum Abschluss eines...       │                  │
│  │                                                   │                  │
│  │ Header shows what types were boosted:             │                  │
│  │   [Type boost: StPO, StGB (keyword matching)]     │                  │
│  │                                                   │                  │
│  │ → Agent sees provenance of each result            │                  │
│  └──────────────────────────────────────────────────┘                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Cell-by-Cell Walkthrough

### Cells 1-5: Setup + Configuration

**Cell 1 (Markdown):** Describes scope — 3 features on BM25 base, no FAISS.

**Cell 2:** pip install (`rank-bm25`, `llama-cpp-python` with CUDA).

**Cell 4:** Paths (fixed for Kaggle: competition data + `charan1996/mistral-7b-gguf`).

**Cell 5 — CONFIG with Feature Toggles:**
```python
CONFIG = {
    # ... same LLM/agent settings as notebook 02 ...
    
    # FEATURE TOGGLES
    "hyde_enabled": False,           # Feature A
    "few_shot_enabled": False,       # Feature B  
    "type_boost_enabled": False,     # Feature C
    
    # HyDE parameters
    "hyde_max_tokens": 300,
    "hyde_temperature": 0.3,         # More creative than agent (0.1)
    "hyde_few_shot_count": 3,        # Examples per HyDE prompt
    "hyde_target_chars_law": 300,    # Target length for fake law articles
    "hyde_target_chars_court": 400,  # Target length for fake court considerations
    
    # Type boost parameters
    "type_boost_factor": 1.5,        # Soft multiplier for matching types
}
```

**Ablation test configs (toggle one at a time):**

| Test | hyde | few_shot | type_boost | What it tests |
|------|------|----------|------------|---------------|
| 1 | OFF | OFF | OFF | Baseline (= notebook 02) |
| 2 | ON | OFF | OFF | HyDE alone (generic prompt) |
| 3 | ON | ON | OFF | HyDE with domain examples |
| 4 | ON | ON | ON | All features |
| 5 | OFF | OFF | ON | Type boost alone (BM25 + boost) |

---

### Cells 6-9: Corpus Loading + BM25 Index (Same as Notebook 02)

Identical BM25 setup:
- `laws_de.csv` → 175K articles, `BM25Okapi` index
- `court_considerations.csv` → 100K decisions (4% of 2.5M)
- Same naive tokenizer: `re.split(r"\W+", text.lower())`

---

### Cells 10-12: Basic Search Tools (Fallback)

Same `LawSearchTool` / `CourtSearchTool` as notebook 02. These get **overridden** by HyDE tools in Cell 20. When `hyde_enabled=False`, the HyDE tools pass the raw query through to BM25 — same behavior as basic tools.

---

### Cells 13-14: LLM Loading (GPU Fixed)

```python
llm = Llama(model_path=..., n_gpu_layers=-1, n_threads=8)
```
Previously ran on CPU (~10 min/query). Now GPU (~30 sec/query).

---

### Cells 15-16: Few-Shot Example Bank (Feature B)

**Purpose:** Build a library of real (query, citation, text) examples so HyDE can see what actual corpus documents look like.

**How it's built:**
```
1. Read train.csv (German queries + gold citations)
2. For each gold citation, look up full text in corpus
3. Group by type code: {"OR": [ex1, ex2, ex3], "StPO": [...], ...}
4. Keep up to 3 per type (shortest queries = most focused)
5. Types with < 3 real examples → fill with LLM-generated synthetic queries
6. Each example gets English translation (query_en) for keyword matching
7. Cache to pickle

Result: ~3,279 law + ~276 court = ~3,555 examples
```

**Each example structure:**
```python
{
    "query": "Was sind die Voraussetzungen eines gültigen Vertrags?",  # German
    "query_en": "What are the requirements for a valid contract?",      # English
    "citation": "Art. 1 OR",
    "text": "Zum Abschluss eines Vertrages ist die übereinstimmende...", # Real corpus
    "source": "train.csv"  # or "synthetic"
}
```

---

### Cells 17-18: Type Registry + Hierarchical Search (Feature C)

**Type classification for every document:**
```python
get_law_type("Art. 221 Abs. 1 StPO") → "StPO"
get_law_type("Art. 1 OR") → "OR"
get_court_type("BGE 137 IV 122") → "BGE_IV"
get_court_type("1B_210/2023") → "CASE_1B"
```

**Hierarchical BM25 search with soft boost:**
```python
def hierarchical_bm25_search(index, query, type_hints, boost_factor=1.5):
    scores = bm25.get_scores(query_tokens)
    if type_hints:
        boost_mask = np.where(doc_types ∈ type_hints, 1.5, 1.0)
        scores = scores * boost_mask  # Soft boost, not hard filter
    return top_k_results
```

**Why soft boost, not hard filter:**  
Hard filter = if type detection wrong, you lose ALL correct results.  
Soft boost = wrong type just doesn't get boosted, correct results still accessible.

**CCH (Contextual Chunk Headers):** Results prefixed with `[TYPE]`:
```
- [StPO] Art. 221 Abs. 1 StPO: Die Untersuchungshaft ist nur zulässig...
- [OR] Art. 1 OR: Zum Abschluss eines Vertrages...
```
Adapted from NirDiamant's RAG Techniques. Gives the agent provenance context.

---

### Cells 19-21: HyDE Generation + Enhanced Tools (Features A+B+C)

#### How Few-Shot Examples Are Selected

**Key: Examples come from the winning TYPE's bank, NOT globally top-3.**

```
Input: "Under what conditions can detention be extended?"
Query words (after stop-word removal): {conditions, detention, extended}

Step 1: Score EVERY example (3,555 total)
  For each example:
    score = |{conditions, detention, extended} ∩ example.query_en_words|

Step 2: Aggregate by type
  type_scores = {VZAE: 3, StPO: 0, OR: 1, BGG: 0, ...}
  (VZAE wins because its examples contain "detention" frequently)

Step 3: Determine type_hints
  VZAE (3) ≥ 1.5 × StPO (0) → type_hints = ["VZAE"] (dominant)

Step 4: Select 3 examples FROM bank["VZAE"]
  → All 3 examples are immigration law (WRONG for criminal detention!)

Result: ([immigration_ex1, immigration_ex2, immigration_ex3], ["VZAE"])
```

**Why this is 70% wrong:** "detention" appears in VZAE (immigration detention) examples more than StPO (criminal detention) because the training set has more immigration questions with that English word.

**If two types are close (< 1.5× ratio):** Both contribute examples proportionally:
```
type_scores = {OR: 5, ZGB: 4}  → ratio = 5/4 = 1.25 < 1.5
→ type_hints = ["OR", "ZGB"]
→ 2 examples from OR + 1 from ZGB (proportional to 5:4 scores)
```

#### The HyDE Prompt

**Language: GERMAN instruction, cross-lingual bridge in examples**

```
[INST] Du bist ein Schweizer Rechtsexperte.
Gegeben eine rechtliche Frage, schreibe einen hypothetischen
Schweizer Gesetzesartikel auf Deutsch, der diese Frage beantworten würde.
Schreibe den Text wie einen echten Gesetzesartikel (Gesetzestext),
nicht als Antwort oder Erklärung.
Der Text soll ca. 300 Zeichen lang sein.
Wenn die Frage auf Englisch ist, schreibe trotzdem auf Deutsch.

Beispiele:

Frage (EN): What is the duty of care in contract law?
Frage (DE): Was ist die Sorgfaltspflicht im Vertragsrecht?
Hypothetischer Text: Art. X OR: Der Schuldner haftet für jede Fahrlässigkeit...

Frage (EN): When can a lease be terminated?
Frage (DE): Wann kann ein Mietvertrag gekündigt werden?
Hypothetischer Text: Art. Y OR: Das Mietverhältnis kann gekündigt werden...

Frage (EN): What constitutes negligent homicide?
Frage (DE): Was ist fahrlässige Tötung?
Hypothetischer Text: Art. Z StGB: Wer fahrlässig den Tod eines Menschen...

Frage: Under what conditions can detention be extended?

Hypothetischer Text: [/INST]
```

**Design choices:**
- **Instruction in German** → sets the generation language
- **"Wenn die Frage auf Englisch ist, schreibe trotzdem auf Deutsch"** → explicit cross-lingual instruction
- **Examples show EN → DE → German text** → teaches the bridge pattern
- **"nicht als Antwort oder Erklärung"** → prevents the LLM from explaining instead of generating article text
- **Target length specified** → prevents overly long or short output
- **temperature=0.3** → slightly creative (vs 0.1 for agent) to generate varied vocabulary

**When `hyde_enabled=False`:** Function returns the raw English query. BM25 searches English tokens against German corpus → near-zero matches.

#### How the Tool Chains Everything Together

```python
class HyDELawSearchTool:
    def run(self, query):
        # Feature B guard
        if CONFIG.get("few_shot_enabled", True):
            examples, type_hints = select_few_shot_examples(query, "law")
        else:
            examples, type_hints = [], []  # Generic HyDE prompt
        
        # Feature C guard
        if not CONFIG.get("type_boost_enabled", True):
            type_hints = []  # No boosting
        
        # Feature A: HyDE generation
        hyde_doc = generate_hypothetical_document(query, "law", examples)
        # If hyde_enabled=False → hyde_doc = raw English query
        
        # BM25 search + type boost
        results = hierarchical_bm25_search(index, hyde_doc, type_hints)
        
        # CCH formatting
        return format_with_type_labels(results)
```

---

### Cells 22-25: ReAct Agent (English)

Same agent as notebook 02 with one addition:

**Cell 24 — Type Registry Injection:**
```python
AGENT_SYSTEM_PROMPT += """
=== AVAILABLE LEGAL SOURCES IN CORPUS ===
Law types: OR(35000), ZGB(28000), StGB(15000), StPO(1171), ...
Court types: BGE_III(12000), BGE_IV(8000), ...

NOTE: You do NOT need to include type abbreviations in your queries.
The search tools automatically detect the relevant legal type.
"""
```

Agent prompt is still **ENGLISH** (→ `03_hyde_kaggle` switches to German).

---

### Cells 26-34: Pipeline (Load Data → Predict → Evaluate)

Standard: load `val.csv` → run agent on each query → save predictions → compute Macro F1.

---

## Feature Dependencies

```
hyde_enabled=False:
  → HyDE bypassed → raw English query goes to BM25
  → few_shot_enabled has NO EFFECT (examples never used)
  → type_boost_enabled still works on BM25 results

hyde_enabled=True, few_shot_enabled=False:
  → Generic HyDE prompt (no examples) → generates German text
  → Quality depends on LLM's built-in German legal knowledge
  → May be BETTER than with wrong examples (no domain poisoning)

hyde_enabled=True, few_shot_enabled=True, type_boost_enabled=False:
  → Domain-matched examples guide HyDE → BM25 search
  → No score boosting → types may rank incorrectly

ALL enabled:
  → Full chain: examples → HyDE → BM25 + boost → CCH labels
```

---

## What Failed and Why

### The 70% Wrong Type Detection
```
Query: "Under what conditions can pre-trial detention be extended?"
Expected type: StPO (criminal procedure)
Matched type: VZAE (immigration law)
Why: "detention" appears more in immigration examples than criminal

→ 3 immigration examples fed to HyDE
→ HyDE generates immigration-themed German text
→ BM25 matches immigration documents
→ Type boost amplifies immigration results
→ 0 correct citations found
```

### BM25 Compound Word Ceiling
Even with perfect HyDE output, BM25 can't match:
```
HyDE generates: "Untersuchungshaft" (one token)
Corpus text: "Untersuchungs- und Sicherheitshaft" (hyphenated → different tokens)
BM25 overlap: ZERO
```
13/19 gold law articles score exactly 0.0 regardless of query.

---

## Interview Questions

1. **"How does HyDE work and when does it help?"**  
   → "HyDE generates a hypothetical document that would answer the query, then searches for real similar documents. It helps when query-document vocabulary differs (cross-lingual, different registers). The generated doc shares vocabulary with real docs → better BM25 matching. It hurts when generated in wrong domain → anchors search to irrelevant text."

2. **"How are few-shot examples selected for HyDE?"**  
   → "All examples' English queries are scored against the input by word overlap (stop words removed). Scores are aggregated BY TYPE — the winning type's 3 examples are selected (not globally top-3). If the top type scores ≥1.5× the runner-up, it's dominant; otherwise both types contribute proportionally. Critical flaw: word overlap can't distinguish 'immigration detention' from 'criminal detention'."

3. **"What is CCH and why use it?"**  
   → "Contextual Chunk Headers prepend type metadata to search results: `[StPO] Art. 221...`. This gives the ReAct agent provenance context — it can see which legal area each result comes from and decide what to search next more intelligently."

4. **"Why soft boost instead of hard filter?"**  
   → "With 70% wrong type detection, hard filtering would discard all correct results. Soft boost (1.5×) just fails to help when wrong — correct results still accessible at their natural BM25 rank."

5. **"What's the cross-lingual bridge pattern?"**  
   → "The HyDE prompt shows examples with BOTH English and German queries: `Frage (EN): ... / Frage (DE): ...`. This teaches the model the translation pattern explicitly — given an English input, produce German output matching the style of the German examples."
