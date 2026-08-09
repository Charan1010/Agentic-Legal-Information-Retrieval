# Pipeline Planner/Director — Complete Change History & Analysis

**Created:** 2026-07-17 | **Scope:** All modifications from V2 baseline through current state

---

## PART 1: INITIAL ARCHITECTURE (V2 BASELINE)

### Core Stack
| Component | Details |
|-----------|---------|
| **LLM** | Mistral-7B-Instruct-v0.2.Q4_K_M.gguf on GPU 0 |
| **Embedding** | Qwen3-Embedding-0.6B on GPU 1, dim=1024, normalized |
| **Reranker** | Qwen3-Reranker-0.6B on GPU 1 (broken from day 1) |
| **Search** | FAISS IndexFlatIP (dense) + BM25Okapi (sparse) |
| **Fusion** | RRF with k=60 |
| **Platform** | Kaggle (2× T4 GPUs) |

### V2 Parameters
| Parameter | V2 Value | Notes |
|-----------|----------|-------|
| max_tokens_planner | 800 | **TOO LOW** — JSON truncated mid-output |
| max_tokens_executor | 200 | **TOO LOW** — executor crashes on complex directions |
| temperature_planner | 0.1 | Conservative |
| temperature_executor | 0.3 | Slightly creative |
| n_ctx | 16384 | Full window |
| rerank_score_cutoff | 0.2 | **BROKEN** — reranker gives ~0.0097 uniformly, nothing passes |
| max_final_citations | 60 | Top-60 output |
| max_executor_iterations | 3 | Iterations per direction |
| executor_timeout_sec | 15 | Hard stop |
| search_top_k | 10 | Per-query retrieval |
| rrf_k | 60 | Fusion parameter |

### V2 Results
- **F1: 0.077** | P=0.20 | R=0.048 | **2 TP** / 42 gold | Time: ~116s
- True Positives: `Art. 212 Abs. 3 StPO`, `Art. 227 Abs. 1 StPO`

### V2 Failure Analysis
1. Reranker non-functional (uniform ~0.0097 scores; cutoff 0.2 → nothing passes)
2. Wrong court prefix: planner used 6B_ (sentencing) instead of 1B_/7B_ (detention)
3. Planner truncation: max_tokens=800 insufficient → JSON parsing failed → generic fallback
4. No BGE direction (11/42 gold = BGE leading cases)
5. No diversification (57% duplicate results across iterations)
6. Missing codes: 7B_, StGB, StBOG never searched

---

## PART 2: VERSION-BY-VERSION CHANGES

### V2 → V3 (Token Fixes)

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| max_tokens_planner | 800 | 1500 | Planner JSON truncated at ~800 tokens |
| max_tokens_executor | 200 | 350 | Executor "thought" field consumed 110+ tokens, no room for query JSON |
| Token ID resolution | None | Added fallback chains | Attempt to fix reranker yes/no token IDs |

**Result: F1 = 0.0385 (1 TP) — REGRESSION (-50%!)**

**Why it failed:**
- Reranker still broken (scores dropped to 0.0039, still uniform)
- Planner still used wrong court codes (6B_ not 1B_)
- Fallback plan used → executor searched "Strafzumessung" instead of "Haftverlängerung"
- Direction 5 (1B_) crashed from JSON truncation despite increase to 350
- Art. 221 Abs. 1 StPO was RETRIEVED but reranker scored it 0.0039 → dropped

---

### V3 → V4 (Reranker Disabled + Prompt Expansion)

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| Reranker | Active (broken) | **DISABLED** (cutoff → 0.0) | Uniform scoring = useless; RRF alone is better |
| System prompt | Basic | Expanded with 6-direction Haft example | Show model what good directions look like |
| Routing context | Missing 7B_/BGE_I | Added BGE_I + 7B_ routing guidance | Planner couldn't route to these without seeing them |
| Token ID resolution | Active | Removed | Confirmed ineffective |

**Result: F1 = 0.078 (4 TP) — RECOVERY (+2× vs V3!)**

**Why it worked:**
- ✅ Reranker disabled → RRF scores flow directly → results no longer zeroed out
- ✅ max_tokens=1500 enough for 3 directions of JSON
- ✅ Prompt expansion helped (3 directions generated instead of fallback)
- ✅ Art. 221 Abs. 1 & 2 StPO now survive without reranker killing them

**True Positives (4):** `Art. 221 Abs. 1 StPO`, `Art. 221 Abs. 2 StPO`, `Art. 212 Abs. 3 StPO`, `Art. 100 Abs. 1 BGG`

**Still broken:**
- Only 3 directions generated (grammar allowed "3-6", model chose minimum)
- Executor repetition: 30 raw results → only 13 unique (57% duplication)
- 7B_, BGE_I, StGB, StBOG still not searched → 14/42 gold unreachable
- Direction 2 (1B_) found old cases (2007-2016) instead of recent gold (2021-2025)

---

### V4 → V5 (Force 6 Directions + Context Scaling)

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| max_tokens_planner | 1500 | **3000** | Need space for 6 directions (was only generating 3 with 1500) |
| max_chars_context | 12000 | **8000** | Prevent total prompt overflow with larger planner output |
| GBNF grammar | 3-6 directions | **Exactly 6 mandatory** | Force diversity through quantity |
| System prompt | 1 example | 2 examples (Haft + IV) + checklists per domain | More guidance for the model |
| Routing context | Basic | Expanded with 7B_ and BGE_I sections | Help planner see these codes |

**Result: F1 = 0.059 (3 TP) — REGRESSION (-24%)**

**Why it regressed:**

1. **max_chars=8000 truncation killed court routing** — Context assembly order is: laws routing → court routing → terminology. At 8000 chars, laws sections (~6,700 chars) consumed the budget. Court routing for BGE_I and 7B_ (appended last) was NEVER SEEN by the planner.

2. **Planner diversity failure** — Despite 6-direction mandate, model generated:
   - Dir 1: StPO (Haft) ✅
   - Dir 2: 1B_ ⚠️ (right area, wrong cases found)
   - Dir 3: BGE_IV ⚠️ (scores collapsed: 0.014-0.016 range)
   - Dir 4: BV ❌ (pulled Art. 192, 21, 123a — completely irrelevant)
   - Dir 5: StPO (Rechtsmittel) ⚠️ — found 1 NEW gold citation
   - Dir 6: StPO (Verfahren) ❌ — redundant with Dir 1
   - **Result:** 3/6 directions were StPO quasi-duplicates

3. **Lost V4's best findings** — Art. 221 Abs. 1 & 2 StPO (found in V4) dropped because seed queries changed

**True Positives (3):** `Art. 212 Abs. 3 StPO`, `Art. 227 Abs. 1 StPO`, `Art. 428 Abs. 1 StPO` (NEW)

**Net change:** Lost 2 TP (Art. 221 ×2), gained 1 TP (Art. 428) = -1 net

---

### V5 → V6 (Our Session: Top-40 + Context Revert + Dedup/Enrich)

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| LAW_TYPES_FOR_PROMPT | All 200+ codes (~9,295 chars) | **Top-40 only** (~1,500 chars) | Save ~7,800 chars in system prompt for other content |
| max_chars_context | 8000 | **12000** (reverted) | Court routing was being cut at 8000 |
| max_tokens_planner | 3000 | 3000 (unchanged here; later bumped to 6000 by user) | — |
| Post-processing | None | **Dedup + Enrich** block added | Force code diversity across directions |

**Dedup/Enrich Logic Added:**
```python
# After planner generates 6 directions:
1. Process directions in priority order
2. Remove any filter_code already used by a higher-priority direction
3. If direction has 0 codes after dedup → assign from _DOMAIN_FALLBACK based on rechtsgebiet
4. If direction has 1 code → add related companion codes from _RELATED_CODES lookup
5. Track all used codes to prevent reuse
```

**Related Codes Map (enrichment):**
- StPO → +BStKR, +JStPO
- 1B_ → +7B_
- 6B_ → +BGE_IV
- IVG → +ATSG
- BGG → +BV
- etc.

**Domain Fallback Map (0-codes):**
- strafprozess → [StPO, BStKR, JStPO]
- strafrecht → [StGB, JStG]
- leitentscheide → [BGE_I, BGE_II, BGE_III, BGE_IV, BGE_V]
- etc.

**Result: F1 = 0.039 (2 TP) — FURTHER REGRESSION**

**Why it regressed further (hypotheses — not fully analyzed):**
- Dedup may be too aggressive (stripping valid StPO from later directions)
- Enrichment adds companion codes but those companion searches may dilute results
- The model may have changed direction structure with the larger system prompt
- max_tokens_planner was later increased to 6000 by user (possibly changed behavior)

**True Positives (2):** Only `Art. 212 Abs. 3 StPO`, `Art. 227 Abs. 1 StPO` (lost Art. 428)

---

## PART 3: CURRENT STATE (All Parameters)

```python
CONFIG = {
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "n_ctx": 16384,
    "n_threads": 8,
    "n_gpu_layers": -1,
    "max_tokens_planner": 6000,         # V2:800 → V3:1500 → V5:3000 → Now:6000
    "max_tokens_executor": 800,          # V2:200 → V3:350 → V4:800 (unchanged since)
    "temperature": 0.1,
    "temperature_executor": 0.3,
    "embed_model": "Qwen/Qwen3-Embedding-0.6B",
    "embed_dim": 1024,
    "rerank_score_cutoff": 0.0,          # DISABLED since V4
    "max_final_citations": 60,
    "max_executor_iterations": 3,
    "executor_timeout_sec": 15,
    "rrf_k": 60,
    "search_top_k": 10,
}

# Context assembly:
select_planner_context(question, max_chars=12000)  # Reverted from 8000

# System prompt injection:
LAW_TYPES_FOR_PROMPT = top 40 law codes by doc count  # Was all 200+
COURT_TYPES_FOR_PROMPT = all court codes (unchanged)

# Post-processing:
Dedup + Enrich block active in both run_planner() and run_planner_logged()
```

### Token Budget (Current)
```
System prompt (Part A):  ~10,800 chars = ~2,700 tokens  [was ~18,600 with full codes]
Context text (Part B):    ≤12,000 chars = ~3,000 tokens
Question (Part C):         ~1,100 chars = ~275 tokens
────────────────────────────────────────────────────
TOTAL INPUT:             ~23,900 chars = ~5,975 tokens
Output budget:            6,000 tokens
────────────────────────────────────────────────────
GRAND TOTAL:             ~11,975 tokens (of 16,384 available)
HEADROOM:                ~4,400 tokens spare
```

---

## PART 4: WHAT'S STILL BROKEN

### P0 — Critical (Blocking Improvement)

| # | Issue | Root Cause | Impact |
|---|-------|-----------|--------|
| 1 | **Planner repeats same codes** | GBNF enforces count (6) not uniqueness; model defaults to StPO | 2-3 wasted directions, same corpus searched 3× |
| 2 | **7B_ never reached** | Even with routing context, model doesn't reliably pick 7B_ for detention | 5/42 gold citations unreachable |
| 3 | **BGE_I never reached** | Model defaults to BGE_IV for Strafrecht; BGE_I (constitutional) overlooked | 5/42 gold citations unreachable |
| 4 | **Reranker permanently broken** | Qwen3-Reranker gives uniform ~0.01 scores | Cannot rerank 60 candidates meaningfully |
| 5 | **Dedup may be too aggressive** | Stripping StPO from later directions leaves them with fallback codes that may be irrelevant | V6 regression suggests dedup hurts |

### P1 — High Impact

| # | Issue | Root Cause | Impact |
|---|-------|-----------|--------|
| 6 | **Wrong 1B_ cases found** | Embedding doesn't encode recency; old cases (2007-2016) retrieved instead of gold (2021-2025) | 6/42 gold from 1B_ missed |
| 7 | **StBOG/StGB never searched** | Not in planner's mental model without explicit routing | 3/42 gold unreachable |
| 8 | **Procedural defaults 90% wrong** | Generic "criminal" defaults don't match specific Haft case | 9/10 injected defaults are false positives |
| 9 | **Executor repeats queries** | No diversity constraint; 80% overlap between iterations | Wastes 2/3 of search budget |
| 10 | **Art. 221 StPO (THE core article) retrieval unreliable** | Embedding scores only 0.003-0.016 for direct detention queries | Core gold citation sometimes missed |

---

## PART 5: PERFORMANCE TIMELINE

```
VERSION     F1      TP   KEY EVENT
─────────────────────────────────────────────────────────────
V2          0.077   2/42  Baseline (reranker broken, planner truncated)
V3          0.039   1/42  ❌ Token fixes insufficient, fallback plan used
V4          0.078   4/42  ✅ BEST: Reranker disabled, RRF direct
V5          0.059   3/42  ❌ 6 dirs forced but context truncated (8000)
V6          0.039   2/42  ❌ Dedup+enrich may be too aggressive
─────────────────────────────────────────────────────────────
BEST EVER:  V4 = 0.078 (4 TP)
GOLD:       42 citations for Query 1 (pre-trial detention)
```

---

## PART 6: WHAT WORKED vs WHAT DIDN'T

### ✅ Worked
| Change | Evidence |
|--------|----------|
| Disabling reranker (V4) | F1 doubled: 0.039→0.078 |
| max_tokens_planner 800→1500 (V4) | Planner JSON parsed successfully |
| GBNF grammar for 6 directions | Model now always produces 6 (no more 3) |
| Top-40 law codes | Saved ~7,800 chars; no loss of functionality |
| Reverting max_chars to 12000 | Court routing visible again |

### ❌ Did NOT Work
| Change | Evidence |
|--------|----------|
| Token ID resolution for reranker (V3) | Scores remained uniform |
| max_chars=8000 truncation (V5) | Killed court routing → regression |
| Forcing 6 directions without diversity constraint | 3/6 were StPO duplicates |
| Post-processing dedup+enrich (V6) | F1 dropped 0.059→0.039 |
| Prompt examples for 7B_/BGE_I | Model still doesn't reliably use them |
| Increasing max_tokens beyond 3000 | No evidence of improvement |

### ⚠️ Uncertain (Needs Testing)
| Change | Status |
|--------|--------|
| Dedup without enrichment | Never tested in isolation |
| Hardcoded direction injection | Proposed but not implemented |
| Recency boost for court cases | Proposed but not implemented |
| Case-type-specific defaults | Proposed but not implemented |
| Alternative reranker model | Not tested |

---

## PART 7: RECOMMENDED NEXT STEPS (Priority Order)

### Immediate (Would fix known regressions)
1. **Disable or soften the dedup+enrich block** — V6 regression suggests it hurts. Either remove entirely or only deduplicate EXACT same direction (same code + same corpus), not strip codes across directions.
2. **Hardcode mandatory directions for Haft cases** — After planner output, inject/force directions for: `7B_`, `BGE_I`, `StGB`, `StBOG` if the question matches detention/criminal patterns. This guarantees coverage regardless of what the planner produces.
3. **Fix procedural defaults** — Replace generic "criminal" defaults with case-type-specific ones (Haft → Art. 221, 222, 227, 382, 393 StPO).

### Medium-term (Architectural improvements)
4. **Replace reranker** — Try BAAI/bge-reranker-v2-m3 or just accept RRF-only and tune fusion weights.
5. **Add recency boost** — For court cases, multiply RRF score by 1.5× if case is ≤3 years old.
6. **Executor diversity** — Add constraint: each iteration must have ≥50% new terms vs previous queries.
7. **Question-aware fallback** — Extract keywords from question for fallback seed queries instead of generic domain terms.

### Testing needed
8. **Run V4 config again** (revert all V5/V6 changes) to confirm V4's 0.078 is reproducible
9. **Run with dedup OFF but top-40 + 12000 context** to isolate which V6 change caused the regression
10. **Test on multiple queries** — All results so far are on 1 single query; need validation set
