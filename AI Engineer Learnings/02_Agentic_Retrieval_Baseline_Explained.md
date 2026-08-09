# 02: Agentic Retrieval Baseline — Cell-by-Cell Breakdown

> **Notebook:** `02_agentic_retrieval_baseline.ipynb`  
> **Architecture:** ReAct Agent with BM25 Search Tools (first true RAG system)  
> **Status:** Original, unmodified (created May 4, 2026)  
> **Key Concept:** This is your first **Agentic RAG** — the LLM decides WHAT to search, EXECUTES the search, OBSERVES results, and ITERATES.

---

## The Big Picture: From Direct Generation to Retrieval-Augmented Generation

```
NOTEBOOK 01 (Direct Generation):
  Question → LLM → Citations (from memory only)
  Problem: Hallucination — LLM invents non-existent citations

NOTEBOOK 02 (This — Agentic RAG):
  Question → LLM reasons → Calls search tool → Gets real documents
           → LLM reasons again → Calls another tool → Gets more documents
           → Extracts citations from REAL results
  Advantage: Grounded in actual corpus — no hallucination of non-existent articles
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FULL SYSTEM ARCHITECTURE                              │
│                                                                             │
│  INPUT                                                                      │
│  ══════                                                                     │
│  English legal question from user                                           │
│  e.g. "Under what conditions can pre-trial detention be extended?"          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LLM ENGINE (Mistral-7B-Instruct-v0.2, Q4_K_M quantized)                  │
│  ════════════════════════════════════════════════════════                    │
│  • Runtime: llama-cpp-python (C++ inference via Python bindings)            │
│  • Hardware: GPU (all 32 layers offloaded via CUDA)                         │
│  • Context: 8192 tokens                                                     │
│  • Format: [INST] system + query [/INST] → generation                      │
│  • Language: Prompt in GERMAN (agent thinks/searches in German)             │
│  • Temperature: 0.1 (mostly deterministic, slight exploration)              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ReAct AGENT LOOP (max 3 iterations)                                        │
│  ═══════════════════════════════════                                         │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  ITERATION 1                                                      │      │
│  │                                                                    │      │
│  │  ┌────────────┐     ┌──────────────┐     ┌───────────────────┐  │      │
│  │  │  THOUGHT   │────▶│    ACTION    │────▶│   TOOL EXECUTION  │  │      │
│  │  │ (LLM gen)  │     │  search_laws │     │  BM25 search over │  │      │
│  │  │            │     │  "Haft StPO" │     │  269K law articles │  │      │
│  │  └────────────┘     └──────────────┘     └─────────┬─────────┘  │      │
│  │                                                      │            │      │
│  │                                          ┌───────────▼─────────┐ │      │
│  │                                          │    OBSERVATION      │ │      │
│  │                                          │ "Art. 221 StPO:..." │ │      │
│  │                                          │ (truncated to 1200  │ │      │
│  │                                          │  chars for LLM)     │ │      │
│  │                                          └─────────────────────┘ │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  ITERATION 2                                                      │      │
│  │                                                                    │      │
│  │  ┌────────────┐     ┌───────────────┐     ┌──────────────────┐  │      │
│  │  │  THOUGHT   │────▶│    ACTION     │────▶│  TOOL EXECUTION  │  │      │
│  │  │ "Now search│     │ search_courts │     │  BM25 search over│  │      │
│  │  │  courts"   │     │ "Haft BGE"    │     │  100K court docs │  │      │
│  │  └────────────┘     └───────────────┘     └────────┬─────────┘  │      │
│  │                                                      │            │      │
│  │                                          ┌───────────▼─────────┐ │      │
│  │                                          │    OBSERVATION      │ │      │
│  │                                          │ "BGE 137 IV 122:..."│ │      │
│  │                                          └─────────────────────┘ │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  ITERATION 3                                                      │      │
│  │                                                                    │      │
│  │  ┌────────────┐     ┌───────────────┐     ┌──────────────────┐  │      │
│  │  │  THOUGHT   │────▶│    ACTION     │────▶│  TOOL EXECUTION  │  │      │
│  │  │ "Search    │     │  search_laws  │     │  BM25 search     │  │      │
│  │  │  related"  │     │ "Rechtsmittel"│     │  (different       │  │      │
│  │  └────────────┘     └───────────────┘     │   query terms)   │  │      │
│  │                                            └────────┬─────────┘  │      │
│  │                                                      │            │      │
│  │                                          ┌───────────▼─────────┐ │      │
│  │                                          │    OBSERVATION      │ │      │
│  │                                          │ "Art. 382 StPO:..." │ │      │
│  │                                          └─────────────────────┘ │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SEARCH ENGINE: BM25Okapi (rank_bm25 library)                              │
│  ═════════════════════════════════════════════                               │
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │  LAWS INDEX                      │  │  COURTS INDEX                    │  │
│  │  • Source: laws_de.csv (73MB)    │  │  • Source: court_considerations  │  │
│  │  • Docs: 269,000 articles        │  │    .csv (2.4GB)                  │  │
│  │  • Format: "Art. X Abs. Y Gesetz"│  │  • Docs: 100,000 (of 2.5M!)     │  │
│  │  • Language: German               │  │  • Format: "BGE X Y Z E. N"     │  │
│  │  • Tokenizer: lowercase +        │  │  • Language: German              │  │
│  │    split on \W+ (naive)          │  │  • Tokenizer: same (naive)       │  │
│  │  • Cached: laws_index.pkl         │  │  • Cached: courts_index.pkl      │  │
│  │  • top_k: 40 results/search      │  │  • top_k: 40 results/search     │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
│  BM25 Scoring Formula:                                                      │
│  score(q,d) = Σ IDF(t) × [f(t,d)×(k1+1)] / [f(t,d)+k1×(1-b+b×|d|/avgdl)]│
│  Where: k1=1.5, b=0.75, IDF=log((N-df+0.5)/(df+0.5))                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CITATION EXTRACTION (runs AFTER all iterations)                            │
│  ═══════════════════════════════════════════════                             │
│                                                                             │
│  Source 1: tool.get_last_citations()                                        │
│    → Structured: all citation fields from BM25 results                      │
│    → Collected during each tool execution                                   │
│                                                                             │
│  Source 2: extract_citations_from_text(llm_response)                        │
│    → Regex patterns applied to LLM's "Final Answer" text:                   │
│      • BGE pattern: BGE \d+ [IVX]+ \d+ (E\. [\d.]+)?                      │
│      • Art pattern: Art\. \d+[a-z]? (Abs\. \d+)? [A-Z]{2,}                │
│      • SR pattern: SR \d{3}(\.\d+)?                                        │
│                                                                             │
│  Deduplication: list(set(all_citations))                                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OUTPUT                                                                     │
│  ══════                                                                     │
│  submission.csv:                                                            │
│  ┌────────────┬──────────────────────────────────────────┐                  │
│  │ query_id   │ predicted_citations                       │                  │
│  ├────────────┼──────────────────────────────────────────┤                  │
│  │ val_001    │ Art. 221 Abs. 1 StPO;BGE 137 IV 122;... │                  │
│  └────────────┴──────────────────────────────────────────┘                  │
│                                                                             │
│  Evaluation: Macro F1 (primary), Micro F1 (secondary)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


LANGUAGE FLOW:
══════════════
  User Question (ENGLISH)
       │
       ▼
  Agent System Prompt (GERMAN) ─── "Du bist ein Schweizer Rechtsrecherche..."
       │
       ▼
  Agent Thoughts (GERMAN) ─── "Ich suche nach Haftverlängerung..."
       │
       ▼
  Search Queries (GERMAN) ─── "Haft Verlängerung StPO"
       │
       ▼
  BM25 Index (GERMAN corpus) ─── matches German tokens
       │
       ▼
  Results (GERMAN) ─── "Art. 221 Abs. 1 StPO: Die Untersuchungshaft..."
       │
       ▼
  Output Citations (LANGUAGE-NEUTRAL) ─── "Art. 221 Abs. 1 StPO"


TECHNOLOGY STACK:
═════════════════
┌─────────────────┬───────────────────────────────────────────────────┐
│ Component        │ Technology                                         │
├─────────────────┼───────────────────────────────────────────────────┤
│ LLM             │ Mistral-7B-Instruct-v0.2 (GGUF Q4_K_M, ~4GB)    │
│ Inference       │ llama-cpp-python (C++ backend, CUDA GPU)          │
│ Search          │ BM25Okapi (rank_bm25 Python library)             │
│ Tokenization    │ Naive: lowercase + regex split on \W+             │
│ Serialization   │ pickle (.pkl index cache files)                   │
│ Data Loading    │ pandas (chunked CSV reading)                      │
│ Agent Pattern   │ ReAct (Reason + Act, 3 iterations)               │
│ Prompt Format   │ Mistral [INST]...[/INST] chat template           │
│ Prompt Language │ German (agent + search queries)                   │
│ Corpus Language │ German (laws + court decisions)                   │
│ Query Language  │ English (user input)                              │
│ Output Format   │ CSV, semicolon-separated citations                │
│ Metric          │ Macro F1 (precision-recall harmonic mean)         │
│ Platform        │ Kaggle (T4 GPU, 30GB RAM, 12hr limit)            │
└─────────────────┴───────────────────────────────────────────────────┘


DATA FLOW (per query, ~15-30 seconds):
══════════════════════════════════════
  1. English question enters
  2. Formatted into [INST] German system prompt + query [/INST]
  3. LLM generates Thought + Action + Action Input (in German)
  4. Action parsed → tool called → BM25 searches German corpus
  5. Results (top 40) → citations extracted → observation truncated
  6. Observation appended to conversation
  7. Repeat steps 3-6 for up to 3 iterations
  8. All collected citations deduplicated
  9. Output as semicolon-joined string
```

---

## Cell 1: Markdown Introduction

Describes the approach and its advantages over direct generation:
- **Grounded** in actual legal documents
- **Less hallucination** (citations come from real search results)
- **Iterative** (can refine searches based on what it finds)

---

## Cell 2: Setup & Configuration

```python
DATASET_MODE = "val"
FORCE_REBUILD_INDICES = False

# New paths vs notebook 01:
INDEX_PATH = REPO_ROOT / "data" / "processed"  # BM25 index cache
LAWS_CSV = DATA_PATH / "laws_de.csv"            # 73MB, ~269K articles
COURTS_CSV = DATA_PATH / "court_considerations.csv"  # 2.4GB, ~2.5M decisions
```

### What's New vs Notebook 01

| Notebook 01 | Notebook 02 |
|-------------|-------------|
| No corpus needed | Loads 73MB laws + 2.4GB courts |
| No index | Builds BM25 search indices |
| No caching | Caches indices as `.pkl` files |

**Key Addition:** `FORCE_REBUILD_INDICES = False`
- First run: builds index from CSV (slow: 15-20 min for courts)
- Subsequent runs: loads cached pickle (fast: <10 sec)
- **Pattern:** Expensive computations should always be cached

---

## Cell 3: CONFIG

```python
CONFIG = {
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "n_ctx": 8192,              # 2× notebook 01's 4096!
    "n_threads": 4,
    "n_gpu_layers": -1,
    
    # Agent settings (NEW)
    "max_iterations": 3,        # Agent loops max 3 times
    "max_tokens": 512,
    "temperature": 0.1,         # Slightly > 0 (was 0.0 in nb01)
    "max_observation_chars": 1200,    # Truncate search results for LLM
    "max_conversation_chars": 28000,  # Safety net for context overflow
    
    # Retrieval settings (NEW)
    "top_k_laws": 40,           # BM25 returns top 40 law results
    "top_k_courts": 40,         # BM25 returns top 40 court results
}
```

### New Parameters Explained

**`n_ctx: 8192` (doubled from 4096)**
- Agent conversations grow with each iteration (prompt + responses + observations)
- Each iteration adds ~1000-2000 tokens of observation text
- 3 iterations × ~2000 = ~6000 tokens of observations + ~2000 prompt = needs 8192
- **Rule:** For agentic systems, context window must accommodate: `system_prompt + max_iterations × (response + observation)`

**`max_iterations: 3`**
- How many Thought→Action→Observation loops the agent runs
- More iterations = more searches = more citations found
- But also: more tokens consumed, more time, more risk of going off-track
- **Tradeoff:** 3 is conservative. Our later notebooks use 3-6.

**`temperature: 0.1` (was 0.0)**
- Slight randomness helps the agent generate DIFFERENT search queries each iteration
- At 0.0, the agent might repeat the same search
- At 0.1, it's still mostly deterministic but can vary its approach
- **Interview Q:** "Why use temperature > 0 for an agent but 0 for direct generation?"  
  **A:** "Agents need to explore — slight randomness prevents repetitive loops. Direct generation needs precision — you want the single best answer."

**`max_observation_chars: 1200`**
- BM25 returns 40 results × ~300 chars each = 12,000 chars per tool call
- 12,000 chars would overflow the context window in 1 iteration
- Solution: Truncate what the LLM SEES to 1200 chars, but keep full results for citation extraction
- **Critical pattern:** The LLM sees a summary; the code extracts from the full data

**`max_conversation_chars: 28000`**
- Safety net: if conversation grows beyond this, aggressively truncate old parts
- At ~4 chars/token: 28000 chars ≈ 7000 tokens (leaves 1192 tokens for generation in 8192 window)
- **This is defensive programming** — prevents the "context overflow" crash

**`top_k_laws/courts: 40`**
- BM25 returns top 40 results per search
- Why 40? Balances recall (finding gold citations) vs noise (irrelevant results)
- Higher = more likely to find correct articles but more false positives

---

## CONTEXT WINDOW BUDGET — Complete Breakdown

This is how EVERY token in the 8192-token window is allocated across the agent's lifecycle:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT WINDOW: 8192 TOKENS                           │
│                    (≈ 28,000 characters at ~3.4 chars/token)             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── SYSTEM PROMPT (fixed, ~2800 chars = ~820 tokens) ──────────────┐ │
│  │  [INST]                                                            │ │
│  │  "Du bist ein Schweizer Rechtsrecherche-Assistent..."              │ │
│  │  + tool descriptions (search_laws, search_courts)                  │ │
│  │  + format rules (Thought/Action/Action Input)                      │ │
│  │  + 4 full examples (Vertragsrecht, Strafrecht, Familien, Miet)    │ │
│  │  + final instruction                                               │ │
│  │  [/INST]                                                           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── QUERY (variable, ~50-200 chars = ~15-60 tokens) ───────────────┐ │
│  │  "Query: Under what conditions can pre-trial detention..."         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── ITERATION 1 ──────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  LLM Response (~200-400 chars = ~60-120 tokens)                   │  │
│  │  "Thought: Ich suche nach Haftverlängerung im StPO\n              │  │
│  │   Action: search_laws\n                                            │  │
│  │   Action Input: Haft Verlängerung Untersuchungshaft StPO"          │  │
│  │                                                                    │  │
│  │  Observation (TRUNCATED to 1200 chars = ~350 tokens)              │  │
│  │  "- Art. 221 Abs. 1 StPO: Die Untersuchungshaft...\n             │  │
│  │   - Art. 227 Abs. 1 StPO: Das zuständige Gericht...\n            │  │
│  │   ... (truncated, 10800 chars remaining)"                          │  │
│  │                                                                    │  │
│  │  [INST] Continue your analysis. [/INST]                            │  │
│  │                                                                    │  │
│  └─── Subtotal: ~1600 chars = ~470 tokens ───────────────────────────┘  │
│                                                                         │
│  ┌─── ITERATION 2 ──────────────────────────────────────────────────┐  │
│  │  LLM Response + Observation (same structure)                       │  │
│  └─── Subtotal: ~1600 chars = ~470 tokens ───────────────────────────┘  │
│                                                                         │
│  ┌─── ITERATION 3 ──────────────────────────────────────────────────┐  │
│  │  LLM Response + Observation (same structure)                       │  │
│  └─── Subtotal: ~1600 chars = ~470 tokens ───────────────────────────┘  │
│                                                                         │
│  ┌─── GENERATION BUDGET (reserved for LLM output) ───────────────────┐ │
│  │  max_tokens: 512                                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TOKEN BUDGET MATH:                                                     │
│  ═════════════════                                                      │
│                                                                         │
│  System prompt:           ~820 tokens   (fixed)                         │
│  Query:                   ~60 tokens    (variable)                       │
│  Iteration 1:            ~470 tokens   (response + truncated obs)       │
│  Iteration 2:            ~470 tokens   (response + truncated obs)       │
│  Iteration 3:            ~470 tokens   (response + truncated obs)       │
│  Generation reserve:      512 tokens   (max_tokens setting)             │
│  ──────────────────────────────────────────────────────────────         │
│  TOTAL USED:            ~2802 tokens                                    │
│  TOTAL AVAILABLE:        8192 tokens                                    │
│  HEADROOM:              ~5390 tokens   (comfortable!)                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### The 4 Limits That Prevent Overflow

```
LIMIT 1: max_observation_chars = 1200
├── WHERE: Observation text sent to LLM after each tool call
├── WHY: BM25 returns 40 results × ~300 chars = 12,000 chars raw
│         Without truncation: 1 tool call fills entire context window
├── HOW: observation[:1200] + "\n... (truncated, X chars remaining)"
├── IMPORTANT: Full observation is STILL used for citation extraction!
│              Only the LLM's view is truncated, not the data pipeline
└── IMPACT: Each observation adds ~350 tokens instead of ~3500

LIMIT 2: max_conversation_chars = 28000
├── WHERE: Total conversation string (system + all iterations combined)
├── WHY: Safety net — if LLM generates unexpectedly long responses,
│         or observations are larger than expected, this catches it
├── HOW: truncate_conversation() keeps system prompt + most recent turns,
│         drops middle content: "...[earlier conversation truncated]..."
├── TRIGGERS: Only if conversation exceeds 28000 chars (~7000 tokens)
│             Leaves ~1192 tokens for generation (8192 - 7000)
└── IMPACT: Rarely triggers in normal operation (budget above shows ~9600 chars typical)

LIMIT 3: max_tokens = 512
├── WHERE: LLM generation output per call
├── WHY: Caps how much the LLM can write before we take back control
├── HOW: llama.cpp stops generation after 512 tokens regardless
├── WHAT FITS: A Thought (20 tokens) + Action (5 tokens) + 
│              Action Input (15 tokens) + extra reasoning (472 tokens)
│              512 is generous for a single agent step
└── IMPACT: Prevents runaway generation; LLM usually stops at ~100-200 tokens
            due to stop=["Observation:"] hitting first

LIMIT 4: max_iterations = 3
├── WHERE: Agent loop count
├── WHY: Caps total context growth (each iteration adds ~470 tokens)
├── HOW: for iteration in range(3): ...
├── EFFECT: 3 iterations × ~470 tokens = ~1410 tokens of accumulated state
│           Well within budget even with generous system prompt
└── TRADEOFF: More iterations = more citations found, but diminishing returns
              after iteration 2 (agent starts repeating queries)
```

### What Happens When Limits Are Hit

```
SCENARIO 1: Normal operation (most queries)
  Total: ~2800 tokens used of 8192 → NO truncation anywhere

SCENARIO 2: Long LLM responses (agent rambles)
  Each response is ~400 tokens instead of ~100
  3 iterations × 400 + observations + system = ~4200 tokens → Still fine

SCENARIO 3: Context overflow (edge case)
  Conversation exceeds 28000 chars → truncate_conversation() fires
  Keeps: system prompt + last 2 iterations
  Drops: iteration 1 content
  LLM retries with shorter context

SCENARIO 4: Retry also overflows (extreme edge case)  
  Further truncate to 20000 chars → retry once more
  If still fails → return citations found so far (graceful degradation)
  NEVER crash — always return partial results
```

### Visual: What the LLM Sees vs What the Code Keeps

```
                    LLM SEES (truncated)              CODE KEEPS (full)
                    ════════════════════              ══════════════════
Tool output:        "- Art. 221 StPO: Die           All 40 results with
                     Untersuchungs...\n              full text (12,000+
                     - Art. 227 StPO: Das            chars), all 40
                     zuständige...\n                 citation strings
                     ... (truncated)"                extracted
                    ─────────────────                ─────────────────
                    ~1200 chars                      ~12,000 chars
                    ~350 tokens                      (never enters LLM)

Conversation:       System + last 2-3 turns         Full log of every
                    (fits in 8192 window)            iteration, every
                                                    tool call, every
                                                    citation found
                    ─────────────────                ─────────────────
                    ≤28000 chars                     Unlimited (in RAM)
```

**Interview Q:** "How do you prevent context overflow in an iterative LLM agent?"  
**A:** "Four layers of defense: (1) Truncate observations before injecting into context (show summary, keep full data separately). (2) Set a hard character limit on total conversation with truncation-from-middle strategy. (3) Cap generation length with max_tokens. (4) Limit iteration count. If all else fails, catch the overflow exception, truncate aggressively, and retry once. Never crash — always return partial results."

---

## Cell 4: BM25 Index (The Search Engine)

```python
class BM25Index:
    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        tokens = re.split(r"\W+", text)
        return [t for t in tokens if t]

    def build(self, documents: list[dict]) -> None:
        self._tokenized_corpus = [self.tokenize(doc["text"]) for doc in documents]
        self.index = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        query_tokens = self.tokenize(query)
        scores = self.index.get_scores(query_tokens)
        top_indices = scores.argsort()[-top_k:][::-1]
        return [self.documents[idx] for idx in top_indices if scores[idx] > 0]
```

### BM25 — The Algorithm (Interview Must-Know)

**What is BM25?**
- "Best Matching 25" — a probabilistic keyword matching algorithm
- The standard for sparse (keyword-based) retrieval
- Used by Elasticsearch, Solr, Lucene under the hood

**How it works (simplified):**
```
score(query, document) = Σ IDF(term) × TF(term, document) × normalization

Where:
- IDF(term) = log((N - df + 0.5) / (df + 0.5))  
  → Rare terms score higher ("Kollusionsgefahr" > "und")
  
- TF(term, doc) = (term_freq × (k1 + 1)) / (term_freq + k1 × (1 - b + b × |D|/avgDL))
  → Frequency matters but with diminishing returns
  → Longer documents are penalized (normalization by length)
```

**Interview Q:** "What's the difference between TF-IDF and BM25?"  
**A:** "BM25 is an evolution of TF-IDF. Key differences: (1) BM25 has saturation — term frequency has diminishing returns (controlled by k1). (2) BM25 has document length normalization (controlled by b). (3) BM25 handles the case where very frequent terms provide negative information. TF-IDF treats all frequency increases linearly."

**BM25 Parameters (from rank_bm25 library):**
- `k1 = 1.5` (default): Controls term frequency saturation. Higher = more weight on frequency.
- `b = 0.75` (default): Controls document length normalization. b=0 ignores length; b=1 fully normalizes.

**The Tokenizer (Critical Weakness):**
```python
def tokenize(self, text: str) -> list[str]:
    text = text.lower()
    tokens = re.split(r"\W+", text)  # Split on non-word characters
    return [t for t in tokens if t]
```
- This is a **naive tokenizer** — splits on whitespace/punctuation
- **Problem for German:** "Untersuchungs- und Sicherheitshaft" → ["untersuchungs", "und", "sicherheitshaft"]
- But query "Untersuchungshaft" → ["untersuchungshaft"] → **ZERO overlap!**
- This is why BM25 alone fails for German legal text (compound words don't match)
- **Fix (not implemented here):** German compound splitter, or character n-grams, or just use embeddings

---

## Cell 5-6: Build/Load Indices

```python
laws_index = get_or_build_index(
    name="laws", csv_path=LAWS_CSV, index_path=LAWS_INDEX_PATH,
    force_rebuild=FORCE_REBUILD_INDICES
)

courts_index = get_or_build_index(
    name="courts", csv_path=COURTS_CSV, index_path=COURTS_INDEX_PATH,
    max_rows=100000  # Only 100K of 2.5M rows!
)
```

### Key Design Decision: `max_rows=100000`

- Full court corpus: 2.5M documents (2.4GB CSV)
- Only loading 100K (4% of corpus!)
- **Why:** Memory + time constraints on Kaggle (30GB RAM, 12-hour limit)
- **Impact:** If a gold citation is in the other 96%, you can NEVER find it
- **This is the "8.1% coverage" problem** we identified later — a hard ceiling on recall

**The Caching Pattern:**
```python
def get_or_build_index(name, csv_path, index_path, force_rebuild=False):
    if index_path.exists() and not force_rebuild:
        return BM25Index.load(index_path)  # Fast: pickle load
    
    documents = load_csv_corpus(csv_path)  # Slow: parse CSV
    index = BM25Index(documents=documents)  # Slow: tokenize all docs
    index.save(index_path)                  # Cache for next time
    return index
```
- **Pattern name:** "Build once, load many" — essential for data pipelines
- Uses `pickle` for serialization (fast binary format)
- **Interview Q:** "How do you handle expensive pre-computations in ML pipelines?"  
  **A:** "Build once and cache to disk (pickle, parquet, or FAISS index files). Check cache existence before recomputing. Provide a force-rebuild flag for updates."

---

## Cell 7: Search Tools (Tool-Use Pattern)

```python
class LawSearchTool:
    name = "search_laws"
    description = """Search Swiss federal laws by keywords..."""

    def __call__(self, query: str) -> str:
        results = self.index.search(query, top_k=self.top_k)
        formatted = [f"- {doc['citation']}: {doc['text'][:300]}" for doc in results]
        return "\n".join(formatted)

    def get_last_citations(self) -> list[str]:
        return [doc["citation"] for doc in self._last_results]
```

### The Tool Pattern (Critical for AI Engineering)

**What makes a "tool" in LLM systems?**
1. **Name** — identifier the LLM uses to call it (`search_laws`)
2. **Description** — natural language explanation of what it does (goes into the prompt)
3. **Input** — what the LLM provides (a search query string)
4. **Output** — what the LLM sees back (formatted text results)

**Why `get_last_citations()` exists separately:**
```python
# The LLM sees THIS (truncated for context window):
"- Art. 1 OR: Zum Abschluss eines Vertrages..."

# But the CODE extracts THIS (full citation list):
["Art. 1 Abs. 1 OR", "Art. 11 OR", "Art. 12 OR", ...]
```
- The LLM gets a SUMMARY (to fit in context window)
- The code gets FULL DATA (for citation extraction)
- **Pattern:** Separate what the LLM sees from what the system captures

**Why Two Tools (not one combined search)?**
- Laws corpus: statutory articles (Art. X Gesetz)
- Courts corpus: case decisions (BGE X Y Z)
- Different citation formats, different search strategies
- **Principle:** Each tool should do ONE thing well

**Interview Q:** "How do you design tools for an LLM agent?"  
**A:** "Each tool needs: (1) a clear name, (2) a description the LLM can understand, (3) well-defined input/output format, (4) error handling for bad inputs. Keep tools focused — one tool per capability. The description is part of the prompt, so make it concise but informative."

---

## Cell 8: Load LLM (with CUDA Detection)

```python
def has_cuda_support() -> bool:
    """Check if llama-cpp-python was built with CUDA support."""
    spec = importlib.util.find_spec("llama_cpp")
    lib_dir = Path(spec.origin).parent
    cuda_libs = list(lib_dir.glob("*cuda*")) + list(lib_dir.glob("*cublas*"))
    return bool(cuda_libs)

n_gpu_layers = CONFIG["n_gpu_layers"]
if n_gpu_layers == -1 and not has_cuda_support():
    n_gpu_layers = 0  # Fallback to CPU
```

**Why this matters:** `llama-cpp-python` can be installed WITH or WITHOUT CUDA. If installed without CUDA and you set `n_gpu_layers=-1`, it crashes. This detection prevents that.

---

## Cell 9: The ReAct Agent (MOST IMPORTANT CELL)

### The System Prompt (in German!)

```python
AGENT_SYSTEM_PROMPT = """Du bist ein Schweizer Rechtsrecherche-Assistent mit Zugang zu zwei Such-Tools:

1. search_laws(query): Durchsuche Schweizer Bundesgesetze
2. search_courts(query): Durchsuche Schweizer Bundesgerichtsentscheide

WICHTIG: Suche IMMER auf Deutsch, da die Dokumente auf Deutsch sind.

Antwortformat:
Thought: [Deine Überlegung zur nächsten Suche]
Action: [tool_name]
Action Input: [deutsche Suchanfrage]
"""
```

**Why German prompt?**
- Corpus is entirely in German
- Search queries must be in German (BM25 matches keywords)
- **Critical lesson from Run 3:** Switching the agent to German gave +5.4× F1 improvement!
- English reasoning + German search = code-switching confusion for 7B models

**The ReAct Format:**
```
Thought: I should search for contract law provisions
Action: search_laws
Action Input: Vertrag Abschluss Voraussetzungen OR
```
- **Thought:** Free-form reasoning (helps the model plan)
- **Action:** Exact tool name (must match TOOLS registry)
- **Action Input:** The argument passed to the tool

**4 Full Examples in Prompt (Few-Shot):**
- Contract law (Vertragsrecht)
- Criminal law (Strafrecht)
- Family law (Familienrecht)
- Tenancy law (Mietrecht)

Each example shows the complete Thought→Action→Observation→Thought→Action cycle.

### The Agent Loop

```python
def run_agent(query: str) -> tuple[list[str], list[dict]]:
    conversation = f"[INST] {AGENT_SYSTEM_PROMPT}\n\nQuery: {query}\n\nThought: [/INST]"
    all_citations = []
    
    for iteration in range(CONFIG["max_iterations"]):  # 3 loops
        # 1. Generate LLM response (Thought + Action)
        response = llm(conversation, max_tokens=512, stop=["Observation:"])
        
        # 2. Parse actions from response
        actions = parse_all_agent_actions(response)
        
        # 3. Execute each action (call the tool)
        for action, action_input in actions:
            tool = TOOLS[action.lower()]
            observation = tool(action_input)
            all_citations.extend(tool.get_last_citations())
        
        # 4. Add observation to conversation for next iteration
        conversation += response + "\nObservation: " + truncated_observation
        
        # 5. Check for termination
        if "Final Answer:" in response:
            break
    
    return list(set(all_citations)), logs
```

### Key Engineering Decisions

**1. Stop tokens: `stop=["Observation:"]`**
```python
response = llm(conversation, stop=["Observation:", "[INST]", "</s>"])
```
- The LLM generates "Thought: ... Action: ... Action Input: ..."
- We STOP it before it generates a fake "Observation:" (which would be hallucinated)
- The REAL observation comes from actually running the tool
- **Without this:** LLM might hallucinate search results instead of actually searching

**2. Context Window Management**
```python
conversation = truncate_conversation(conversation, max_chars=28000)
```
- Each iteration adds ~2000 chars (response + observation)
- After 3 iterations: base prompt (~3000) + 3×2000 = ~9000 chars ≈ ok for 8192 context
- But edge cases (long responses, multiple actions) can overflow
- **Truncation strategy:** Keep system prompt + most recent conversation, drop middle

**3. Multi-Action Parsing**
```python
def parse_all_agent_actions(response: str) -> list[tuple[str, str]]:
    """Parse ALL action/input pairs from agent response."""
```
- The LLM might generate MULTIPLE actions in one response:
  ```
  Thought: I need to search both laws and courts.
  Action: search_laws
  Action Input: Vertrag Abschluss
  Action: search_courts
  Action Input: Vertragsabschluss BGE
  ```
- This parser finds ALL action/input pairs (not just the first one)
- **Why this matters:** Batch execution is more efficient than one action per iteration

**4. Citation Extraction (Dual Source)**
```python
# Source 1: From tool results (structured)
obs_citations = tool.get_last_citations()
all_citations.extend(obs_citations)

# Source 2: From LLM's final answer text (regex)
if "Final Answer:" in response:
    citations = extract_citations_from_text(final_text)
    all_citations.extend(citations)
```
- Primary source: structured citations from tool's search results
- Backup source: regex extraction from anything the LLM writes
- **Belt and suspenders** — capture citations from every possible source

**5. Error Recovery**
```python
try:
    response = llm(conversation, ...)
except ValueError as e:
    if "exceed context window" in str(e).lower():
        conversation = truncate_conversation(conversation, max_chars=20000)
        response = llm(conversation, ...)  # Retry with shorter context
```
- If context overflows, aggressively truncate and retry ONCE
- If it still fails, return whatever citations were found so far
- **Never crash — always return partial results**

---

## Cell 10: Evaluation Functions

```python
def citation_f1(predicted, gold) -> dict:
    pred_set = set(predicted)
    gold_set = set(gold)
    
    true_positives = len(pred_set & gold_set)
    precision = true_positives / len(pred_set)
    recall = true_positives / len(gold_set)
    f1 = 2 * precision * recall / (precision + recall)
```

### F1 Score — The Competition Metric (Interview Must-Know)

**What is F1?**
- Harmonic mean of Precision and Recall
- Balances "did you find correct things?" (precision) with "did you find ALL correct things?" (recall)

```
Precision = TP / (TP + FP) = "Of what I predicted, how many were correct?"
Recall    = TP / (TP + FN) = "Of what was correct, how many did I find?"
F1        = 2 × P × R / (P + R) = harmonic mean

Example:
  Predicted: ["Art. 1 OR", "Art. 2 OR", "Art. 999 OR"]  (3 predictions)
  Gold:      ["Art. 1 OR", "Art. 2 OR", "Art. 3 OR", "Art. 4 OR"]  (4 gold)
  
  TP = 2 (Art. 1 and Art. 2 are in both)
  FP = 1 (Art. 999 is wrong)
  FN = 2 (Art. 3 and Art. 4 were missed)
  
  Precision = 2/3 = 0.667
  Recall = 2/4 = 0.500
  F1 = 2 × 0.667 × 0.500 / (0.667 + 0.500) = 0.571
```

**Macro F1 vs Micro F1:**
```
Macro F1 = average of per-query F1 scores
  → Each query weighted equally (regardless of how many citations it has)
  → This is the COMPETITION metric

Micro F1 = F1 computed on aggregate TP/FP/FN across all queries
  → Queries with more citations have more weight
  → Useful for understanding overall performance
```

**Interview Q:** "When do you use Macro vs Micro F1?"  
**A:** "Macro when each instance (query) matters equally — prevents large queries from dominating. Micro when you care about overall accuracy across all instances. For imbalanced datasets, they can differ significantly."

---

## Cell 11-12: Batch Processing & Submission

Standard loop: run agent on all queries, collect predictions, save as CSV.

---

## Why This Approach Is Better Than Notebook 01 (But Still Limited)

| Aspect | Notebook 01 (Direct Gen) | Notebook 02 (Agentic RAG) |
|--------|--------------------------|---------------------------|
| **Grounding** | None — pure hallucination | BM25 search over real corpus |
| **Citation source** | LLM's parametric memory | Actual documents in index |
| **Iteration** | Single pass | 3 loops of Thought→Action→Observe |
| **Language handling** | English prompt → English output | German prompt → German search → German results |
| **Corpus coverage** | Whatever LLM was trained on | 269K laws + 100K courts |

### Why It STILL Fails (Identified Limitations)

| Problem | Root Cause | Impact |
|---------|-----------|--------|
| **German compound words** | BM25 tokenizer splits "Untersuchungs-" ≠ "Untersuchungshaft" | 15/19 gold articles score 0.0 |
| **English→German gap** | Agent sometimes searches in English despite German prompt | Matches nothing in German corpus |
| **Only 100K courts** | 4% of 2.5M court decisions indexed | Gold citations not in index |
| **BM25 can't do semantics** | "pre-trial detention" doesn't match "Untersuchungshaft" | Cross-lingual retrieval impossible |
| **3 iterations too few** | Gold has 42 citations across 8 domains; 3 searches can't cover all | Max ~6 searches × 40 results = 240 candidates |

---

## Concepts Introduced in This Notebook (Summary)

| Concept | What It Is | Why It Matters |
|---------|-----------|----------------|
| **ReAct Pattern** | Thought→Action→Observation loop | The standard for LLM agents |
| **BM25** | Probabilistic keyword retrieval | Baseline for ALL search systems |
| **Tool-Use** | LLM calls external functions | Foundation of AI agents |
| **Context Window Management** | Truncation, safety nets | Prevents crashes in iterative systems |
| **Index Caching** | Build once, load many | Essential for production ML |
| **Dual Extraction** | Citations from tools + regex from LLM text | Maximize recall |
| **Stop Tokens for Agents** | Stop at "Observation:" to prevent hallucination | Critical for tool-use reliability |
| **F1 / Macro F1** | Precision-Recall balance metric | Standard for retrieval evaluation |

---

## Interview Questions This Notebook Prepares You For

1. **"Explain the ReAct pattern."**  
   → "ReAct = Reason + Act. The LLM generates a Thought (reasoning), then an Action (tool call), observes the result, and repeats. It separates reasoning from execution, preventing hallucination of tool outputs."

2. **"How does BM25 work?"**  
   → "BM25 scores documents by term overlap with the query, weighted by IDF (rare terms score higher) and with diminishing returns on term frequency (saturation). It normalizes by document length to prevent long documents from dominating."

3. **"How do you prevent an LLM agent from hallucinating tool outputs?"**  
   → "Use stop tokens. Stop generation at 'Observation:' so the LLM can't write fake observations. Then insert the REAL tool output into the conversation."

4. **"How do you manage context window in an iterative agent?"**  
   → "Track total conversation length. Truncate middle content (keep system prompt + recent turns). Set a safety limit (max_conversation_chars) and truncate before each LLM call."

5. **"What's the difference between Macro and Micro F1?"**  
   → "Macro averages F1 per query (equal weight to each query). Micro computes F1 on aggregate TP/FP/FN (queries with more items have more weight). Use Macro when each instance matters equally."

6. **"Why use German for the agent prompt when queries are in English?"**  
   → "The corpus is in German. BM25 matches keywords literally. If the agent thinks in English and generates English search queries, they won't match German documents. Making the agent think and search in the corpus language is critical."

7. **"How would you improve this system?"**  
   → "Three upgrades: (1) Replace BM25 with semantic embeddings for cross-lingual capability. (2) Add more iterations and query diversity. (3) Index the full corpus instead of 4%. These are exactly what notebooks 03 and 04 implement."

---

## What Comes Next

```
Notebook 02 (this): BM25 keyword search → limited by language gap
    ↓
Notebook 03: Add FAISS embeddings (semantic search) + HyDE (generate hypothetical German docs)
    ↓  
Notebook 04: Multi-direction planner (decompose query into 6 parallel searches)
```

The progression from keyword search → semantic search → multi-direction planning is the evolution from "basic RAG" to "agentic RAG" to "planning-based RAG."
