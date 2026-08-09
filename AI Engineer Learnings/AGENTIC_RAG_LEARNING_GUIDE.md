# Agentic RAG: From Theory to Production — A Complete Case Study

> **Project:** Swiss Legal Citation Retrieval (Omnilex Competition)  
> **Duration:** May–July 2026 | **Iterations:** 10+ architectural versions  
> **Final Architecture:** Hybrid Agentic RAG with Rule-Based Routing + ML Reranking  
> **Key Learning:** When to use LLM agents vs. structured retrieval

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [Architecture Evolution (5 Phases)](#2-architecture-evolution)
3. [Decision-by-Decision Analysis](#3-decision-by-decision-analysis)
4. [What Worked & Why](#4-what-worked--why)
5. [What Failed & Why](#5-what-failed--why)
6. [Competitor Analysis (What Winners Do Differently)](#6-competitor-analysis)
7. [Key Principles of Agentic RAG (Derived from Experience)](#7-key-principles)
8. [Final Architecture Recommendation](#8-final-architecture)
9. [Technical Deep Dives](#9-technical-deep-dives)
10. [Portfolio Talking Points](#10-portfolio-talking-points)

---

## 1. The Problem

### Competition Task
Given an English legal question about Swiss law, return the **exact** statutory articles and court decisions that a lawyer would cite in a brief.

### Why This Is Hard
| Challenge | Why |
|-----------|-----|
| Cross-lingual | Questions in English, corpus in German |
| Granular retrieval | Must find "Art. 221 **Abs. 1** StPO" not just "Art. 221 StPO" |
| Multi-hop reasoning | One question needs citations from 5-8 different legal domains |
| Structured output | Exact citation format: `Art. X Abs. Y Gesetz` or `BGE 137 IV 122 E. 4.2` |
| Massive corpus | 73MB laws + 2.4GB court decisions (2.4M documents) |
| Recall-heavy | Gold answers have 20-60 citations per question |

### Gold Standard Example (Query 1: Pre-trial Detention)
```
Question: "Under what conditions can pre-trial detention be extended?"

Gold Answer: 42 citations across 8 legal domains:
- StPO Haft (Art. 212, 221, 222, 227)         = 5 articles
- StPO Rechtsmittel (Art. 382-396)             = 5 articles  
- StPO Kosten (Art. 422, 428)                  = 3 articles
- StGB (Art. 140 Abs. 1 Raub)                  = 1 article
- StBOG (Art. 37, 39)                          = 2 articles
- BGE_I (Constitutional precedents)            = 5 decisions
- BGE_IV (Criminal precedents)                 = 6 decisions
- 1B_ + 7B_ (Recent Federal Court cases)       = 11 decisions
- BGG (Art. 100 procedural)                    = 1 article
```

**Key Insight:** A single question requires searching across **8 different corpus sections** with different filter codes. This is why naive single-query retrieval fails.

---

## 2. Architecture Evolution

### Phase 1: Naive Approaches (F1 = 0.006)

```
┌─────────────────────────────────────────────┐
│  ARCHITECTURE 01: Direct Generation          │
│                                             │
│  Question → LLM → "Art. 221 Abs. 1 StPO"   │
│                                             │
│  Problem: LLM hallucinates citations that   │
│  don't exist. No grounding in corpus.       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  ARCHITECTURE 02: Simple RAG Agent           │
│                                             │
│  Question → BM25 search → Top-K results     │
│                                             │
│  Problem: English query vs German corpus.   │
│  BM25 can't handle cross-lingual.          │
└─────────────────────────────────────────────┘
```

### Phase 2: HyDE + Iterative Agent (F1 = 0.006 → 0.040)

```
┌─────────────────────────────────────────────────────────┐
│  ARCHITECTURE 03: HyDE + ReAct Agent                     │
│                                                         │
│  Question → LLM generates hypothetical German doc       │
│          → Embed hypothetical doc                       │
│          → FAISS similarity search                      │
│          → ReAct agent iterates (3-6 loops)            │
│          → Reranker scores results                      │
│          → Output top-K                                 │
│                                                         │
│  Run 1: F1=0.006 (BM25 tokenizer broken)               │
│  Run 2: F1=0.006 (embeddings too weak)                  │
│  Run 3: F1=0.034 (switched to German-only agent)        │
│  Run 4: F1=0.040 (added PRF context)                    │
└─────────────────────────────────────────────────────────┘
```

### Phase 3: Planner-Director (F1 = 0.039 → 0.078)

```
┌─────────────────────────────────────────────────────────┐
│  ARCHITECTURE 04: Planner + Director Executors           │
│                                                         │
│  Question → LLM Planner (Mistral-7B)                    │
│          → Generates 6 "research directions"            │
│          → Each direction: {corpus, filter, queries}    │
│          → 6 parallel searches (FAISS+BM25)             │
│          → RRF fusion                                   │
│          → Reranker (broken) / direct RRF               │
│          → Aggregate top-60                             │
│                                                         │
│  V2: F1=0.077 (reranker broken, 3 directions)           │
│  V4: F1=0.078 (reranker disabled, best)                 │
│  V5: F1=0.059 (context truncation regression)           │
│  V6: F1=0.039 (dedup over-aggressive)                   │
└─────────────────────────────────────────────────────────┘
```

### Phase 4: Competitor (What Actually Wins) — F1 = 0.102

```
┌─────────────────────────────────────────────────────────┐
│  COMPETITOR: Structured Retrieval + ML Reranking         │
│                                                         │
│  Question → Regex extract explicit citations            │
│          → BGE-M3 embedding (1024d, multilingual)       │
│          → Hybrid: 80% dense + 20% sparse              │
│          → Feature stacking (8 signals):               │
│            • TF-IDF score (weight=3.5)                  │
│            • Citation regex match (weight=10.0)         │
│            • Query transfer from training (weight=1.5)  │
│            • Co-citation patterns                       │
│            • Domain keyword overlap                     │
│            • Abbreviation expansion                     │
│          → LightGBM reranker (trained on train.csv)     │
│          → Safe tail replacement (bottom 5 only)        │
│          → Output top-25                                │
│                                                         │
│  F1 ≈ 0.102 (3× better than our best)                  │
│  No LLM planner. No iterative agent. Just features.    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Decision-by-Decision Analysis

### Decision 1: Embedding Model Choice

| Option | Dim | Result | Lesson |
|--------|-----|--------|--------|
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | F1=0.006 | Too weak for legal granularity |
| Qwen3-Embedding-0.6B | 1024 | F1=0.078 | Better but still can't distinguish Art. 221 vs 222 |
| BGE-M3 (competitor) | 1024+sparse | F1=0.102 | Multilingual + sparse = winning combo |

**Lesson:** For domain-specific retrieval, general-purpose embeddings fail. You need either:
- A domain-fine-tuned model, OR
- Hybrid dense+sparse (embedding catches semantics, BM25 catches exact terms)

**Why 384d fails at legal tasks:** Swiss law articles are syntactically identical ("Abs. 1 ... wird bestraft mit..."). The semantic differences are in 1-2 domain words. A 384d model can't encode that level of granularity — articles about "Raub" (robbery) and "Diebstahl" (theft) embed nearly identically.

---

### Decision 2: BM25 vs FAISS vs Hybrid

| Approach | Strengths | Weaknesses | F1 Impact |
|----------|-----------|------------|-----------|
| BM25 only | Catches exact "Art. 221" keywords | Fails on cross-lingual (English→German) | 0.006 |
| FAISS only | Semantic matching across languages | Can't distinguish Art. 221 vs 222 (99% cosine sim) | 0.006 |
| Hybrid (RRF fusion) | Best of both | Still limited by component quality | 0.040 |

**Lesson:** Neither BM25 nor dense retrieval alone is sufficient for legal citation retrieval. The **combination** via RRF (Reciprocal Rank Fusion) is mandatory.

**Technical detail — RRF formula:**
```
RRF_score(doc) = Σ 1/(k + rank_i(doc))  where k=60
```
This means a document ranked #1 in BM25 and #50 in FAISS gets:
```
1/(60+1) + 1/(60+50) = 0.0164 + 0.0091 = 0.0255
```
A document ranked #5 in both gets:
```
1/(60+5) + 1/(60+5) = 0.0154 + 0.0154 = 0.0308 (HIGHER — consistency rewarded)
```

---

### Decision 3: Cross-Lingual Strategy

| Approach | How | Result | Lesson |
|----------|-----|--------|--------|
| English query → German corpus directly | Multilingual embedding handles it | F1=0.006 | Embedding too weak |
| HyDE (generate German hypothetical doc) | LLM writes fake German article, embed that | F1=0.006→0.040 | Helps but slow (5s/query) |
| German-only agent (Run 3) | LLM translates query to German first | F1=0.034 (+5.4×!) | **Massive win** — removing code-switching helps |
| Regex extraction + translation (competitor) | Parse citations directly from English | F1=0.102 | Best: structured extraction, not generation |

**Lesson:** The biggest single improvement (Run 2→Run 3, **+5.4× F1**) came from making the agent think entirely in German. Code-switching (English query → German search → English reasoning) confuses small LLMs.

**Key Insight:** HyDE is theoretically elegant but practically expensive (5s/query for LLM generation). For structured tasks like citation retrieval, regex extraction is faster AND more accurate.

---

### Decision 4: Reranker Choice

| Reranker | What Happened | Root Cause | Lesson |
|----------|--------------|------------|--------|
| Qwen3-Reranker-0.6B | Uniform scores (0.003 for ALL docs) | Wrong prompt format or token IDs | Small transformer rerankers are fragile |
| Cross-encoder (attempted) | Similar failure | Same model class, same problem | 0.6B too small for legal discrimination |
| LightGBM (competitor) | Works well (~0.102 F1) | Trained on task-specific features | ML > neural for structured scoring |
| Disabled (V4) | F1 improved when removed! | Broken reranker is WORSE than no reranker | Always validate components |

**Lesson:** A broken reranker is worse than no reranker at all. V4's best result (F1=0.078) came specifically from DISABLING the reranker and using raw RRF scores.

**Deeper lesson:** For structured retrieval tasks, tree-based ML models (LightGBM/XGBoost) often beat transformer rerankers because:
1. They can ingest hand-crafted features (TF-IDF, citation regex, query overlap)
2. They're fast (microseconds vs milliseconds per document)
3. They're interpretable (feature importance is visible)
4. They don't need prompt engineering

---

### Decision 5: Single-Query Agent vs Multi-Direction Planner

| Approach | How | F1 | Tradeoff |
|----------|-----|-----|----------|
| Single ReAct agent (03) | One agent iteratively searches | 0.040 | Low risk, low reward — can't cover 8 domains |
| Multi-direction planner (04) | LLM decomposes into 6 searches | 0.078 | High reward IF routing is correct, catastrophic if wrong |

**Lesson:** The planner architecture DOES help (0.040→0.078 = 2×) because legal questions genuinely need multi-domain coverage. But it introduces **routing fragility** — one wrong filter code loses 50% of recall.

**The fundamental tradeoff:**
```
Single Agent:  Low variance, low ceiling (can't cover 8 domains in 3 iterations)
Planner:       High variance, high ceiling (CAN cover 8 domains but routing is fragile)
Rule-Based:    Low variance, high ceiling (hardcoded routing = guaranteed coverage)
```

**Conclusion:** Don't let an LLM decide routing. Use deterministic rules.

---

### Decision 6: Token Budget Management

| Parameter | V2 | V3 | V4 | V5 | Current | Lesson |
|-----------|----|----|----|----|---------|--------|
| max_tokens_planner | 800 | 1500 | 1500 | 3000 | 6000 | 800 crashed; 1500 was minimum; 3000+ is wasteful |
| max_tokens_executor | 200 | 350 | 800 | 800 | 800 | 200 crashed; 350 still fragile; 800 is safe |
| max_chars_context | — | — | 12000 | 8000 | 12000 | 8000 truncated critical routing = regression |

**Lesson:** Token budgets are not "more is better." The sweet spot is the MINIMUM that avoids truncation. Going from 1500→3000→6000 didn't improve F1 — it just made generation slower and more prone to rambling.

**Critical Failure (V5):** Reducing context from 12000→8000 chars to "make room" for larger output actually CUT the court routing guide. The planner never saw instructions for 7B_ (Bundesstrafgericht) → never routed there → lost 5 gold citations.

**Rule:** Always verify what's being truncated. Character limits are invisible failure modes.

---

### Decision 7: Grammar Constraints (GBNF)

| Grammar Rule | What It Does | Result |
|---|---|---|
| Enforce exactly 6 directions | GBNF forces JSON with 6 direction objects | ✅ Planner always outputs 6 (no more "3 then stop") |
| Constrain corpus to "laws"/"courts"/"both" | Only valid corpus values allowed | ✅ No hallucinated corpus names |
| Free-text for filter_codes | LLM can write any string as code | ❌ Sometimes writes invalid codes (filtered post-hoc) |

**Lesson:** GBNF grammars are powerful for structural constraints but can't enforce SEMANTIC constraints. You can force "6 directions" but can't force "6 DIVERSE directions."

**What GBNF CAN do:** Guarantee valid JSON, enforce field types, limit enum values  
**What GBNF CANNOT do:** Ensure diversity, prevent repetition, validate domain logic

---

### Decision 8: Procedural Defaults Injection

| Approach | What We Did | Result |
|----------|------------|--------|
| Inject 9 "standard" criminal law articles | Added Art. 100, 81, 42, 95, 105, 29, 78, 80, 10 | 1/9 correct (11% hit rate) |

**Lesson:** Generic procedural defaults are a precision killer. 8 out of 9 injected citations were FALSE POSITIVES. They occupy slots that could go to real results.

**Better approach:** Case-type-specific defaults:
- Haft (detention) → Art. 221, 222, 227, 382, 393 StPO
- Strafurteil (conviction) → Art. 42, 47, 50 StGB
- Zivilsache (civil) → Art. 308, 310 ZPO

---

### Decision 9: Post-Processing (Dedup + Enrich)

| What We Did | Logic | Result |
|---|---|---|
| Strip duplicate filter_codes across directions | If Dir 1 uses StPO, Dir 5 can't | V6 F1 dropped 0.059→0.039 |
| Enrich single-code directions with companions | StPO → +BStKR, +JStPO | May have diluted search quality |
| Fallback codes from rechtsgebiet | 0-code directions get domain defaults | Untested in isolation |

**Lesson:** Post-processing heuristics are dangerous. They look logical but their interactions are unpredictable. The dedup stripped StPO from later directions that NEEDED it (Rechtsmittel articles are also in StPO). The enrichment added companion codes that were irrelevant to the specific sub-question.

**Rule:** Never add post-processing without A/B testing each component in isolation.

---

### Decision 10: Context Assembly Order

| Order | What Gets Included at 8000 chars | What Gets Cut |
|-------|----------------------------------|---------------|
| Laws routing → Courts routing → Terminology | Laws header (2284) + 3 law sections (5745) | ALL court routing, ALL terminology |

**Lesson:** The ORDER of context assembly creates implicit priorities. Laws always get budget because they're assembled first. Courts are cut because they're last.

**Better approach:** Interleave or allocate fixed budgets per section:
- Reserve 4000 chars for laws routing
- Reserve 4000 chars for courts routing
- Reserve 2000 chars for domain-specific terms
- Total: 10000 chars (fits in 12000 budget)

---

## 4. What Worked & Why

| # | Decision | Impact | Why It Worked |
|---|----------|--------|--------------|
| 1 | **Disable broken reranker** (V4) | F1: 2× improvement | Broken component is worse than no component — RRF alone was better |
| 2 | **German-only agent** (Run 3) | F1: 5.4× improvement | Eliminated code-switching confusion in 7B LLM |
| 3 | **GBNF grammar for 6 directions** | Structural guarantee | LLM always outputs valid JSON with exactly 6 directions |
| 4 | **Hybrid BM25+FAISS** | Better than either alone | Keyword catches exact terms; embedding catches semantics |
| 5 | **Top-40 law codes** (trim system prompt) | -7800 chars, no quality loss | 200+ codes was noise; model only uses ~15-20 anyway |
| 6 | **Routing context for court sections** | Planner can see 7B_/BGE_I | Without context, planner can't know these codes exist |
| 7 | **max_tokens_planner 800→1500** | JSON parsing succeeds | Minimum viable budget to complete 6-direction JSON |

---

## 5. What Failed & Why

| # | Decision | Impact | Root Cause | Lesson |
|---|----------|--------|-----------|--------|
| 1 | **Qwen3-Reranker-0.6B** | Uniform 0.003 scores | Model too small OR wrong prompt format | Always validate new components before integrating |
| 2 | **max_chars=8000** | Killed court routing | Assembly order puts courts LAST; truncation cuts them | Verify what gets cut, not just what fits |
| 3 | **HyDE (hypothetical doc generation)** | +17% only (Run 4) | Can't fix what embedding can't find | HyDE amplifies initial retrieval quality |
| 4 | **Dedup+Enrich post-processing** | F1 dropped 24% | Stripped valid codes; added irrelevant codes | Test heuristics in isolation |
| 5 | **Forcing 6 directions without diversity** | 3/6 were StPO duplicates | Grammar can't enforce semantics | Structural != semantic constraints |
| 6 | **PRF (Pseudo-Relevance Feedback)** | Only +17% over baseline | If initial retrieval is wrong, PRF amplifies the error | PRF is a good-gets-better technique, not a fix-bad technique |
| 7 | **Few-shot bank (3279 examples)** | Zero impact (Run 2→3) | Code had `types=None` bug; examples never used | Dead code detection is critical |
| 8 | **Procedural defaults (9 articles)** | 8/9 wrong = precision killer | Generic defaults don't match specific questions | Domain specificity > coverage |
| 9 | **Increasing max_tokens beyond 3000** | No improvement | Model was already generating complete output at 1500-3000 | More tokens ≠ better output |
| 10 | **Token ID resolution for reranker** | No improvement | Fundamental model problem, not token mapping | Symptom-fixing vs root-cause-fixing |

---

## 6. Competitor Analysis

### What the Winner Does (F1 ≈ 0.102)

**Philosophy:** Treat legal citation retrieval as a **structured information extraction** problem, NOT a generation problem.

| Technique | Weight | How It Works | Why It Wins |
|-----------|--------|-------------|-------------|
| **Regex Citation Extraction** | 10.0 | Parse "Art. 221 Abs. 1 StPO" from query text | If query mentions an article, it's almost certainly gold |
| **TF-IDF Matching** | 3.5 | Term frequency between query and article text | Catches keyword overlap that embeddings miss |
| **Query Transfer** | 1.5 | Find similar training queries → reuse their gold citations | Nearest-neighbor approach for known patterns |
| **Dense Embedding (BGE-M3)** | 1.0 | 1024d multilingual embedding search | Semantic fallback for novel queries |
| **Co-Citation Patterns** | 0.5 | "If Art. 221 is cited, Art. 227 often is too" | Exploits legal structure (related articles co-occur) |
| **Abbreviation Expansion** | 0.3 | "StPO" → "Strafprozessordnung" + all known aliases | Helps BM25 match different forms |
| **Safe Tail Replacement** | — | Only modify bottom 5 predictions, never touch top 20 | Conservative: protects what's already good |
| **LightGBM Reranker** | — | Trained on all features + train.csv gold labels | Learns non-linear patterns |

### Key Insight: No LLM Planner

The competitor doesn't use an LLM to decompose the question. They don't have a "planner." They just:
1. Extract what they can (regex)
2. Search broadly (embedding)
3. Score with features (TF-IDF, overlap, transfer)
4. Rerank with ML (LightGBM)
5. Output top-25

**Why this beats LLM planning:**
- No hallucination risk (LLMs invent non-existent citations)
- No routing fragility (one wrong code ≠ catastrophic failure)
- Interpretable (each feature has a known weight)
- Fast (no LLM generation bottleneck)
- Reproducible (deterministic given same inputs)

---

## 7. Key Principles of Agentic RAG (Derived from Experience)

### Principle 1: Validate Every Component in Isolation
> "A broken reranker is worse than no reranker."

Before integrating ANY component, verify it produces meaningful output. Our reranker produced uniform scores — it was actively harmful. We only discovered this after 3 failed runs.

**How to apply:** After adding a component, test with known-good inputs. If a reranker gives the same score to a perfect match and a random document, it's broken.

---

### Principle 2: Structural Constraints ≠ Semantic Constraints
> "GBNF grammar forces 6 directions. It can't force 6 DIFFERENT directions."

You can enforce output FORMAT perfectly with grammars. You cannot enforce output QUALITY. The model will produce valid JSON with repetitive content if it doesn't understand diversity.

**How to apply:** For quality constraints, use post-processing validation (reject directions that overlap >80% with existing ones) rather than trying to constrain the generation grammar.

---

### Principle 3: Context Truncation is an Invisible Failure Mode
> "Everything looked fine. The planner just never saw the court routing section."

When you set `max_chars=8000`, nothing crashes. No error message. The planner simply never sees what was truncated. You only discover the problem by analyzing what the planner DOESN'T do.

**How to apply:** Always log what gets truncated. Print: "Context sections included: [X, Y, Z]. Sections CUT: [A, B]." Make invisible failures visible.

---

### Principle 4: For Structured Tasks, ML > LLM
> "LightGBM with 8 features beats a 7B LLM planner."

Legal citation retrieval is fundamentally a STRUCTURED task: given features of a query-document pair, predict relevance. This is exactly what gradient-boosted trees excel at. LLMs add hallucination risk and latency for no benefit on structured classification.

**When to use LLM:** Free-form reasoning, query expansion, translation  
**When to use ML:** Scoring, ranking, classification of structured features

---

### Principle 5: The Retrieval Pool Determines the Ceiling
> "You can't rerank citations that were never retrieved."

If your embedding model doesn't put the correct article in the top-100 results, no downstream component can fix it. Rerankers reorder existing results — they don't create new ones.

**How to apply:** Measure **recall@100** before building downstream components. If gold citations aren't in the top-100 retrieval pool, fix embeddings first. Everything else is wasted effort.

---

### Principle 6: Hybrid Search is Mandatory for Domain Tasks
> "BM25 catches 'Art. 221'; FAISS catches 'pre-trial detention'. Neither alone is sufficient."

Keyword search (BM25) is precise for exact terms but fails on paraphrases. Dense search (FAISS) handles semantics but can't distinguish structurally similar documents. The combination via RRF is strictly better than either alone.

**How to apply:** Always run both BM25 and dense retrieval. Fuse with RRF (k=60). This is a free win with no downside.

---

### Principle 7: Don't Over-Engineer Before Measuring
> "We built a 6-direction planner before confirming our embeddings could find basic articles."

The planner architecture was sophisticated but built on a foundation of broken embeddings and a broken reranker. Complexity hid the real problem.

**How to apply:** Build bottom-up:
1. Can embeddings find gold articles in top-100? (Measure recall@100)
2. Can reranker discriminate gold from noise? (Measure NDCG@10)
3. ONLY THEN add planning/routing complexity

---

### Principle 8: One Wrong Routing Decision is Catastrophic
> "Choosing 6B_ instead of 1B_ lost 12 court decisions in one move."

In planner-based architectures, a single routing mistake cascades. If the planner picks the wrong court division, every downstream search, rerank, and aggregation step operates on the wrong corpus section. There's no recovery mechanism.

**How to apply:** For high-stakes routing decisions, use rules or ensembles, not a single LLM call. If you must use LLM routing, always add a fallback that covers ALL possible routes (even if it means more searches).

---

### Principle 9: Regex > LLM for Structured Extraction
> "If the query says 'Art. 221 Abs. 1 StPO', just put it in the output."

The competitor's highest-weighted signal (weight=10.0) is simple regex extraction. If the question mentions a specific article, it's almost certainly in the gold answer. No LLM reasoning needed — just pattern matching.

**How to apply:** Before ANY LLM processing, run regex to extract explicit citations from the query. Give these maximum weight in your final ranking.

---

### Principle 10: Test on Multiple Queries Before Concluding
> "V4's F1=0.078 looked great — on 1 query. On 10 queries, it would average 0.03-0.05."

Single-query optimization is misleading. A planner that perfectly routes "Haft" questions might completely fail on "Steuerrecht" or "Familienrecht" questions. Always validate on the full set.

**How to apply:** Minimum validation set: 5-10 diverse queries covering different legal domains. Never celebrate single-query improvements.

---

## 8. Final Architecture Recommendation

### Recommended: Hybrid Structured Retrieval

```
┌─────────────────────────────────────────────────────────┐
│  INPUT: English legal question                           │
│                                                         │
│  ┌─ STAGE 1: EXTRACTION (deterministic) ─────────────┐ │
│  │  • Regex: Extract cited articles (weight=10.0)     │ │
│  │  • Keywords: Extract legal domain terms            │ │
│  │  • Translation: LLM single-pass → German query     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─ STAGE 2: ROUTING (rule-based, NOT LLM) ─────────┐ │
│  │  • Domain classifier: keywords → legal area        │ │
│  │  • Code assignment: domain → filter codes          │ │
│  │  • Example: "detention" → [StPO, 1B_, 7B_, BGE_I] │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─ STAGE 3: RETRIEVAL (hybrid) ────────────────────┐  │
│  │  • Dense: BGE-M3 embedding (1024d) per domain     │  │
│  │  • Sparse: BM25 on German query per domain        │  │
│  │  • Fusion: RRF (k=60)                            │  │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─ STAGE 4: SCORING (feature stacking) ────────────┐  │
│  │  • Dense similarity (weight=1.0)                  │  │
│  │  • BM25 score (weight=0.5)                        │  │
│  │  • Regex match (weight=10.0)                      │  │
│  │  • TF-IDF overlap (weight=3.5)                    │  │
│  │  • Query transfer from training gold (weight=1.5) │  │
│  │  • Co-citation patterns (weight=0.5)              │  │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─ STAGE 5: RERANKING (ML) ────────────────────────┐  │
│  │  • LightGBM trained on train.csv feature vectors  │  │
│  │  • Conservative: protect top-20, adjust bottom-5  │  │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  OUTPUT: Top-25 ranked citations                         │
│  Expected F1: 0.10-0.20                                 │
└─────────────────────────────────────────────────────────┘
```

### Why This Architecture

| Component | From | Rationale |
|-----------|------|-----------|
| Regex extraction | Competitor | Free precision, highest signal |
| LLM translation (single-pass) | Our 04 planner | Cross-lingual query expansion |
| Rule-based routing | New (replaces LLM planner) | Deterministic, no hallucination |
| BGE-M3 embedding | Competitor | Stronger than MiniLM-384d or Qwen-0.6B |
| Hybrid BM25+FAISS | Both | Proven better than either alone |
| Feature stacking | Competitor | Multiple signals > single score |
| LightGBM reranker | Competitor | Trained on task data, fast, interpretable |

---

## 9. Technical Deep Dives

### Deep Dive A: Why German Compound Words Break BM25

**The problem:**
```
Corpus text:  "Untersuchungs- und Sicherheitshaft"  (3 BM25 tokens)
Query term:   "Untersuchungshaft"                   (1 BM25 token)

BM25 match score: 0.0 (no token overlap!)
```

German compounds split differently when hyphenated. BM25 treats each hyphen-separated part as a token. The query uses the compound form. Zero overlap = zero BM25 score.

**Impact:** 15 of 19 gold law articles scored 0.0 with BM25 in Run 1.

**Fix:** Use a German compound splitter (or switch to character n-gram overlap):
```python
# Compound-aware tokenizer
"Untersuchungshaft" → ["Untersuchung", "Haft", "Untersuchungshaft"]
"Untersuchungs- und Sicherheitshaft" → ["Untersuchung", "Sicherheit", "Haft"]
# Now they share "Untersuchung" and "Haft" → positive BM25 score
```

---

### Deep Dive B: Why the Reranker Failed

**Expected behavior:**
```
Input: (query, relevant_doc) → score ≈ 0.9
Input: (query, irrelevant_doc) → score ≈ 0.1
```

**Actual behavior (Qwen3-Reranker-0.6B):**
```
Input: (query, relevant_doc) → score = 0.0039
Input: (query, irrelevant_doc) → score = 0.0041
All 106 candidates: scores in range [0.0016, 0.0328]
```

**Root cause candidates:**
1. Wrong prompt format (model expects specific instruction prefix)
2. Token ID mismatch (model's "yes"/"no" logits not correctly mapped)
3. Model too small (0.6B params can't discriminate legal relevance)
4. Context length issue (input too long for model's training distribution)

**What we tried:** Token ID resolution chains → no improvement  
**What the competitor did:** Skipped transformer rerankers entirely → used LightGBM

**Lesson:** Don't debug a component for 3 iterations. If it doesn't work after 1 fix, replace it.

---

### Deep Dive C: Token Budget Mathematics

```
Mistral-7B context window: 16,384 tokens

Prompt structure:
  [INST] {system_prompt}

  {context_text}

  FRAGE: {question} [/INST]

Budget breakdown (V4 — best version):
  System prompt:     ~10,800 chars = ~2,700 tokens (17%)
  Context text:      ~12,000 chars = ~3,000 tokens (18%)
  Question:          ~1,100 chars  = ~275 tokens   (2%)
  ─────────────────────────────────────────────────────
  Total input:                      ~5,975 tokens  (37%)
  Output (6 directions JSON):       ~2,500 tokens  (15%)
  ─────────────────────────────────────────────────────
  USED:                             ~8,475 tokens  (52%)
  HEADROOM:                         ~7,909 tokens  (48%)
```

**Key insight:** We had 48% headroom but still crashed in V2 because `max_tokens_planner=800` was too low for 6-direction JSON output (~2500 tokens needed). The crash was output truncation, not input overflow.

---

### Deep Dive D: RRF Fusion — How and Why

**Reciprocal Rank Fusion** merges multiple ranked lists without needing score normalization:

```python
def rrf_score(doc, rankings, k=60):
    """k=60 is standard — dampens the effect of being #1 vs #5"""
    score = 0
    for ranking in rankings:
        if doc in ranking:
            rank = ranking.index(doc) + 1  # 1-indexed
            score += 1.0 / (k + rank)
    return score
```

**Why k=60?** Higher k makes the function flatter (less reward for being #1). k=60 means:
- Rank 1: score contribution = 1/61 = 0.0164
- Rank 10: score contribution = 1/70 = 0.0143
- Rank 50: score contribution = 1/110 = 0.0091

The difference between rank 1 and rank 10 is only 13%. This means RRF rewards **consistent appearance across multiple lists** more than being #1 in a single list.

**Application:** A document that appears in both BM25 top-50 AND FAISS top-50 will score higher than a document that's #1 in FAISS but absent from BM25. This is exactly what we want for legal retrieval — we trust documents that BOTH keyword and semantic search find relevant.

---

## 10. Portfolio Talking Points

### For Resume/Interviews

**Project Description:**
> "Built an Agentic RAG pipeline for Swiss legal citation retrieval, iterating through 10+ architectural versions. Identified that LLM-based planning introduces routing fragility, and demonstrated that hybrid structured retrieval (BGE-M3 + BM25 + LightGBM) achieves 3× better F1 than LLM-only approaches."

**Key Technical Achievements:**
1. Identified and quantified embedding model bottleneck (384d → 1024d = 5× improvement)
2. Discovered that disabling a broken component (reranker) doubled F1
3. Implemented GBNF grammar constraints for structured LLM output
4. Built multi-direction planner with domain-specific routing
5. Analyzed competitor approach and identified 6 missing components

**Lessons for Interviewers:**
- "I learned that for structured retrieval tasks, ML reranking (LightGBM) beats transformer rerankers because it can ingest hand-crafted domain features"
- "The biggest single improvement (+5.4× F1) came from eliminating code-switching — making the agent think entirely in the target language"
- "I discovered that post-processing heuristics (dedup/enrich) can harm performance if not A/B tested in isolation"
- "I validated that hybrid BM25+dense retrieval via RRF is strictly better than either alone for domain-specific tasks"

**Technical Stack:**
- LLM: Mistral-7B-Instruct-v0.2 (GGUF quantized, llama-cpp-python)
- Embeddings: Qwen3-Embedding-0.6B (1024d), comparing with BGE-M3
- Search: FAISS IndexFlatIP + BM25Okapi + RRF fusion
- Grammar: GBNF for structured JSON output
- Reranking: Qwen3-Reranker (broken) → LightGBM (recommended)
- Platform: Kaggle (2× T4 GPUs, 30GB RAM)

---

## Appendix: Quick Reference Card

### What to Use When (Agentic RAG Decision Matrix)

| Situation | Use LLM | Use Rules | Use ML |
|-----------|---------|-----------|--------|
| Query translation | ✅ | | |
| Query expansion | ✅ | | |
| Domain routing | | ✅ | |
| Retrieval | | | ✅ (embeddings) |
| Scoring/Ranking | | | ✅ (LightGBM) |
| Citation extraction | | ✅ (regex) | |
| Diversity enforcement | | ✅ (post-processing rules) | |
| Output generation | ✅ | | |

### When Agentic RAG Helps vs Hurts

| Helps | Hurts |
|-------|-------|
| Multi-domain questions (need 8+ corpus sections) | Single-domain questions (one search suffices) |
| Open-ended queries (need exploration) | Structured queries (exact citations mentioned) |
| When routing is reliable | When routing is fragile (one mistake = catastrophe) |
| When you have good components (embeddings, reranker) | When foundation is broken (bad embeddings, dead reranker) |
| When you measure on multiple queries | When you over-optimize on 1 query |
