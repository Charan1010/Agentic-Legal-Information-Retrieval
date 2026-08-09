# Pipeline V5 Debug Log — Grounded Analysis

**Run:** 2026-06-04 18:07:30 | **Query count:** 1 | **Total time:** 128.8s  
**Result:** P=0.050 | R=0.071 | **F1=0.059** (worse than V4's 0.078)

**Changes since V4:** max_tokens_planner 1500→3000, max_chars context 12000→8000, reranker cutoff 0.2→0.0, planner prompt expanded with 6-direction Haft example + BGE_I/7B_ routing

---

## Executive Summary

The planner now successfully generates 6 directions (fixed from V4's 3), and JSON parsing succeeds cleanly. However, **recall dropped from 4/42 to 3/42** because:
1. The planner's 6 directions are **not diverse enough** — 4/6 directions search StPO with near-identical queries
2. **Missing 7B_ entirely** — gold has 5 citations from 7B_ (Bundesstrafgericht); the planner didn't route there despite it being in the expanded prompt example
3. **Missing BGE_I entirely** — gold has 5 BGE citations under BGE_I (BGE 132 I 21, BGE 133 I 168/270); planner only used BGE_IV
4. **Missing StGB** — gold expects Art. 140 Abs. 1 StGB (Raub); no direction searches StGB
5. **Missing StBOG** — gold expects Art. 37/39 StBOG; no direction targets StBOG
6. Direction 4 (BV) pulled completely irrelevant articles (Art. 192, Art. 21, Art. 123a = constitutional revision, art freedom, sex offender measures)
7. The reranker with cutoff=0.0 kept all 106 candidates but score differentiation is almost zero (range 0.033→0.001)

---

## Query 1: Pre-Trial Detention Extension (Kollusionsgefahr)

### Gold Profile (42 citations)
| Category | Gold Citations | Count |
|----------|---------------|-------|
| StPO (Haft, Art. 212-240) | Art. 221 Abs. 1/2, Art. 222, Art. 227 Abs. 1, Art. 212 Abs. 3 | 5 |
| StPO (Rechtsmittel, Art. 382-397) | Art. 382/385/390/393/396 | 5 |
| StPO (Kosten, Art. 422-432) | Art. 422 Abs. 1/2, Art. 428 Abs. 1 | 3 |
| StPO (Verteidigung, Art. 135) | Art. 135 Abs. 3/4 | 2 |
| StGB (materielles Delikt) | Art. 140 Abs. 1 (Raub) | 1 |
| StBOG (Organisation) | Art. 37 Abs. 1, Art. 39 Abs. 1 | 2 |
| BGG | Art. 100 Abs. 1 | 1 |
| BGE_I (Grundrechte-Leitentscheide) | BGE 132 I 21 (×3 Erwägungen), BGE 133 I 168, BGE 133 I 270 | 5 |
| BGE_IV (Straf-Leitentscheide) | BGE 137 IV 122 (×4), BGE 139 IV 270, BGE 143 IV 168 | 6 |
| 1B_ (Einzelfälle) | 1B_210/2023, 1B_536/2018, 1B_90/2021, 1B_15/2023, 1B_357/2022, 1B_28/2022 E. 4.1 | 6 |
| 7B_ (Bundesstrafgericht) | 7B_496/2025, 7B_231/2025, 7B_69/2024, 7B_301/2024, 7B_12/2025 | 5 |

---

## Phase-by-Phase Analysis

### PHASE 1: PLANNER — 6 Directions Generated ✅ but Poorly Diversified ✗

**What it produced:**
| Dir | Corpus | Filter | Rechtsgebiet | Covers Gold? |
|-----|--------|--------|-------------|-------------|
| 1 | laws | StPO | Strafprozessrecht-Haft | ✅ Partial (Haft articles) |
| 2 | courts | 1B_ | Haftpraxis Einzelfälle | ✅ Correct area but wrong cases |
| 3 | courts | BGE_IV | Leitentscheide Haftrecht | ⚠️ Partial — needs BGE_I too |
| 4 | laws | BV | Verfassungsrecht | ✗ Pulled garbage (Art. 192, 21) |
| 5 | laws | StPO | Rechtsmittel | ⚠️ Right idea, wrong articles found |
| 6 | laws | StPO | Verfahren | ✗ Redundant with Dir 1 & 5 |

**CRITICAL GAPS (not searched at all):**
| Missing Target | Gold Citations Lost | Available Filter |
|---|---|---|
| 7B_ (Bundesstrafgericht) | 7B_496/2025, 7B_231/2025, 7B_69/2024, 7B_301/2024, 7B_12/2025 = **5** | `7B_` |
| BGE_I (Grundrechte-BGE) | BGE 132 I 21 (×3), BGE 133 I 168, BGE 133 I 270 = **5** | `BGE_I` |
| StGB (materiell) | Art. 140 Abs. 1 StGB = **1** | `StGB` |
| StBOG (Organisation) | Art. 37/39 StBOG = **2** | `StBOG` |
| BGG | Art. 100 Abs. 1 BGG = **1** | `BGG` |

**Impact of gaps:** 14/42 gold citations (33% of recall) are UNREACHABLE because no direction targets those codes.

**Root cause analysis:**
- The planner created 3 directions all filtering on `StPO` (Dirs 1, 5, 6) — these are effectively the same search space split into vague sub-topics
- Direction 6 ("Verfahrensrecht bei Haftverlängerung" / StPO) is nearly identical to Direction 5 ("Rechtsmittel gegen Haftverlängerung" / StPO) — pulled Art. 89, 91, 92, 314 (generic procedural timing articles with zero relevance)
- The prompt EXAMPLE explicitly shows 7B_ as Direction 4 and BGE_I in Direction 3, yet the model didn't follow it
- The CHECKLIST says: "STRAFPROZESS (Haft): MUSS = StPO + 1B_ + BGE_IV + BGE_I + Rechtsmittel + 7B_" — model partially followed but dropped BGE_I and 7B_

**Why 7B_ was missed despite being in the example:**
The `max_chars=8000` truncation may have cut the context before the court routing for BUNDESSTRAFGERICHT reached the planner. The full context builds up to ~14,440 chars naturally, and the Bundesstrafgericht section is appended LAST (it's the last court section). With 8000 cap, it likely got truncated.

---

### PHASE 2: EXECUTORS — Semantic Search Quality Issues

#### Direction 1 (StPO laws) — 10 citations, 6.6s
**Seed:** `"Untersuchungshaft Haftverlängerung Kollusionsgefahr Verhältnismässigkeit"`
- ✅ Found: Art. 227 Abs. 1 (Haftverlängerung), Art. 212 Abs. 3 (Überhaft)
- ✗ Missed: Art. 221 Abs. 1/2, Art. 222 (despite being THE core articles)
- Only 1 iteration (executor gave second query, but diversity check stopped it)
- **Problem:** Art. 221 Abs. 1 StPO (THE most important article) was NOT in the top-10 results. It was injected later as a "procedural default" (rank 98 with score 0.003). This means the embedding quality for Art. 221 is poor relative to the query.

#### Direction 2 (1B_ courts) — 30 citations, 17.5s  
**Best direction by volume.** 3 full iterations before timeout.
- ✅ Found: 1B_28/2022 E. 4.4 (this IS in gold... but as E. 4.1, not 4.4 — **close miss**)
- ✗ Missed all 6 gold 1B_ citations (1B_210/2023, 1B_536/2018, 1B_90/2021, 1B_15/2023, 1B_357/2022, 1B_28/2022 E. 4.1)
- **Problem:** The search found OLDER cases (2007-2016 era) instead of the 2021-2025 cases in gold. The embedding space may not differentiate recency, and newer cases aren't scored higher.
- **1B_28/2022 near-miss:** We found E. 4.4 but gold wants E. 4.1 from the same case. The chunking splits Erwägungen, so we grabbed the wrong section.

#### Direction 3 (BGE_IV courts) — 13 unique citations, 11.0s
- ✗ Found ZERO gold BGE citations (gold wants BGE 137 IV 122, BGE 139 IV 270, BGE 143 IV 168)
- What it found instead: BGE 150 IV 405, BGE 146 IV 311, BGE 146 IV 279 — these are about "Sicherheitshaft" and "Wiederholung Landesverweisung", tangentially related at best
- **Problem:** The seed query `"Gutachten Haftverlängerung Kollusionsgefahr"` has "Gutachten" (expert opinion) which is irrelevant here — it's an IV/disability term contaminating criminal search
- Score plateau: all results scored 0.014-0.016 (no differentiation = essentially random retrieval)

#### Direction 4 (BV laws) — 18 unique citations, 14.1s
- ✅ Found: Art. 10 Abs. 2 BV (persönliche Freiheit) — relevant but NOT in gold
- ✗ Found garbage: Art. 192 (constitutional revision), Art. 21 (freedom of art), Art. 123a (sex offender detention), Art. 139 (popular initiative), Art. 20 (freedom of research)
- **Root cause:** BV has only 658 articles and the embedding model can't distinguish "Freiheit" in Art. 10 (personal liberty) from "Freiheit" in Art. 20/21 (academic/artistic freedom). The model latches onto the word "Freiheit" literally.

#### Direction 5 (StPO Rechtsmittel) — 20 unique citations, 10.4s
- ✅ Found: Art. 428 Abs. 1 StPO (Kosten Rechtsmittelverfahren) — IN GOLD!
- ✅ Found: Art. 396 Abs. 2 StPO (close to gold's Art. 396 Abs. 1 — different Absatz)
- ✗ Missed: Art. 382, 385, 390, 393 (core Legitimation/Beschwerde articles)
- **Problem:** Seed query `"Rechtsmittel Haftverlängerung Beschwerdefrist Instanzenzug"` is too specific. The gold articles are more general (who can appeal? what can be appealed?), not specifically about Haftverlängerung.
- Iter 1 searched "Kollisionsgefahr Prüfung Haftgrund Rechtsgrundlage" — wrong concept entirely
- Iter 2: empty query → forced stop

#### Direction 6 (StPO Verfahren) — 10 citations, 4.5s
- ✗ All irrelevant: Art. 89 (deadlines can't be extended), Art. 91 (how to count days), Art. 314 (suspension of investigation), Art. 165 (obligation to appear)
- **This entire direction was wasted** — it's a redundant StPO search that found deadline/timing articles instead of substantive Haft procedure
- Only 1 iteration (executor gave second query but diversity check likely filtered)

---

### PHASE 3: AGGREGATION + RERANKING

**Input:** 96 unique citations + 11 procedural defaults = 106 candidates  
**Output:** Top 60 (max_final_citations=60)

**Reranker performance (Qwen3-Reranker-0.6B):**
- Score range: 0.0328 → 0.0016 — extremely compressed (factor of ~20× between best and worst)
- Top 26 items score 0.026-0.033 (genuine differentiation)
- Items 27-106 all score 0.014-0.016 (essentially a tie = random ordering)
- **The reranker can't meaningfully rank 80% of candidates**

**Procedural defaults (11 injected):**
- Art. 221 Abs. 1 StPO → rank 98 (score 0.003) — this IS gold but ranked near-bottom
- Art. 100 Abs. 1 BGG → rank 100 (score 0.002) — also gold, also buried
- Art. 31 Abs. 3 BV → rank 97 (score 0.003) — relevant but not in gold
- **These defaults saved nothing** because they ranked below the top-60 cutoff

**Critical: The procedural defaults that ARE in gold (Art. 221, Art. 100 BGG) were injected but then ranked SO LOW they didn't make the final 60.** The reranker scored them at 0.002-0.003 vs the 0.016 cutoff for rank 60. This means the reranker actively hurts recall by burying known-good citations.

---

## What Improved vs V4

| Aspect | V4 | V5 | Verdict |
|--------|----|----|---------|
| Planner directions | 3 | 6 | ✅ Fixed |
| JSON parsing | Failed once (retry) | Clean first try | ✅ Fixed |
| Reranker cutoff | 0.2 (killed everything) | 0.0 (kept everything) | ✅ Fixed |
| Total prompt tokens | ~6925 est | 27,701 chars logged | ✅ No overflow |
| Overall F1 | 0.078 | 0.059 | ✗ Regressed |

---

## What Regressed vs V4

| Issue | Cause | Impact |
|-------|-------|--------|
| F1 dropped 0.078→0.059 | Lost Art. 221 Abs. 1 and 1 other that V4 found | -1 TP |
| Art. 221 Abs. 1 StPO not in output | Injected as default but reranker buried it at rank 98 | High |
| max_chars=8000 truncation | Court context for BGE/7B_ sections likely cut | Planner can't see Bundesstrafgericht guidance |

---

## Root Cause Analysis (Systemic)

### Problem 1: Embedding Quality for Core Articles
Art. 221 Abs. 1 StPO is THE foundational detention article, yet it scores 0.003 against queries about detention. This means the embedding for this article doesn't capture its semantic role. The article text is:
> "1 Untersuchungs- und Sicherheitshaft sind nur zulässig, wenn..."

The embedding model may be treating this as a generic conditional statement rather than recognizing it as the central norm.

### Problem 2: Planner Diversity Failure
Despite 6 directions, 4/6 filter on StPO with overlapping queries. The model read the example (which shows StPO, 1B_, BGE_IV, 7B_, StPO-Rechtsmittel, BV/BGG) but only partially followed it — replacing 7B_ with a third StPO direction and replacing BGE_I with nothing.

### Problem 3: Reranker Score Compression  
With scores ranging 0.033-0.001 across 106 items, the reranker provides almost no useful signal beyond the top ~25. Items 27-60 are essentially randomly ordered. The model is too small (0.6B params) to differentiate legal relevance at this granularity.

### Problem 4: Temporal Blind Spot
Gold expects very recent cases (7B_496/2025, 7B_231/2025, 1B_210/2023). The retriever found older cases (1B_300/2008, 1B_288/2008). Embeddings don't encode recency, and there's no recency boost in the scoring.

### Problem 5: Chunking Granularity
1B_28/2022 appears in our results (E. 4.4) but gold wants E. 4.1 from the same case. This is a chunking mismatch — the right case is found but the wrong Erwägung is retrieved.

---

## Specific Recommendations

### Immediate Fixes (High Impact)

1. **Revert max_chars to 12000** — the 8000 truncation cuts the Bundesstrafgericht/7B_ section from context, preventing planner from routing there

2. **Force diversity in planner output** — add a constraint: "KEINE 3+ directions mit gleichem filter_code. Maximal 2 directions dürfen denselben Code verwenden." This would force the model to pick 7B_, StGB, StBOG instead of repeating StPO 3×

3. **Fix procedural defaults injection** — currently defaults are appended AFTER all search results with a synthetic score of 0.003. They should either:
   - Be force-included in final output regardless of rank, OR
   - Be scored with the same embedding model against the query (they'd score ~0.016+ which gets them into top-60)

4. **Add BGE_I to Direction 3** — the planner example shows `["BGE_IV", "BGE_I"]` together but model only used BGE_IV. Could either:
   - Make this a hard rule in the prompt: "Bei Haft-Fragen: BGE_IV UND BGE_I zusammen suchen"
   - Or ensure the routing context includes BGE_I←→Haft mapping (currently in the court section that gets truncated at 8000)

### Medium-Term Fixes

5. **Improve BV direction** — the BV search is nearly useless (pulled art freedom, constitutional revision). Better approach: hardcode the 5-6 BV articles that matter for detention cases (Art. 10, 31, 32, 36) as procedural defaults instead of searching the whole BV corpus

6. **Add recency scoring** — boost cases from 2020+ by a factor (e.g., RRF_score × 1.5 for cases ≤3 years old). This would help find the 2023-2025 cases in gold.

7. **Executor query diversification** — the executor's "thought" field should explicitly list what sub-topics remain unexplored. Currently Iter 1-3 repeat the same concepts.

---

## Token Budget (Confirmed Working)

```
System prompt (with codes):  18,588 chars (logged)
Context (injected):           8,019 chars (truncated from ~14,440)  
User message (context+Q):    9,096 chars
TOTAL PROMPT:                27,701 chars (~6,925 tokens @4ch/tok)
n_ctx:                       16,384
Output room:                 ~9,459 tokens
max_tokens_planner:          3,000
Status:                      ✅ NO OVERFLOW — JSON parsed cleanly
```

The context truncation to 8000 worked to prevent overflow, but at the cost of cutting routing guidance that would have helped the planner choose 7B_ and BGE_I.

---

## Comparison: V4 vs V5 True Positives

| Citation | V4 | V5 | Status |
|----------|----|----|--------|
| Art. 221 Abs. 1 StPO | ✅ | ✗ (rank 98) | **REGRESSED** — reranker buried it |
| Art. 212 Abs. 3 StPO | ✅ | ✅ | Stable |
| Art. 227 Abs. 1 StPO | ✅ | ✅ | Stable |
| Art. 428 Abs. 1 StPO | ✗ | ✅ | **NEW** — Direction 5 found it |
| Art. 221 Abs. 2 StPO | ✅ | ✗ | **REGRESSED** |

Net: -1 TP (lost 2, gained 1)

---

## Priority Action Items

| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| P0 | Revert max_chars 8000→12000 (or increase n_ctx to 32768) | Planner sees 7B_/BGE_I guidance |
| P0 | Force-include procedural defaults in final output (bypass reranker rank) | +2 TP (Art. 221, Art. 100 BGG) |
| P1 | Add diversity constraint: max 2 directions per filter_code | Prevents 3× StPO waste |
| P1 | Add StGB direction for materielles Delikt | +1 TP (Art. 140) |
| P2 | Combine BGE_IV + BGE_I in one direction | +2-3 TP from BGE_I Leitentscheide |
| P2 | Add StBOG to routing | +2 TP (Art. 37, 39) |
| P3 | Recency boost for 2020+ cases | Better 1B_ and 7B_ hits |
