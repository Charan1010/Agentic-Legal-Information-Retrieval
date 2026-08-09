# Notebook 03 — HyDE + Hierarchical Retrieval: Complete Detailed Flow

## Table of Contents

1. [Competition Context](#1-competition-context)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Cell-by-Cell Walkthrough](#3-cell-by-cell-walkthrough)
   - [Phase A: Environment & Configuration (Cells 1–4)](#phase-a-environment--configuration-cells-14)
   - [Phase B: Corpus Loading & BM25 Index (Cells 5–8)](#phase-b-corpus-loading--bm25-index-cells-58)
   - [Phase C: Baseline Search Tools (Cells 9–11)](#phase-c-baseline-search-tools-cells-911)
   - [Phase D: LLM Loading (Cells 12–13)](#phase-d-llm-loading-cells-1213)
   - [Phase E: Hybrid Few-Shot Bank (Cells 14–15)](#phase-e-hybrid-few-shot-bank-cells-1415)
   - [Phase F: Type Registry & Hierarchical Search (Cells 16–17)](#phase-f-type-registry--hierarchical-search-cells-1617)
   - [Phase G: HyDE + Hierarchical Search Tools (Cells 18–20)](#phase-g-hyde--hierarchical-search-tools-cells-1820)
   - [Phase H: ReAct Agent + Type Injection (Cells 21–24)](#phase-h-react-agent--type-injection-cells-2124)
   - [Phase I: Inference & Evaluation (Cells 25–36)](#phase-i-inference--evaluation-cells-2536)
4. [Data Flow: End-to-End for a Single Query](#4-data-flow-end-to-end-for-a-single-query)
5. [The Three RAG Techniques Combined](#5-the-three-rag-techniques-combined)
6. [Key Data Structures Reference](#6-key-data-structures-reference)
7. [Configuration Reference](#7-configuration-reference)

---

## 1. Competition Context

**Omnilex Legal Retrieval** (Kaggle code competition):
- **Input**: English legal questions about Swiss law
- **Output**: Exact German/Swiss legal citation strings (e.g. `Art. 1 Abs. 1 OR`, `BGE 142 III 481 E. 2.6`)
- **Metric**: Macro F1 across all queries
- **Constraints**: Code competition, 12-hour runtime, no internet access
- **Key challenge**: Queries are in **English**, corpus is 100% **German** → cross-lingual retrieval

**Corpus**:
| Corpus | File | Size | Documents | Types |
|--------|------|------|-----------|-------|
| Laws | `laws_de.csv` | 73 MB | ~175,933 | 656 statute abbreviations (OR, ZGB, StGB, BV, FINMA, USG, ...) |
| Courts | `court_considerations.csv` | 2.43 GB | ~2,476,315 | 59 types: 5 BGE divisions (BGE_I through BGE_V) + 54 case prefixes (1C, 5A, 2C, 6B, ...) |

**LLM**: Mistral-7B-Instruct v0.2 Q4_K_M GGUF (quantized, runs locally via `llama-cpp-python`)

---

## 2. High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                     NOTEBOOK 03: FULL PIPELINE                       │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │  laws_de.csv │    │ court_con... │    │   train.csv            │  │
│  │  175K docs   │    │ 2.5M docs    │    │   (German queries +    │  │
│  │  (German)    │    │ (German)     │    │    gold citations)     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬─────────────┘  │
│         │                   │                       │                │
│         ▼                   ▼                       │                │
│  ┌──────────────────────────────────┐               │                │
│  │   BM25 INDICES (BM25Okapi)      │               │                │
│  │   laws_index   courts_index     │               │                │
│  │   + doc_types arrays (numpy)    │  ◄─── type    │                │
│  └──────────┬───────────────┬──────┘    metadata    │                │
│             │               │                       │                │
│             │               │                       ▼                │
│             │               │          ┌──────────────────────────┐  │
│             │               │          │  HYBRID FEW-SHOT BANK   │  │
│             │               │          │  v2: 3 examples/type    │  │
│             │               │          │  Real (train.csv) +     │  │
│             │               │          │  Synthetic (Mistral)    │  │
│             │               │          │  + English translations │  │
│             │               │          └──────────┬──────────────┘  │
│             │               │                     │                  │
│             │               │                     │ domain-matched   │
│             │               │                     │ few-shot select  │
│             │               │                     ▼                  │
│             │               │          ┌──────────────────────────┐  │
│             │               │          │  HyDE GENERATOR          │  │
│             │               │          │  (Mistral-7B-Instruct)   │  │
│             │               │          │  English Q → German text │  │
│             │               │          └──────────┬──────────────┘  │
│             │               │                     │                  │
│             ▼               ▼                     ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │          HIERARCHICAL SEARCH TOOLS                           │    │
│  │                                                              │    │
│  │  ┌─────────────────────┐  ┌──────────────────────────┐      │    │
│  │  │ HyDELawSearchTool   │  │ HyDECourtSearchTool      │      │    │
│  │  │                     │  │                          │      │    │
│  │  │ 1. detect_law_type  │  │ 1. detect_court_type    │      │    │
│  │  │ 2. select_few_shot  │  │ 2. select_few_shot      │      │    │
│  │  │ 3. HyDE generate    │  │ 3. HyDE generate        │      │    │
│  │  │ 4. BM25 + boost     │  │ 4. BM25 + boost         │      │    │
│  │  │ 5. Merge HyDE+KW    │  │ 5. Merge HyDE+KW        │      │    │
│  │  │ 6. CCH format       │  │ 6. CCH format            │      │    │
│  │  └─────────────────────┘  └──────────────────────────┘      │    │
│  └──────────────────────────────────┬───────────────────────────┘    │
│                                     │                                │
│                                     ▼                                │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    REACT AGENT                               │    │
│  │  System prompt (German) + TYPE_REGISTRY injected             │    │
│  │  Thought → Action → Observation loop (max 3 iterations)      │    │
│  │  All queries translated to German by LLM                     │    │
│  └──────────────────────────────────┬───────────────────────────┘    │
│                                     │                                │
│                                     ▼                                │
│                    ┌──────────────────────────┐                      │
│                    │  CITATION EXTRACTION     │                      │
│                    │  regex: Art., BGE, SR     │                      │
│                    │  + tool.get_last_citations │                      │
│                    └──────────┬───────────────┘                      │
│                               │                                      │
│                               ▼                                      │
│                    ┌──────────────────────────┐                      │
│                    │  submission_hyde.csv      │                      │
│                    │  query_id, citations      │                      │
│                    └──────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cell-by-Cell Walkthrough

### Phase A: Environment & Configuration (Cells 1–4)

#### Cell 1 (Markdown) — Notebook Header
Describes the notebook purpose: HyDE-enhanced agentic retrieval. Lists the four key enhancements over the baseline:
1. Hypothetical document generation
2. Few-shot examples from train.csv
3. Hybrid search (HyDE + keywords)
4. Two HyDE variants (law vs court)

#### Cell 2 (Markdown) — Section Header: "Setup & Configuration"

#### Cell 3 (Code) — Environment Detection & Path Setup
**What it does**: Detects whether we're on Kaggle or local, sets all file paths accordingly.

**Key variables created**:
| Variable | Local Value | Purpose |
|----------|-------------|---------|
| `KAGGLE_ENV` | `False` | Toggles Kaggle vs local paths |
| `DATASET_MODE` | `"val"` | Which split to run on (`"val"` for dev, `"test"` for submission) |
| `DATA_PATH` | `../data` | Root data directory |
| `MODEL_PATH` | `../models` | Where GGUF model lives |
| `OUTPUT_PATH` | `../output` | Where submission CSVs go |
| `INDEX_PATH` | `../data/processed` | Where cached BM25 pickle files go |
| `LAWS_CSV` | `../data/laws_de.csv` | Laws corpus CSV (73MB, ~175K rows) |
| `COURTS_CSV` | `../data/court_considerations.csv` | Courts corpus CSV (2.43GB, ~2.5M rows) |
| `QUERY_FILE` | `../data/val.csv` | Query file for current run |
| `IS_VALIDATION_MODE` | `True` | Whether gold labels are available |
| `FORCE_REBUILD_INDICES` | `False` | If True, rebuilds BM25 from CSV instead of loading cache |

**Outputs**: Prints environment info, file sizes, paths.

#### Cell 4 (Code) — CONFIG Dictionary
**What it does**: Single configuration dict controlling the entire pipeline.

**Key settings**:

| Group | Setting | Value | Purpose |
|-------|---------|-------|---------|
| Model | `model_file` | `"mistral-7b-instruct-v0.2.Q4_K_M.gguf"` | GGUF model filename |
| Model | `n_ctx` | `16384` | Context window (tokens) |
| Model | `n_gpu_layers` | `-1` | GPU offload (-1 = all layers) |
| Agent | `max_iterations` | `3` | Max ReAct loops per query |
| Agent | `max_tokens` | `512` | Max tokens per LLM generation |
| Agent | `temperature` | `0.1` | Low temp for deterministic routing |
| Agent | `max_observation_chars` | `1200` | Truncate tool output for LLM context |
| Agent | `max_conversation_chars` | `28000` | Total conversation budget |
| Retrieval | `top_k_laws` | `40` | BM25 results per law search |
| Retrieval | `top_k_courts` | `40` | BM25 results per court search |
| HyDE | `hyde_enabled` | `True` | Master toggle (False = ablation) |
| HyDE | `hyde_max_tokens` | `300` | Max tokens for hypothetical doc |
| HyDE | `hyde_temperature` | `0.3` | Slightly creative for vocab diversity |
| HyDE | `hyde_few_shot_count` | `3` | Few-shot examples per HyDE prompt (domain-matched) |
| HyDE | `hyde_examples_per_type` | `3` | Examples stored per type in few-shot bank |
| HyDE | `hyde_target_chars_law` | `300` | Target length: hypothetical law article |
| HyDE | `hyde_target_chars_court` | `400` | Target length: hypothetical court consideration |
| HyDE | `hyde_max_synthetic_types` | `50` | Cap on synthetic query generation per corpus |
| Hierarchical | `type_boost_factor` | `1.5` | Score multiplier for type-matching docs |
| Hierarchical | `type_auto_detect` | `True` | Enable auto-detection from BM25 results |
| Hierarchical | `type_dominant_threshold` | `0.4` | Min fraction of top-20 to trigger auto-detect |

---

### Phase B: Corpus Loading & BM25 Index (Cells 5–8)

#### Cell 5 (Markdown) — Section Header: "Load Corpora and Build/Load Indices"

#### Cell 6 (Code) — BM25Index Class + Utilities
**What it does**: Defines the core retrieval infrastructure. This is the longest code cell (~260 lines).

**Key class: `BM25Index`**

```
BM25Index
├── __init__(documents, text_field, citation_field)
├── tokenize(text) → list[str]          # lowercase + \W+ split
├── build(documents)                     # creates BM25Okapi from tokenized corpus
├── search(query, top_k, return_scores)  # tokenize query → get_scores → argsort top-k
├── save(path)                           # pickle: documents + tokenized_corpus
└── load(path) → BM25Index              # restore from pickle, rebuild BM25Okapi
```

**How tokenization works**:
- `text.lower()` → `re.split(r"\W+", text)` → filter empty strings
- No stemming, no stopword removal — simple but works for German legal text because legal terms are distinctive

**How search works**:
1. Tokenize query with same tokenizer
2. `BM25Okapi.get_scores(query_tokens)` → numpy array of scores for ALL documents
3. `scores.argsort()[-top_k:][::-1]` → indices of top-k highest-scoring docs
4. Filter out docs with score ≤ 0
5. Return list of `{"citation": ..., "text": ...}` dicts

**Utility functions**:
- `load_csv_corpus(csv_path, chunk_size, max_rows)`: Reads CSV in chunks with tqdm progress bar. Each row → `{"citation": str, "text": str}`. `max_rows` caps loading for faster dev iterations.
- `get_or_build_index(name, csv_path, index_path, force_rebuild, max_rows)`: Cache-or-build pattern. If pickle exists and `force_rebuild=False`, loads from disk (~1s). Otherwise builds from CSV (laws: ~30s, courts: ~15-20min full).

**Why pickle caching matters**: The courts CSV is 2.43GB with 2.5M rows. Building BM25 from scratch takes 15-20 minutes and ~8-16GB peak RAM. The cached pickle loads in ~10 seconds.

#### Cell 7 (Code) — Load Laws Index
```python
laws_index = get_or_build_index("laws", LAWS_CSV, LAWS_INDEX_PATH, ...)
```
- Loads or builds the laws BM25 index
- Runs a test search for `"Vertrag"` to verify it works
- Result: `laws_index` with ~175,933 documents

#### Cell 8 (Code) — Load Courts Index
```python
courts_index = get_or_build_index("courts", COURTS_CSV, COURTS_INDEX_PATH, ..., max_rows=100000)
```
- **Currently using `max_rows=100000`** — loads only the first 100K of 2.5M court documents
- This is a development shortcut for faster iteration
- For final submission, remove `max_rows` to use the full 2.5M corpus
- Runs a test search for `"Meinungsfreiheit"` to verify

---

### Phase C: Baseline Search Tools (Cells 9–11)

#### Cell 9 (Markdown) — Section Header: "Define Search Tools"

#### Cell 10 (Code) — LawSearchTool & CourtSearchTool Classes
**What it does**: Defines two search tool classes that wrap BM25Index with a callable interface compatible with the ReAct agent.

**Both tools share the same structure**:
```
SearchTool
├── name: str           # "search_laws" or "search_courts"
├── description: str    # Natural language description for agent
├── __init__(index, top_k, max_excerpt_length)
├── __call__(query)     # Shortcut for run()
├── run(query) → str    # Execute search, return formatted results
└── get_last_citations() → list[str]  # Citations from most recent search
```

**run() flow**:
1. Validate query not empty
2. `self.index.search(query, top_k)` → list of doc dicts
3. Store in `self._last_results` (for `get_last_citations()` later)
4. Format each result as `"- {citation}: {text[:300]}..."`
5. Return joined string

**Tool registry**:
```python
TOOLS = {"search_laws": law_tool, "search_courts": court_tool}
```
This dict is the interface between the ReAct agent and the search tools. The agent outputs `Action: search_laws`, the agent loop looks up `TOOLS["search_laws"]` and calls it.

**Important**: This cell creates the BASELINE tools. They get **overridden** later in Cell 19 with HyDE+Hierarchical tools. The same `TOOLS` dict is mutated — the agent code doesn't change.

#### Cell 11 (Code) — Test Baseline Tools
Quick smoke test: calls `law_tool("Vertrag Abschluss")` and `court_tool("Meinungsfreiheit")` to verify tools work.

---

### Phase D: LLM Loading (Cells 12–13)

#### Cell 12 (Markdown) — Section Header: "Load Local LLM"

#### Cell 13 (Code) — Load Mistral via llama-cpp-python
**What it does**: Loads the quantized GGUF model into memory.

**Key steps**:
1. `has_cuda_support()`: Checks if llama-cpp was built with CUDA by looking for `*cuda*` or `*cublas*` shared libraries in the package directory
2. Finds model file at `MODEL_PATH / CONFIG["model_file"]`, or scans for any `.gguf` file as fallback
3. Auto-detects GPU: if CUDA support found, uses `n_gpu_layers=-1` (all layers on GPU). Otherwise falls back to CPU (`n_gpu_layers=0`)
4. Creates `Llama` instance:
   ```python
   llm = Llama(model_path=..., n_ctx=16384, n_threads=4, n_gpu_layers=-1, verbose=False)
   ```

**The `llm` variable** is the callable LLM used everywhere in the notebook:
- `llm(prompt, max_tokens=..., temperature=..., stop=[...])` → `{"choices": [{"text": "..."}]}`
- It's the Mistral `[INST]...[/INST]` prompt format throughout

---

### Phase E: Hybrid Few-Shot Bank (Cells 14–15)

#### Cell 14 (Markdown) — Section Header: "Build Few-Shot Example Bank (Hybrid v2)"
Describes the v2 hybrid approach: 3 examples per type (train.csv priority + synthetic fill), English translations for domain-matched routing at inference time.

#### Cell 15 (Code) — Hybrid Few-Shot Bank Builder v2 (~300 lines)
**This is one of the most important cells.** It builds the few-shot example bank that teaches HyDE what real legal documents look like.

**Key change from v1 → v2**: Instead of 1 example per type (flat list, always first N alphabetically), we now build **3 examples per type** organized in a dict (`type → [ex1, ex2, ex3]`), with **English translations** of each example's query for domain-matched selection at inference time.

**Step-by-step breakdown:**

##### Step 0: Helper Functions

```python
def get_law_type(citation):
    """'Art. 10a Abs. 1 USG' → 'USG'"""
    # Regex: find last uppercase abbreviation (2+ chars) at end of string
    # Fallback: find all uppercase words, take last one
    # Last resort: 'OTHER'
```

```python
def get_court_type(citation):
    """'BGE 142 III 239 E. 2.1' → 'BGE_III'
       '1C_633/2018 E. 1' → 'CASE_1C'"""
    # Pattern 1: BGE + volume roman numeral → 'BGE_III'
    # Pattern 2: case number prefix → 'CASE_1C'
    # Fallback: 'OTHER'
```

These two functions classify every document in the corpus into a "type" — the fundamental building block for both the few-shot bank and hierarchical search.

##### Step 1: Build citation→text lookups

```python
law_citation_to_text = {doc["citation"]: doc["text"] for doc in laws_index.documents}
court_citation_to_text = {doc["citation"]: doc["text"] for doc in courts_index.documents}
```
Two separate dicts for instant lookup: given a citation string, get its full text. Used to resolve train.csv gold citations → actual corpus text.

##### Step 2: Enumerate all types in corpus

```python
corpus_law_types = defaultdict(list)   # type → [{"citation": ..., "text": ...}, ...]
corpus_court_types = defaultdict(list)
```
Iterates every document, extracts its type, keeps up to **10** candidate documents per type (increased from 3 in v1 — more candidates = better synthetic fill pool). This tells us what types exist and how many documents each has.

**Result**: `len(corpus_law_types)` = 656 law types, `len(corpus_court_types)` = 59 court types (with 100K court docs loaded).

##### Step 3: Resolve train.csv → up to 3 real (query, text) pairs per type

```python
train_df = pd.read_csv(DATA_PATH / "train.csv")
```

For each training example:
1. Read the German query and gold citation string
2. Split gold citations by `;`
3. For each citation: look up in `law_citation_to_text` or `court_citation_to_text`
4. If found → create example dict: `{"query": ..., "citation": ..., "text": ..., "source": "train.csv"}`
5. Avoid duplicate citations within the same type
6. Keep up to **3 examples per type**, sorted by query length (shortest = most focused first)

**Result**: `real_law_examples[type]` and `real_court_examples[type]` — **lists of up to 3 examples** per type (not just 1 like v1), but only for types that appear in train.csv gold citations.

**Coverage gap**: Train.csv covers ~X law types out of 656, and ~Y court types out of 59. Notably: train.csv has **0 non-leading court decision citations** (no `1C_...`, `5A_...` etc.), but val.csv has 33 of them.

##### Step 4: Fill gaps with synthetic queries (up to 3 per type)

Two cases (new in v2):
- **Case A**: Type has 0 real examples → needs 3 synthetic
- **Case B**: Type has 1-2 real examples → needs 1-2 synthetic to fill to 3

For each type needing fill (capped at `hyde_max_synthetic_types=50` per corpus, ranked by corpus frequency):
1. Pick candidate documents not already used by real examples
2. Sort by text length descending (more context = better synthetic query)
3. Call `generate_synthetic_query(text_snippet, doc_type)`:
   ```python
   prompt = "[INST] Gegeben der folgende {Gesetzesartikel/Gerichtserwägung}, 
              schreibe eine kurze rechtliche Frage auf Deutsch...
              Text: {text[:400]}
              Frage: [/INST]"
   ```
4. LLM generates a synthetic German question (max 100 tokens, temp 0.3)
5. Append to `real_law_examples[type]` → fills to 3

**Why this matters**: Without synthetic examples, the HyDE generator has never seen examples of FINMA regulations, environmental law (USG), or non-leading court decisions. It would generate generic text that doesn't match corpus vocabulary.

##### Step 5 (NEW in v2): Translate all queries to English

```python
def translate_query_to_english(german_query):
    prompt = "[INST] Translate this German legal question to English...\n"
             f"German: {german_query[:400]}\nEnglish: [/INST]"
```

Every example (real + synthetic) gets its German query translated to English. The `query_en` field is stored alongside the original `query`. This is used for **domain-matched few-shot selection** at inference time — matching incoming English queries against stored English translations via keyword overlap, with no LLM routing needed.

##### Step 6: Build final few-shot banks (type → [3 examples])

```python
law_few_shot_bank = {}    # type → [ex1, ex2, ex3] (each has query, query_en, citation, text, source)
court_few_shot_bank = {}  # type → [ex1, ex2, ex3]
```

Final output:
- `law_few_shot_bank`: Dict of `type → list[dict]`, up to 3 examples per type
- `court_few_shot_bank`: Same structure
- `selected_law_examples`: Flat list (all examples from all types) — fallback compatibility
- `selected_court_examples`: Same
- Each example has: `{query, query_en, citation, text, source}`
- Tagged with `"source": "train.csv"` or `"source": "synthetic"` for transparency

---

### Phase F: Type Registry & Hierarchical Search (Cells 16–17)

#### Cell 16 (Markdown) — Section Header: "Type Registry & Hierarchical Search Infrastructure"
Describes the adaptation of two NirDiamant RAG techniques:
1. **Hierarchical Indices**: corpus hierarchy (Type → Article → Text) + soft BM25 boost
2. **Contextual Chunk Headers (CCH)**: type metadata prepended to results

#### Cell 17 (Code) — Type Registry + Hierarchical Search (~220 lines)

##### Step 1: Compute `doc_types` parallel arrays

```python
laws_index.doc_types = np.array(
    [get_law_type(doc["citation"]) for doc in laws_index.documents], dtype=object
)
courts_index.doc_types = np.array(
    [get_court_type(doc["citation"]) for doc in courts_index.documents], dtype=object
)
```

This creates a numpy array **parallel** to `index.documents` — same length, same order. `doc_types[i]` is the type label for `documents[i]`. This is the "metadata layer" that enables filtered/boosted search without rebuilding the BM25 index.

##### Step 2: Build TYPE_REGISTRY

```python
LAW_TYPE_REGISTRY = {
    "OR":    {"count": 3700, "example": "Art. 1 Abs. 1 OR"},
    "ZGB":   {"count": 2400, "example": "Art. 1 ZGB"},
    "FINMA": {"count": 2700, "example": "..."},
    ...  # 656 entries
}
COURT_TYPE_REGISTRY = {
    "BGE_III": {"count": ..., "example": "BGE 142 III 481 E. 2.6"},
    "CASE_1C": {"count": ..., "example": "1C_633/2018 E. 1"},
    ...  # 59 entries
}
```

Each entry has document count and an example citation. Used for:
- Agent prompt injection (LLM knows what types exist)
- Validation (is a detected type actually real?)
- Analysis/debugging

##### Step 3: Type detection functions

Three detection strategies:

**`detect_law_type(query)`** — Regex detection from query text:
- Sorts all known abbreviations by length descending (match `AHVG` before `AHV`)
- Regex `\b{ABBREV}\b` on uppercased query
- Returns first match or `None`
- Example: `"Vertrag Kündigung OR"` → `"OR"`

**`detect_court_type(query)`** — Regex detection from query text:
- Pattern 1: `BGE \d+ [IVX]+` → `"BGE_III"`
- Pattern 2: `\d+[A-Z]+ [\s_/]\d+` → `"CASE_1C"`
- Returns match or `None`

**`detect_dominant_type(scores, doc_types, top_n=20)`** — Auto-detection from BM25 results:
- Takes the raw BM25 score array (before any boosting)
- Examines the types of the top-20 scoring documents
- If one type has ≥ 40% (`type_dominant_threshold`) of the top-20, returns that type
- Handles cases where the query content implicitly targets one type without mentioning it
- Example: a query about "Vertragsverletzung Schadenersatz" might have 12/20 top results from OR, even without "OR" in the query

##### Step 4: `hierarchical_bm25_search()` — Core function

```python
def hierarchical_bm25_search(index, query, top_k, type_hint, boost_factor, auto_detect):
    """
    Returns: (results_list, type_info_dict_or_None)
    """
```

**Full flow**:
```
1. Tokenize query
2. Get raw BM25 scores: scores = index.index.get_scores(query_tokens)
   → numpy array of shape (N_docs,), one score per document
   
3. LEVEL 1 — TYPE ROUTING:
   if type_hint provided:
       type_info = {"type": type_hint, "source": "explicit"}
   elif auto_detect enabled:
       dominant = detect_dominant_type(scores, index.doc_types)
       if dominant:
           type_info = {"type": dominant, "source": "auto"}
   
4. LEVEL 2 — SOFT BOOST (not filter!):
   if type_info found:
       boost_mask = np.where(doc_types == type_info["type"], 1.5, 1.0)
       scores = scores * boost_mask
       # Documents matching the type get 1.5x their original BM25 score
       # All other documents keep their original score (1.0x)
       # NOTHING IS EXCLUDED — this is the key safety feature
   
5. Sort by boosted scores, return top-k with metadata:
   Each result dict includes:
   - citation, text (from original document)
   - _score (boosted BM25 score)
   - _type (document's type label)
```

**Why soft boost, not hard filter?** If the LLM guesses `type=OR` but the correct answer is from `ZGB`, a hard filter would exclude `ZGB` documents entirely. With a soft boost, `ZGB` documents still compete — they just need 1.5x higher raw BM25 scores to beat boosted `OR` documents. Wrong guesses cost very little; right guesses improve precision.

##### Step 5: Build prompt strings

```python
LAW_TYPES_FOR_PROMPT = "OTHER(84000), OR(3700), FINMA(2700), ZGB(2400), ..."
COURT_TYPES_FOR_PROMPT = "CASE_6B(318000), CASE_2C(317000), ..."
```

Condensed strings showing available types with document counts. Top 40 law types, all 59 court types. These get injected into the agent system prompt so the LLM knows what abbreviations exist.

---

### Phase G: HyDE + Hierarchical Search Tools (Cells 18–20)

#### Cell 18 (Markdown) — Section Header: "HyDE — Hypothetical Document Generation"
Describes domain-matched few-shot selection: instead of using the same 3 examples every time, examples are selected based on detected legal type + keyword overlap on English translations.

#### Cell 19 (Code) — HyDE Generator + Enhanced Search Tools (~400 lines)

##### `select_few_shot_examples(query, doc_type, type_hint, n)` (NEW in v2)

Domain-matched few-shot selector — picks the most relevant examples for each query **without using the LLM for routing**.

**Selection strategy (priority order)**:
1. **Type hint match**: If `type_hint` (from regex detection) matches a type in the bank, use that type's 3 examples
2. **Keyword overlap**: Tokenize the input query, score each example's `query_en` by shared word count, return examples from highest-scoring matches
3. **Fallback**: If still not enough examples, take from remaining types (alphabetical order)

```python
def select_few_shot_examples(query, doc_type="law", type_hint=None, n=3):
    bank = law_few_shot_bank if doc_type == "law" else court_few_shot_bank
    
    # Priority 1: type_hint → bank[type_hint]
    # Priority 2: keyword overlap on query_en fields
    # Priority 3: fallback to first available
    return result[:n]
```

**Why this matters**: In v1, the same 3 examples (first alphabetically) were used for every query. A contract law query got the same examples as a criminal law query. Now, a query about "Vertrag OR" gets OR-specific examples, a query about environmental liability gets USG examples, etc.

##### `build_hyde_prompt(query, doc_type, few_shot_examples)`

Constructs a Mistral `[INST]...[/INST]` prompt:

**For laws** (`doc_type="law"`):
```
[INST] Du bist ein Schweizer Rechtsexperte. Gegeben eine rechtliche Frage,
schreibe einen hypothetischen Schweizer Gesetzesartikel auf Deutsch,
der diese Frage beantworten würde.
Schreibe den Text wie einen echten Gesetzesartikel (Gesetzestext),
nicht als Antwort oder Erklärung.
Der Text soll ca. 300 Zeichen lang sein.
Wenn die Frage auf Englisch ist, schreibe trotzdem auf Deutsch.

Beispiele:

Frage: {example1.query[:300]}
Hypothetischer Text: {example1.text[:400]}

Frage: {example2.query[:300]}
Hypothetischer Text: {example2.text[:400]}

Frage: {actual_query}

Hypothetischer Text: [/INST]
```

**For courts** (`doc_type="court"`): Same structure, but asks for "hypothetische Erwägung eines Bundesgerichtsentscheids" (BGE consideration style text). Target length 400 chars instead of 300.

**Few-shot count**: Controlled by `hyde_few_shot_count` (default 3). In v2, receives **pre-selected domain-matched examples** from `select_few_shot_examples()` instead of slicing a flat list.

##### `generate_hypothetical_document(query, doc_type, few_shot_examples)`

```python
1. Check CONFIG["hyde_enabled"] — if False, return original query (ablation mode)
2. Check _hyde_cache (dict: MD5 hash of query+type → generated text)
3. Build prompt via build_hyde_prompt()
4. Call LLM:
   llm(prompt, max_tokens=300, temperature=0.3, stop=["[INST]", "</s>", "\nFrage:", "\n\nFrage:"])
5. Cache result
6. If LLM fails: fallback to returning original query (graceful degradation)
```

**Why HyDE works for this task**: The query might be `"What are the requirements for a valid contract?"` (English, 8 words). BM25 on this against a German corpus would return garbage. HyDE transforms it into something like `"Art. X. Zum Abschluss eines Vertrages ist die übereinstimmende gegenseitige Willensäusserung der Parteien erforderlich..."` (German, ~50 words of realistic legal vocabulary). This German text shares vocabulary with actual corpus documents, dramatically improving BM25 retrieval.

##### `HyDELawSearchTool` — Full search pipeline

```python
def run(self, query):
    # 1. LEVEL 1: Detect type from query
    type_hint = detect_law_type(query)  # e.g. "OR" from "Vertrag OR"
    
    # 2. DOMAIN-MATCHED FEW-SHOT SELECTION (NEW in v2)
    matched_examples = select_few_shot_examples(query, "law", type_hint)
    
    # 3. HYDE: Generate hypothetical German law article
    hyde_doc = generate_hypothetical_document(query, "law", matched_examples)
    
    # 4. LEVEL 2: TWO hierarchical BM25 searches
    hyde_results, hyde_type = hierarchical_bm25_search(
        self.index, hyde_doc, top_k=40, type_hint=type_hint
    )
    keyword_results, kw_type = hierarchical_bm25_search(
        self.index, query, top_k=40, type_hint=type_hint
    )
    
    # 5. MERGE: Union of results, dual-source boost
    # Citations found by BOTH HyDE and keyword get ranked first
    # Then HyDE-only results, then keyword-only results
    
    # 6. CCH FORMAT: Prepend type label to each result
    # "[Type boost: OR (explicit)]"
    # "- [OR] Art. 1 Abs. 1 OR: Zum Abschluss eines Vertrages..."
    # "- [OR] Art. 2 OR: Jeder Vertrag, der..."
    # "- [ZGB] Art. 1 ZGB: Das Gesetz findet..."  ← non-boosted type still appears
```

**The merge strategy**: Each result is tagged with its source (`hyde`, `keyword`, or both). Sorting priority:
1. Documents found by both HyDE AND keyword search (highest confidence)
2. Documents found by HyDE only
3. Documents found by keyword only

**CCH-style formatting**: Each result line starts with `[TYPE]` (e.g., `[OR]`, `[ZGB]`, `[BGE_III]`). This gives the LLM contextual awareness of where each result comes from — the "Contextual Chunk Headers" adaptation.

##### `HyDECourtSearchTool` — Same architecture, different prompt

Identical flow to `HyDELawSearchTool` but:
- Uses `detect_court_type()` instead of `detect_law_type()`
- Calls `select_few_shot_examples(query, "court", type_hint)` for court-specific examples
- HyDE generates court consideration style text (Erwägung)
- Searches `courts_index` instead of `laws_index`

##### Tool Override

```python
TOOLS = {
    "search_laws": HyDELawSearchTool(...),
    "search_courts": HyDECourtSearchTool(...),
}
```
The TOOLS dict is **overwritten** — same keys, new tool objects. The ReAct agent code (Cell 22) uses `TOOLS[action_lower]`, so it automatically picks up the enhanced tools without any code changes.

#### Cell 20 (Code) — Test HyDE + Hierarchical Search
Runs a comparison test:
1. Generates hypothetical law article and court consideration for a test query
2. Compares HyDE-enhanced search vs baseline keyword-only search
3. Shows overlap analysis: how many citations are shared, HyDE-only, keyword-only

---

### Phase H: ReAct Agent + Type Injection (Cells 21–24)

#### Cell 21 (Markdown) — Section Header: "Define ReAct Agent"

#### Cell 22 (Code) — ReAct Agent (~400 lines)

##### `AGENT_SYSTEM_PROMPT`

Written entirely in German. Key components:

```
1. Tool descriptions (search_laws, search_courts)
2. Instruction: "IMMER auf Deutsch suchen"
3. Response format: Thought → Action → Action Input
4. 4 worked examples:
   - Contract law (Vertragsrecht → OR)
   - Criminal law (Strafrecht → StGB)
   - Family law (Familienrecht → ZGB)
   - Tenancy law (Mietrecht → OR)
5. Closing instruction: "Suche IMMER auf Deutsch. Rufe beide Tools auf."
```

The examples show the LLM HOW to include type abbreviations in its queries (e.g., `"Vertrag Abschluss Voraussetzungen OR"`).

##### `parse_all_agent_actions(response)`

Regex parser that extracts ALL `(Action, Action Input)` pairs from a single LLM response. The LLM sometimes outputs multiple actions in one turn.

Pattern: `Action:\s*(\w+)` followed by `Action Input:\s*(.+?)` up to the next `Action:` or end of string.

##### `extract_citations_from_text(text)`

Regex citation extractor — used to find citations in the LLM's final answer text:
- `SR \d{3}...` — SR numbers
- `BGE \d+ [IVX]+ \d+` — BGE citations
- `Art. \d+ [A-Z]{2,}` — Article citations

##### `truncate_observation_for_llm(observation, max_chars=1200)`

Tool output can be very long (40 search results × 300 chars = 12,000 chars). This truncates to 1200 chars **only for the LLM's context window**. The full observation is preserved in logs and used for citation extraction.

##### `truncate_conversation(conversation, max_chars)`

If the accumulated conversation exceeds the budget (28,000 chars), keeps the system prompt + most recent conversation, dropping the middle.

##### `run_agent(query, verbose)` — The Main Loop

```
Input: English legal question
Output: (list of citation strings, list of log dicts)

1. Format initial conversation:
   "[INST] {SYSTEM_PROMPT}\n\nQuery: {query}\n\nThought: [/INST]"

2. FOR iteration in range(max_iterations=3):
   
   a. Truncate conversation if needed (stay within 28K chars)
   
   b. LLM generates response (stops at "Observation:" or "[INST]" or "</s>"):
      "Ich suche nach Vertragsvoraussetzungen im Obligationenrecht.\n
       Action: search_laws\n
       Action Input: Vertrag Abschluss Voraussetzungen OR"
   
   c. Error handling: if context window overflow, aggressively truncate to 20K and retry
   
   d. Parse ALL actions from response (may be multiple)
   
   e. FOR EACH action:
      - Look up tool in TOOLS dict
      - Call tool(action_input):
        → detect_law_type("Vertrag Abschluss Voraussetzungen OR") = "OR"
        → select_few_shot_examples(query, "law", type_hint="OR") = 3 OR-specific examples
        → generate_hypothetical_document(..., matched_examples) = German law text
        → hierarchical_bm25_search(hyde_doc, type_hint="OR") → boosted results
        → hierarchical_bm25_search(query, type_hint="OR") → boosted results  
        → merge + format with CCH labels
      - Extract citations via tool.get_last_citations()
      - Truncate observation for LLM context
   
   f. Append observations to conversation:
      "Tool search_laws: [Type boost: OR (explicit)]\n
       - [OR] Art. 1 Abs. 1 OR: Zum Abschluss eines Vertrages...\n
       - [OR] Art. 2 OR: ...\n
       [INST] Continue your analysis. [/INST]\n\nThought:"
   
   g. Check for "Final Answer:" in response → extract citations → break
   
   h. If no actions and no final answer → extract citations from text → break

3. Deduplicate all collected citations
4. Return (unique_citations, logs)
```

**How citations are collected (two paths)**:
1. **Tool path**: `tool.get_last_citations()` returns exact citation strings from the BM25 results. These are the **most reliable** — they come directly from the corpus.
2. **Regex path**: `extract_citations_from_text(response)` finds citations mentioned in the LLM's text output. These are **less reliable** but catch citations the LLM recalls from context.

#### Cell 23 (Code) — Inject Type Registry into Agent Prompt

```python
AGENT_SYSTEM_PROMPT += f"""
=== VERFÜGBARE RECHTSQUELLEN IM KORPUS ===

Gesetzestypen (häufigste, mit Dokumentanzahl):
OTHER(84000), OR(3700), FINMA(2700), ZGB(2400), ...

Gerichtstypen:
CASE_6B(318000), CASE_2C(317000), ...BGE_I(19000), ...

TIPP: Verwende den Gesetzestyp (z.B. OR, ZGB, StGB, BV, FINMA, USG) 
als Stichwort in deiner Suchanfrage.
"""
```

**Why this matters**: Without this, the LLM only knows types it saw during pre-training (OR, ZGB, StGB — the common ones). It has no idea that FINMA, USG, AHVG, ArG, etc. exist in the corpus. By injecting the registry with document counts, the LLM can:
1. Include the right abbreviation when it recognizes the legal domain
2. See which types are large (OR: 3700 docs) vs niche (RuVAG: 10 docs)
3. Recognize that non-leading court types like `CASE_1C` exist (not just BGE)

#### Cell 24 (Code) — Test Agent
Runs the full agent pipeline on a single test query with `verbose=True` to show the Thought/Action/Observation trace.

---

### Phase I: Inference & Evaluation (Cells 25–36)

#### Cell 25 (Markdown) — Section Header: "Load Test Data"

#### Cell 26 (Code) — Load Queries
Loads `val.csv` or `test.csv` (depending on `DATASET_MODE`). Shows column info and whether gold citations are available.

#### Cell 27 (Markdown) — Section Header: "Generate Predictions"

#### Cell 28 (Code) — Run Agent on All Queries
```python
for _, row in tqdm(test_df.iterrows()):
    citations, logs = run_agent(row["query"], verbose=False)
    predictions.append({"query_id": row["query_id"], "predicted_citations": ";".join(citations)})
```

Iterates all queries, runs the full HyDE + Hierarchical + ReAct pipeline on each, collects predictions.

#### Cell 29 (Code) — Preview Predictions DataFrame

#### Cell 30 (Markdown) — Section Header: "Create Submission"

#### Cell 31 (Code) — Save Submission
Saves `output/submission_hyde.csv` with columns `query_id, predicted_citations`.

#### Cell 32 (Code) — Evaluation Functions (~200 lines)

Three evaluation functions:

**`citation_f1(predicted, gold)`** — Single-query F1:
```
precision = |pred ∩ gold| / |pred|
recall    = |pred ∩ gold| / |gold|
f1        = 2 * P * R / (P + R)
```

**`macro_f1(predictions, gold)`** — Average F1 across all queries (THE competition metric):
```
macro_f1 = (1/N) * Σ f1_i
```

**`micro_f1(predictions, gold)`** — Aggregate TP/FP/FN across all queries:
```
micro_precision = total_TP / (total_TP + total_FP)
micro_recall    = total_TP / (total_TP + total_FN)
```

**`evaluate_submission(submission_df, gold_df)`** — Full evaluation:
- Merges prediction and gold DataFrames on `query_id`
- Parses citation strings (`;`-separated)
- Computes macro and micro F1
- Prints per-sample TP/FP/FN breakdown

#### Cell 33 (Markdown) — Section Header: "Local Evaluation"

#### Cell 34 (Code) — Run Evaluation
Only runs if `IS_VALIDATION_MODE=True` and gold labels exist. Prints:
```
EVALUATION RESULTS
Macro F1 (PRIMARY): 0.XXXX
Macro Precision:    0.XXXX
Macro Recall:       0.XXXX
```

#### Cell 35 (Markdown) — Summary
Lists all enhancements and potential further improvements (multiple HyDE docs, embedding search, dynamic few-shot selection, iterative HyDE).

#### Cell 36 (Code) — Run on Test Set
If `test.csv` exists, runs the full pipeline on the test set and saves `output/test_submission.csv`.

---

## 4. Data Flow: End-to-End for a Single Query

Here's what happens when the agent processes:
> **"What are the requirements for contract termination in Swiss law?"**

```
STEP 1: AGENT RECEIVES QUERY
  ┌─────────────────────────────────────────────────────────────┐
  │ [INST] {SYSTEM_PROMPT + TYPE_REGISTRY}                      │
  │                                                             │
  │ Query: What are the requirements for contract termination   │
  │        in Swiss law?                                        │
  │                                                             │
  │ Thought: [/INST]                                            │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
STEP 2: LLM GENERATES THOUGHT + ACTION
  "Ich suche nach Vertragskündigung im Obligationenrecht.
   Action: search_laws
   Action Input: Vertrag Kündigung Voraussetzungen OR"
                              │
                              ▼
STEP 3: AGENT PARSES ACTION
  action = "search_laws"
  action_input = "Vertrag Kündigung Voraussetzungen OR"
  tool = TOOLS["search_laws"]  →  HyDELawSearchTool
                              │
                              ▼
STEP 4: HyDELawSearchTool.run("Vertrag Kündigung Voraussetzungen OR")

  4a. TYPE DETECTION (Level 1):
      detect_law_type("Vertrag Kündigung Voraussetzungen OR")
      → Regex finds \bOR\b → type_hint = "OR"

  4b. DOMAIN-MATCHED FEW-SHOT SELECTION (NEW in v2):
      select_few_shot_examples("Vertrag Kündigung...", "law", type_hint="OR")
      → Priority 1: type_hint="OR" found in law_few_shot_bank
      → Returns law_few_shot_bank["OR"] = [ex1, ex2, ex3] (3 OR-specific examples)
      → Each example has query_en for the keyword matching fallback path

  4c. HyDE GENERATION:
      build_hyde_prompt(query, "law", matched_examples)
      → "[INST] Du bist ein Schweizer Rechtsexperte...
              Beispiele:
              Frage: {OR_example_1.query}
              Hypothetischer Text: {OR_example_1.text}
              Frage: {OR_example_2.query}
              Hypothetischer Text: {OR_example_2.text}
              Frage: {OR_example_3.query}
              Hypothetischer Text: {OR_example_3.text}
              ...
              Frage: Vertrag Kündigung Voraussetzungen OR
              Hypothetischer Text: [/INST]"
      
      llm(prompt, max_tokens=300, temperature=0.3)
      → hyde_doc = "Art. X. Die Kündigung eines Vertrages bedarf 
         keiner Begründung, sofern die gesetzlichen Fristen 
         eingehalten werden. Die Kündigung ist schriftlich 
         zu erklären und dem Vertragspartner zuzustellen..."

  4d. HIERARCHICAL BM25 — HyDE path:
      scores = BM25Okapi.get_scores(tokenize(hyde_doc))
      → [0.0, 0.0, ..., 12.4, ..., 8.7, ...]  (175K scores)
      
      Auto-detect: detect_dominant_type(scores, doc_types)
      → type_hint already set, skip auto-detect
      
      Soft boost:
      boost_mask = [1.0, 1.0, ..., 1.5, ..., 1.0, ...]
                   (1.5 where doc_type=="OR", 1.0 elsewhere)
      scores = scores * boost_mask
      → OR docs get 1.5x boost, others unchanged
      
      top_indices = scores.argsort()[-40:][::-1]
      → 40 results, mostly OR docs (boosted) but ZGB/StGB can still appear

  4e. HIERARCHICAL BM25 — Keyword path:
      Same process with original query "Vertrag Kündigung Voraussetzungen OR"
      Same type_hint="OR", same boost

  4f. MERGE:
      HyDE results: 40 citations
      Keyword results: 40 citations
      Union: ~60 unique (some overlap)
      
      Sort order:
      1. Found by BOTH HyDE and keyword (highest confidence)
      2. Found by HyDE only
      3. Found by keyword only

  4g. CCH FORMAT:
      "[Type boost: OR (explicit)]
       - [OR] Art. 266a Abs. 1 OR: Die Kündigung ist mitteilung...
       - [OR] Art. 266 OR: Die Dauer des Mietverhältnisses...
       - [ZGB] Art. 1 ZGB: Das Gesetz findet auf..."

                              │
                              ▼
STEP 5: AGENT RECEIVES OBSERVATION
  Observation is truncated to 1200 chars for LLM context.
  Full observation preserved in logs for citation extraction.
  
  Citations collected: tool.get_last_citations()
  → ["Art. 266a Abs. 1 OR", "Art. 266 OR", "Art. 1 ZGB", ...]

                              │
                              ▼
STEP 6: NEXT ITERATION (if max_iterations not reached)
  LLM sees results, decides to search courts:
  "Thought: Jetzt suche ich nach BGE zur Vertragskündigung.
   Action: search_courts
   Action Input: Vertrag Kündigung Voraussetzungen"
  
  → Same HyDE + Hierarchical flow for courts index
  → More citations collected

                              │
                              ▼
STEP 7: FINAL ANSWER or MAX ITERATIONS
  All citations deduplicated.
  Return: (["Art. 266a Abs. 1 OR", "Art. 266 OR", "BGE 140 III 496 E. 4.1", ...], logs)
```

---

## 5. The Three RAG Techniques Combined

| Technique | Original (NirDiamant) | Our Adaptation | Where in Code |
|-----------|----------------------|----------------|---------------|
| **HyDE** | Generate hypothetical doc, embed with dense vectors, search vector store | Generate hypothetical German legal text, search BM25 with it | `generate_hypothetical_document()` → `hierarchical_bm25_search()` |
| **Hierarchical Indices** | Two vector stores: summary-level + chunk-level. Search summaries first, then filter chunks by page | Two-level BM25: detect type first (Level 1), then soft-boost type-matching docs (Level 2) | `detect_law_type()` / `detect_dominant_type()` → `scores * boost_mask` |
| **Contextual Chunk Headers** | Prepend document title to each chunk before embedding → better retrieval relevance | Prepend `[TYPE]` label to each search result → LLM understands document provenance | `formatted.append(f"- [{doc_type_label}] {citation}: {text}")` |

**Why we don't use vector stores / embeddings**: Competition constraint — 12hr runtime, no internet, limited compute. BM25 is instant (numpy operations), needs no GPU for indexing, and works surprisingly well for legal text where terms are distinctive. HyDE bridges the vocabulary gap that BM25 would otherwise miss.

---

## 6. Key Data Structures Reference

| Variable | Type | Shape/Size | Description |
|----------|------|------------|-------------|
| `laws_index` | `BM25Index` | ~175K docs | Laws BM25 index |
| `courts_index` | `BM25Index` | 100K docs (capped) | Courts BM25 index |
| `laws_index.documents` | `list[dict]` | 175K × {citation, text} | Raw law documents |
| `laws_index.doc_types` | `np.ndarray` | (175K,) dtype=object | Type label per law doc |
| `courts_index.doc_types` | `np.ndarray` | (100K,) dtype=object | Type label per court doc |
| `LAW_TYPE_REGISTRY` | `dict` | 656 entries | type → {count, example} |
| `COURT_TYPE_REGISTRY` | `dict` | 59 entries | type → {count, example} |
| `law_few_shot_bank` | `dict` | type → list[dict] | type → [3 examples], each with query, query_en, citation, text, source |
| `court_few_shot_bank` | `dict` | type → list[dict] | type → [3 examples], same structure |
| `selected_law_examples` | `list[dict]` | ~N entries | Flat list fallback: {query, query_en, citation, text, source} |
| `selected_court_examples` | `list[dict]` | ~M entries | Flat list fallback: {query, query_en, citation, text, source} |
| `_hyde_cache` | `dict` | Grows during inference | MD5(query:type) → generated text |
| `TOOLS` | `dict` | 2 entries | "search_laws" → HyDELawSearchTool, "search_courts" → HyDECourtSearchTool |
| `AGENT_SYSTEM_PROMPT` | `str` | ~3K+ chars | German system prompt + type registry |
| `llm` | `Llama` | ~4GB VRAM | Mistral-7B GGUF callable |

---

## 7. Configuration Reference

```python
CONFIG = {
    # === Model ===
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "n_ctx": 16384,             # 16K context window
    "n_threads": 4,             # CPU threads
    "n_gpu_layers": -1,         # -1 = all on GPU
    
    # === Agent ===
    "max_iterations": 3,        # ReAct loops per query
    "max_tokens": 512,          # Tokens per LLM generation
    "temperature": 0.1,         # Low = deterministic routing
    "max_observation_chars": 1200,  # Tool output truncation for LLM
    "max_conversation_chars": 28000, # Total conversation budget
    
    # === Retrieval ===
    "top_k_laws": 40,           # BM25 results per law search
    "top_k_courts": 40,         # BM25 results per court search
    
    # === HyDE ===
    "hyde_enabled": True,       # Master toggle (False for ablation)
    "hyde_max_tokens": 300,     # Tokens for hypothetical doc
    "hyde_temperature": 0.3,    # Slightly creative for vocab
    "hyde_few_shot_count": 3,   # Examples per HyDE prompt (now domain-matched)
    "hyde_examples_per_type": 3, # Examples stored per type in bank
    "hyde_target_chars_law": 300,   # Target: hypothetical law text
    "hyde_target_chars_court": 400, # Target: hypothetical court text
    "hyde_max_synthetic_types": 50, # Cap on synthetic query generation per corpus (increased from 20)
    
    # === Hierarchical Search ===
    "type_boost_factor": 1.5,        # Score multiplier for type match
    "type_auto_detect": True,        # Auto-detect from results
    "type_dominant_threshold": 0.4,  # Fraction to trigger auto-detect
}
```

### Ablation Testing Knobs

| To test... | Set... | Effect |
|------------|--------|--------|
| Keyword-only (no HyDE) | `hyde_enabled: False` | `generate_hypothetical_document()` returns original query |
| No type boosting | `type_boost_factor: 1.0` | Boost mask is all 1.0 = no effect |
| No auto-detect | `type_auto_detect: False` | Only explicit regex detection |
| More/fewer results | `top_k_laws/courts: N` | More docs = higher recall, lower precision |
| More few-shot examples | `hyde_few_shot_count: 5` | Longer HyDE prompt, potentially better generation |
| More examples per type | `hyde_examples_per_type: 5` | 5 stored examples per type in bank (more diversity) |
| More type coverage | `hyde_max_synthetic_types: 100` | More synthetic queries, longer Cell 15 runtime |
