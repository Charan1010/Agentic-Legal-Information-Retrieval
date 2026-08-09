# Trial-and-Error History: Every Experiment, What Worked, What Failed

> **Scope:** Complete chronological record from first notebook 03 run through V6  
> **Purpose:** Learn from every mistake. Understand WHY things failed, not just THAT they failed.  
> **Format:** Each experiment = Hypothesis → Change → Result → Root Cause → Lesson

---

## File Map: How Every File Relates

```
TIMELINE:  Apr 30          May 9         May 14-15        May 19-24          May 26-31          Jun 4-5         Jul 17
           ──────          ─────         ─────────        ─────────          ─────────          ───────         ──────
           
NOTEBOOKS (the code):
           
  01_direct_generation_baseline.ipynb ─────────────────────────────────────────────────────────────────────────────▶
  │ Created: Apr 30 | Modified: May 13
  │ Purpose: Simplest baseline — LLM generates citations from memory
  │ Architecture: Prompt → LLM → regex parse
  │ Status: FROZEN (never run on Kaggle, no results)
  │
  02_agentic_retrieval_baseline.ipynb ─────────────────────────────────────────────────────────────────────────────▶
  │ Created: Apr 30 | Modified: May 4
  │ Purpose: First RAG — adds BM25 search tools
  │ Architecture: ReAct agent + BM25 (keyword only)
  │ Status: FROZEN (never run on Kaggle, no results)
  │ Related doc: ReAct_Agent_Cell_Explained.md (May 3)
  │
  03_hyde_retrieval.ipynb ──────────────────────────────────────────────────────────────────────────────────────────▶
  │ Created: May 9 | Modified: May 15 (then FROZEN)
  │ Purpose: Adds HyDE + FAISS embeddings + few-shot bank
  │ Architecture: HyDE + FAISS + BM25 + ReAct agent
  │ Status: FROZEN — evolved into 03_hyde_kaggle
  │ Related doc: 03_DETAILED_FLOW.md (May 9 — cell-by-cell architecture doc)
  │
  │   ├──▶ kaggle_submission.ipynb (Created: May 14, Modified: May 15)
  │   │    Kaggle-packaged copy of 03_hyde_retrieval
  │   │    PRODUCED: (no separate analysis — same as Run 1)
  │   │
  │   └──▶ 03_hyde_kaggle.ipynb (Created: May 15, Modified: May 31) ◀── ACTIVELY ITERATED
  │        Evolved version — German agent, PRF, GBNF grammar
  │        This notebook was modified 4 times for Runs 1-4
  │        │
  │        ├──▶ kaggle_submission_v2.ipynb (Created: May 14, Modified: May 31)
  │        │    Kaggle-packaged copy of 03_hyde_kaggle
  │        │    PRODUCED: Run 1, Run 2, Run 3, Run 4 results on Kaggle
  │        │
  │        ├── RUN ANALYSIS FILES (created AFTER each Kaggle run):
  │        │    ├── RUN_1_ANALYSIS.md (Created: May 15 — analyzes Run 1 output)
  │        │    ├── RUN_2_ANALYSIS.md (Created: May 20 — analyzes Run 2 output)
  │        │    ├── RUN_3_ANALYSIS.md (Created: May 21 — analyzes Run 3 output)
  │        │    └── RUN_4_ANALYSIS.md (Created: May 24 — analyzes Run 4 output)
  │        │
  │        └── NOTEBOOK_ANALYSIS.md (root dir — overall 03 architecture analysis)
  │
  04_planner_director.ipynb ───────────────────────────────────────────────────────────────────────────────────────▶
     Created: May 26 | Modified: Jul 24 (STILL ACTIVE)
     Purpose: Complete redesign — planner decomposes into 6 directions
     Architecture: Planner LLM → 6 Executors → FAISS+BM25 → RRF → aggregate
     This notebook was modified for V2, V3, V4, V5, V6 (same file, different CONFIG)
     │
     ├── PIPELINE DEBUG LOGS (raw output from each Kaggle run):
     │    ├── pipeline_debug_log.txt    (May 31 — V1 first run)
     │    ├── pipeline_debug_log_v2.txt (May 31 — V2 baseline)
     │    ├── pipeline_debug_log_v3.txt (May 31 — V3 token fix)
     │    ├── pipeline_debug_log_v4.txt (May 31 — V4 reranker disabled)
     │    ├── pipeline_debug_log_v5.txt (Jun 4  — V5 force 6 directions)
     │    └── pipeline_debug_log_v6.txt (Jun 5  — V6 dedup+enrich)
     │
     └── ANALYSIS FILES (created AFTER analyzing each log):
          ├── Query1_Deep_Analysis.md     (May 31 — V1 single query deep dive)
          ├── V2_Deep_Analysis.md          (May 31 — V2 analysis)
          ├── V2_Planner_Prompt_Analysis.md (May 31 — V2 prompt dissection)
          ├── pipeline_v4_analysis.md      (May 31 — V4 best-result analysis)
          ├── pipeline_v5_analysis.md      (Jun 4  — V5 regression analysis)
          └── COMPLETE_PIPELINE_HISTORY.md (Jul 17 — full retrospective)


HOW THE FILES CONNECT:
═════════════════════

  NOTEBOOK (code)           KAGGLE RUN              DEBUG LOG              ANALYSIS MD
  ═══════════════           ══════════              ═════════              ═══════════
  
  03_hyde_retrieval ──────▶ (first test) ─────────▶ (not saved) ─────────▶ NOTEBOOK_ANALYSIS.md
       │
       └▶ 03_hyde_kaggle ─▶ Run 1 on Kaggle ─────▶ (in notebook output) ▶ RUN_1_ANALYSIS.md
                           │
                           ├▶ Run 2 on Kaggle ───▶ (in notebook output) ▶ RUN_2_ANALYSIS.md
                           │  (changed: GBNF, reranker, FAISS-only)
                           │
                           ├▶ Run 3 on Kaggle ───▶ (in notebook output) ▶ RUN_3_ANALYSIS.md
                           │  (changed: German agent, monolingual rerank)
                           │
                           └▶ Run 4 on Kaggle ───▶ (in notebook output) ▶ RUN_4_ANALYSIS.md
                              (changed: PRF, remove few-shot)

  04_planner_director ────▶ V2 on Kaggle ─────────▶ pipeline_debug_log_v2.txt ──▶ V2_Deep_Analysis.md
       (same notebook,     │                                                      V2_Planner_Prompt_Analysis.md
        CONFIG changed     │
        between runs)      ├▶ V3 on Kaggle ───────▶ pipeline_debug_log_v3.txt ──▶ Query1_Deep_Analysis.md
                           │
                           ├▶ V4 on Kaggle ───────▶ pipeline_debug_log_v4.txt ──▶ pipeline_v4_analysis.md
                           │
                           ├▶ V5 on Kaggle ───────▶ pipeline_debug_log_v5.txt ──▶ pipeline_v5_analysis.md
                           │
                           └▶ V6 on Kaggle ───────▶ pipeline_debug_log_v6.txt ──▶ (not formally analyzed)


KEY INSIGHT: 
  - 03_hyde_kaggle = ONE notebook file, run 4 times with internal code changes between runs
  - 04_planner_director = ONE notebook file, run 6 times with CONFIG changes between runs
  - Each "version" is NOT a separate file — it's the SAME file modified and re-run
  - The RUN_*_ANALYSIS.md files were created AFTER downloading Kaggle output
  - The pipeline_debug_log_v*.txt files were downloaded from Kaggle after each run
  - The analysis MDs were written (likely with AI assistance) to understand what went wrong
```

---

## Timeline at a Glance

```
May 13 ── 03_hyde_retrieval (F1=0.000) ── total failure
    │
May 19 ── Run 1 (F1=0.006) ── FAISS+BM25 added, but 188 citations/query
    │
May 19 ── Run 2 (F1=0.006) ── GBNF+reranker fixed precision, but recall=0
    │
May 20 ── Run 3 (F1=0.034) ── ✅ German agent = 5.5× improvement
    │
May 24 ── Run 4 (F1=0.040) ── ✅ PRF+no-fewshot = +17%
    │
May 31 ── Pipeline V2 (F1=0.077) ── new architecture: planner/director
    │
May 31 ── V3 (F1=0.039) ── ❌ token fix regression
    │
May 31 ── V4 (F1=0.078) ── ✅ BEST EVER: reranker disabled
    │
Jun 4  ── V5 (F1=0.059) ── ❌ context truncation regression
    │
Jun 5  ── V6 (F1=0.039) ── ❌ dedup/enrich regression
```

---

## Experiment 1: First Run (May 13) — Complete Failure

### Hypothesis
"BM25 keyword search + HyDE should find relevant Swiss law articles"

### Configuration
```python
LLM:           Mistral-7B on CPU (no GPU!)
Search:        BM25 only (no FAISS)
Tokenizer:     text.lower().split()  # naive whitespace
Corpus:        175K laws + 100K courts (4% of 2.5M)
Agent:         ReAct free-text, 3 iterations
Few-shot bank: 119 law types, 19 court types
```

### Result: **F1 = 0.000** (literally zero correct citations)

### What Actually Happened (Val Q1 — detention law):
```
Gold expects:  Art. 221 StPO, Art. 227 StPO, BGE 137 IV 122, ...
Agent searched: "Untersuchungshaft" via BM25
BM25 tokenized corpus: "untersuchungs-" "und" "sicherheitshaft"  (hyphen split)
BM25 tokenized query:  "untersuchungshaft"  (single token)
Token overlap: ZERO → Art. 221 StPO scored 0.0 → invisible

What was returned instead: Commercial register law, broadcasting regulation, 
alcohol law — because their text happened to share OTHER tokens with the query
```

### Root Cause Chain
```
naive tokenizer (split on whitespace)
  → German compound words don't match their hyphenated forms
    → 15/19 gold law articles scored exactly 0.0
      → BM25 returned completely irrelevant articles
        → F1 = 0.000
```

### Lesson
> **Never use naive tokenization for German text.** German compound words (Untersuchungshaft, Strafprozessordnung, Bundesgerichtsentscheid) are a SINGLE token when written together but become multiple tokens when hyphenated. A proper German tokenizer must handle both forms.

---

## Experiment 2: Run 1 — Add FAISS + GPU (May 19)

### Hypothesis
"Adding semantic search (FAISS embeddings) will fix the BM25 compound word problem because embeddings capture MEANING not just keywords"

### Changes from Experiment 1
| Parameter | Before | After |
|-----------|--------|-------|
| Hardware | CPU | **GPU** |
| Search | BM25 only | **FAISS + BM25 hybrid (RRF)** |
| Embedding model | None | **paraphrase-multilingual-MiniLM-L12-v2 (384d)** |
| Corpus courts | 100K (4%) | **200K (8.1%)** |
| Few-shot bank | 119 types | **656 law + 58 court types (3,555 examples)** |
| HyDE | Not working | **Enabled with type hints from few-shot** |

### Result: **F1 = 0.006** (barely above zero)

### What Went Wrong
1. **188.5 citations per query** — no filtering! Every BM25 result + every FAISS result dumped into output
2. **Precision ≈ 0.5%** — 188 predictions, maybe 1 correct
3. **Embedding model too weak** — MiniLM-384d can't distinguish "Art. 221 StPO" from "Art. 222 StPO" (99% cosine similarity)
4. **Few-shot type matching wrong 70% of time** — matched immigration law instead of criminal procedure

### Specific Failure (Val Q3 — debt remission):
```
Expected domain: OR (Obligationenrecht / Contract Law)
Few-shot matched: WHG (Water Management Act!)
Why: Word "Schuld" (debt) has overlap with "Schuldiger" (guilty) in environmental law text
Impact: All HyDE generation and searches went to WRONG corpus section
```

### Lesson
> **A 384d general-purpose embedding model cannot distinguish between Swiss law articles.** Legal articles are syntactically identical ("Abs. 1 ... wird bestraft mit..."). The differences are in 1-2 domain words. You need either domain-specific fine-tuning or a larger model (1024d+).

> **Few-shot matching by word overlap is unreliable for legal terminology.** "Schuld" (debt) ≠ "Schuld" (guilt) — same word, different legal domain.

---

## Experiment 3: Run 2 — Fix Output Quality (May 19)

### Hypothesis
"Reducing output from 188 → 25 citations and adding a reranker will improve precision without hurting recall"

### Changes
| Parameter | Run 1 | Run 2 |
|-----------|-------|-------|
| Retrieval | BM25 + FAISS | **FAISS only** (removed BM25) |
| Agent output format | Free-text regex parsing | **GBNF grammar JSON** |
| Reranker | None | **BAAI/bge-reranker-v2-m3** |
| Citations per query | 188 (all raw results) | **25** (reranked top-25) |
| Agent iterations | 3 | **6** |

### Result: **F1 = 0.006** (UNCHANGED despite massive engineering)

### The Critical Insight
```
188 citations at F1=0.006 → ~1 correct hit in 188
 25 citations at F1=0.006 → ~0.15 correct hit in 25

Reducing output didn't help because the correct citations AREN'T IN THE RETRIEVAL POOL.
If FAISS doesn't find the gold article in top-50, no reranker can rescue it.
```

### What We Confirmed
- ✅ GBNF grammar works (zero parse failures)
- ✅ Reranker reduces noise (188 → 25 is cleaner)
- ❌ But recall is still 0 for most queries (correct articles not retrieved)
- ❌ Cross-lingual reranking (English query ↔ German text) is 10-20% weaker

### Lesson
> **You cannot rerank what you never retrieved.** The retrieval pool (top-50 from FAISS) determines the CEILING. If the correct article isn't in the pool, nothing downstream can help. Fix retrieval first.

> **Precision improvements are worthless when recall is zero.** Reducing from 188 to 25 predictions looks good but means nothing if 0/25 are correct.

---

## Experiment 4: Run 3 — German Agent (May 20) ✅ BREAKTHROUGH

### Hypothesis
"Making the agent think and search entirely in German will eliminate the English→German gap that causes retrieval failure"

### Changes
| Parameter | Run 2 | Run 3 |
|-----------|-------|-------|
| Agent language | English reasoning | **German reasoning + German queries** |
| Reranking mode | English query ↔ German text | **German HyDE doc ↔ German text** (monolingual) |
| HyDE type_hints | From few-shot bank | **None** (removed — were 70% wrong) |
| rerank_top_n | 10 | **25** |
| max_iterations | 6 | **4** |
| Score cutoff | None | **-3.0** |

### Result: **F1 = 0.034** — **5.5× IMPROVEMENT** 🎉

### Why It Worked (Three Changes Compounded)

**1. German agent (+3× by itself)**
```
Before: English thought → English query → search German corpus (mismatch!)
After:  German thought → German query → search German corpus (match!)

Example:
  Before: "I'll search for pre-trial detention requirements" → FAISS can't match to German
  After:  "Ich suche nach Voraussetzungen der Untersuchungshaft" → direct token overlap with StPO
```

**2. Monolingual reranking (+50%)**
```
Before: reranker(English_query, German_doc) → cross-lingual gap hurts scores
After:  reranker(German_HyDE_doc, German_doc) → same-language comparison = better discrimination
```

**3. Remove type hints (+20%)**
```
Before: HyDE prompt includes "types: VZAE, HVUV" → HyDE generates immigration-themed text
After:  HyDE prompt has no type hint → generates based solely on query meaning
```

### What Still Failed
- Agent misinterpreted Q1 (IP): latched onto "provisional measures", ignored IP/copyright
- Translation error Q3: "remission of debt" → "Entschuldigungsbrief" (apology letter!)
- Agent STILL never signals "done" — exhausts all 4 iterations

### Lesson
> **The single biggest improvement (5.5×) came from language alignment.** For cross-lingual RAG, making the intermediate reasoning layer match the corpus language is more important than any retrieval algorithm improvement.

> **Removing a broken component (type hints) can be as valuable as adding a new one.** The few-shot bank was wrong 70% of the time — removing it eliminated a source of systematic error.

---

## Experiment 5: Run 4 — PRF Replaces Few-Shot (May 24) ✅ IMPROVEMENT

### Hypothesis
"Using actual corpus documents (PRF) as HyDE context is better than a pre-built few-shot bank"

### Changes
| Parameter | Run 3 | Run 4 |
|-----------|-------|-------|
| Few-shot bank | 3,279 law + 276 court examples | **REMOVED** |
| Few-shot FAISS | 3,555 vectors | **REMOVED** |
| HyDE context | None | **PRF: top-3 FAISS results as "Referenztexte"** |

### Result: **F1 = 0.040** — +17% improvement

### How PRF→HyDE Works
```
Step 1: Agent generates German query "Untersuchungshaft Voraussetzungen StPO"
Step 2: Raw FAISS search → top 3 results (may be imperfect but real corpus text)
Step 3: Feed those 3 results as context into HyDE prompt:
        "Referenztexte aus der Datenbank:
         - Art. 212 StPO: Die Beschuldigte Person wird aus der Haft entlassen...
         - Art. 226 StPO: Das Zwangsmassnahmengericht entscheidet..."
Step 4: LLM generates hypothetical article GROUNDED in real vocabulary
Step 5: Embed hypothetical article → FAISS search → better results
```

### Per-Query Results (first detailed breakdown):
| Query | F1 | What Happened |
|-------|-----|---------------|
| Q5 (parental contact) | **0.111** | Best! Found ZGB family law correctly |
| Q9 (child maintenance) | **0.103** | Found ZGB maintenance articles |
| Q4 (holographic testament) | **0.000** | PRF returned wrong docs → HyDE drifted |
| Q7 (donation/gift) | **0.000** | PRF returned wrong domain entirely |
| Q8 (fiduciary duty) | **0.000** | Complete miss |

### The PRF Failure Mode
```
When PRF works (Q5, Q9):   Good initial results → Good HyDE context → Better final results
When PRF fails (Q4, Q7):   Wrong initial results → Wrong HyDE context → WORSE final results

PRF is a "good gets better" technique:
  ✅ If initial retrieval is in the right ballpark → amplifies signal
  ❌ If initial retrieval is in wrong domain → amplifies NOISE
```

### Lesson
> **PRF (Pseudo-Relevance Feedback) is a double-edged sword.** It amplifies whatever signal the initial retrieval provides. If initial retrieval is wrong (50% of queries with weak embeddings), PRF makes it WORSE by grounding HyDE in irrelevant documents.

> **Removing dead code (few-shot bank) simplified the system with no quality loss.** The bank was 185 lines of code that produced zero signal.

---

## Experiment 6: Pipeline V2 — New Architecture (May 31) ✅ ARCHITECTURAL SHIFT

### Hypothesis
"A planner that decomposes the question into 6 typed search directions will achieve broader coverage than a single agent iterating"

### Complete Redesign
| Component | Runs 1-4 | Pipeline V2 |
|-----------|----------|-------------|
| Architecture | Single ReAct agent | **Planner → 6 Executor directions** |
| Embedding | MiniLM-384d | **Qwen3-Embedding-0.6B (1024d)** |
| Reranker | BAAI/bge-reranker-v2-m3 | **Qwen3-Reranker-0.6B** |
| Planner output | Iterative free-form | **Structured JSON: 6 directions with filter codes** |
| Search filtering | None (search whole corpus) | **Filter by law_code/court_code** |

### Result: **F1 = 0.077** (2 TP: Art. 212 Abs. 3 StPO, Art. 227 Abs. 1 StPO)

### What the Planner Produced
```json
{
  "directions": [
    {"corpus": "laws", "filter_codes": ["StPO"], "seed_queries": ["Haftverlängerung"]},
    {"corpus": "courts", "filter_codes": ["6B_"], "seed_queries": ["Haft Kollusionsgefahr"]},
    {"corpus": "courts", "filter_codes": ["BGE_IV"], "seed_queries": ["Leitentscheid Haft"]}
  ]
}
```

### Critical Bugs
1. **Reranker broken** — Qwen3-Reranker gives uniform 0.0097 scores to ALL documents
2. **Wrong court prefix** — Planner chose `6B_` (sentencing) instead of `1B_` (detention)
3. **Only 3 directions** — Grammar allowed "3-6", model chose minimum
4. **max_tokens=800 truncated** — JSON cut mid-output, fell back to generic plan

### Lesson
> **Upgrading embedding model (384d → 1024d) helps but doesn't solve the problem.** Qwen3-1024d is better than MiniLM-384d but still can't reliably distinguish Swiss law articles.

> **The planner architecture has HIGH variance.** When routing is correct (StPO → 1B_), it finds citations that single-agent never could. When routing is wrong (6B_ instead of 1B_), it catastrophically misses entire corpus sections.

---

## Experiment 7: V3 — Token Fix (May 31) ❌ REGRESSION

### Hypothesis
"Increasing max_tokens will fix the JSON truncation crash"

### Changes
```python
max_tokens_planner: 800 → 1500
max_tokens_executor: 200 → 350
+ token ID resolution for reranker
```

### Result: **F1 = 0.039** (1 TP) — **50% REGRESSION**

### Why More Tokens Made Things WORSE
```
V2: Planner truncated at 800 tokens → fell back to generic plan → found 2 TP
V3: Planner completed at 1500 tokens → produced BAD plan → found only 1 TP

The generic fallback plan (V2) was actually BETTER than the model's real plan (V3)!
The model's "complete" plan used wrong court codes and repetitive queries.
```

### Lesson
> **Fixing a crash isn't the same as fixing the system.** The crash (JSON truncation) was masking a deeper problem: the model produces bad plans. The generic fallback happened to be more diverse than the model's actual output.

> **Token ID resolution doesn't fix a fundamentally broken model.** The reranker's uniform scoring is a model architecture issue, not a tokenization issue.

---

## Experiment 8: V4 — Disable Reranker (May 31) ✅ BEST RESULT

### Hypothesis
"The reranker is actively harmful. Disabling it and using raw RRF scores should improve results."

### Changes
```python
rerank_score_cutoff: 0.2 → 0.0  # Effectively disabled
+ Expanded system prompt with 6-direction Haft example
+ Added routing context for BGE_I and 7B_
```

### Result: **F1 = 0.078** (4 TP) — **BEST EVER** 🏆
- `Art. 221 Abs. 1 StPO` ✅
- `Art. 221 Abs. 2 StPO` ✅
- `Art. 212 Abs. 3 StPO` ✅
- `Art. 100 Abs. 1 BGG` ✅

### Why Disabling a Component IMPROVED Results
```
With reranker (V3):
  RRF finds Art. 221 (score 0.025) → reranker scores it 0.0097 → below 0.2 cutoff → DROPPED

Without reranker (V4):
  RRF finds Art. 221 (score 0.025) → keeps it → IN OUTPUT → TRUE POSITIVE
```

The reranker was KILLING good results by assigning uniform near-zero scores. Removing it let the RRF signal pass through.

### Lesson
> **A broken component is worse than no component.** This is perhaps the most important lesson in this project. The reranker LOOKED useful (it's a transformer! it should discriminate!) but its uniform scores actively destroyed the RRF signal.

> **Always validate components in isolation before integrating.** If we had tested the reranker on known-good/known-bad pairs first, we would have discovered it's broken and never integrated it.

---

## Experiment 9: V5 — Force 6 Directions (June 4) ❌ REGRESSION

### Hypothesis
"Forcing 6 directions (instead of 3) will cover more gold citation domains"

### Changes
```python
max_tokens_planner: 1500 → 3000
max_chars_context: 12000 → 8000  # "to prevent overflow"
GBNF grammar: "3-6 directions" → "exactly 6 mandatory"
System prompt: +1 more example, +domain checklists
```

### Result: **F1 = 0.059** (3 TP) — **24% REGRESSION**

### The Invisible Failure: Context Truncation
```
Context assembly order:
  1. Laws routing header (2,284 chars) ←── always fits
  2. Laws domain sections (5,745 chars) ←── always fits
  3. Court routing header (1,088 chars) ←── SOMETIMES CUT AT 8000
  4. Court domain sections (2,500 chars) ←── ALWAYS CUT
  5. Terminology bridge (1,776 chars) ──── ALWAYS CUT

At max_chars=8000:
  Laws consume 2,284 + 5,745 = 8,029 chars → ALREADY OVER LIMIT
  Courts: ZERO chars reach the planner!
  
Result: Planner never sees instructions for 7B_ or BGE_I → can't route there
```

### The Diversity Problem
```
Planner output (6 directions):
  Dir 1: StPO (Haft)          ← useful
  Dir 2: 1B_ (courts)         ← useful  
  Dir 3: BGE_IV (precedents)  ← useful
  Dir 4: BV (constitution)    ← WRONG (Art. 192, 21, 123a = irrelevant)
  Dir 5: StPO (Rechtsmittel)  ← redundant with Dir 1
  Dir 6: StPO (Verfahren)     ← redundant with Dir 1

3/6 directions search the SAME corpus section (StPO) with slightly different queries.
The grammar forces 6 directions but can't force DIVERSITY.
```

### Lesson
> **Character limits are invisible failure modes.** Nothing crashes when you truncate context. The planner just silently produces worse plans because it can't see the routing information. ALWAYS log what gets cut.

> **Forcing quantity (6 directions) ≠ forcing quality (6 diverse directions).** GBNF grammar can enforce structure (count, field types) but not semantics (diversity, correctness).

> **The "safety" change (12000→8000) was the actual cause of regression.** It was made to prevent a theoretical overflow that never happened, but caused a real truncation that always happened.

---

## Experiment 10: V6 — Post-Processing Dedup+Enrich (June 5) ❌ REGRESSION

### Hypothesis
"Post-processing that removes duplicate filter codes and enriches single-code directions will force diversity"

### Changes
```python
LAW_TYPES_FOR_PROMPT: all 200+ codes → top-40 only (saves ~7800 chars)
max_chars_context: 8000 → 12000 (reverted)
+ Dedup: strip codes already used by higher-priority directions
+ Enrich: single-code directions get companion codes (StPO→+BStKR, 1B_→+7B_)
+ Fallback: 0-code directions get domain defaults from rechtsgebiet
```

### Result: **F1 = 0.039** (2 TP) — **FURTHER REGRESSION**

### Why Dedup Hurt
```
Planner output:
  Dir 1: ["StPO"]              ← kept
  Dir 5: ["StPO"]              ← StPO REMOVED (already used by Dir 1)
  Dir 5 after dedup: []        ← empty! Falls through to unfiltered search

But Dir 5 was searching "Rechtsmittel" (appeal procedures) in StPO.
Removing StPO from Dir 5 means it can't find appeal articles (Art. 382-396).
Those are DIFFERENT articles in the SAME code (StPO) — legitimate use of same filter!
```

### Lesson
> **Post-processing heuristics interact unpredictably.** Dedup assumes same filter code = same search. But "StPO Haft" and "StPO Rechtsmittel" are completely different sub-domains within the same code. The dedup was semantically wrong.

> **Never add multiple changes without A/B testing each one.** We added top-40 + context revert + dedup + enrich simultaneously. When F1 dropped, we couldn't tell which change caused it.

---

## Master Summary: What Definitively Worked

| # | Change | Impact | Confidence |
|---|--------|--------|------------|
| 1 | German agent (not English) | +5.5× F1 | ✅ HIGH — proven across multiple runs |
| 2 | Disable broken reranker | +2× F1 | ✅ HIGH — immediate, repeatable |
| 3 | Remove type-hint poisoning | Part of +5.5× | ✅ HIGH — wrong 70% of time |
| 4 | Monolingual reranking (DE↔DE) | Part of +5.5× | ✅ HIGH — eliminates cross-lingual gap |
| 5 | GBNF grammar for structured output | Zero parse failures | ✅ HIGH — no regression from this |
| 6 | PRF instead of few-shot bank | +17% | ⚠️ MEDIUM — helps when initial retrieval is good |

## Master Summary: What Definitively Failed

| # | Change | Impact | Root Cause |
|---|--------|--------|-----------|
| 1 | Naive German tokenizer | F1=0.000 | Compound words don't match hyphenated forms |
| 2 | Few-shot type matching | 70% wrong | Word overlap ≠ legal domain similarity |
| 3 | Cross-lingual reranking | -10-20% | Transformer can't bridge EN↔DE gap at 0.6B scale |
| 4 | Qwen3-Reranker-0.6B | Uniform 0.01 scores | Model too small or wrong prompt format |
| 5 | max_chars=8000 | Killed court routing | Assembly order puts courts last → always cut |
| 6 | Dedup across directions | -24% F1 | Same code ≠ same search (StPO has 400+ articles) |
| 7 | More max_tokens (800→6000) | No improvement | Output quality unrelated to token budget |
| 8 | PRF when initial retrieval wrong | Amplifies error | PRF is "good gets better", not "bad gets fixed" |

## The Fundamental Learning

```
ITERATION HISTORY SHOWS ONE CLEAR PATTERN:

The BIGGEST wins came from REMOVING broken things:
  - Remove cross-lingual mismatch (German agent)     → 5.5×
  - Remove broken reranker                           → 2×  
  - Remove wrong type hints                          → part of 5.5×
  - Remove dead few-shot bank                        → +17%

The BIGGEST losses came from ADDING clever things:
  - Add post-processing dedup                        → -24%
  - Add context truncation for "safety"              → -24%
  - Add more max_tokens                              → no change
  - Add token ID resolution                          → no change

LESSON: In debugging, SUBTRACTION is more powerful than ADDITION.
If something isn't working, first ask "what can I REMOVE?" not "what can I ADD?"
```
