# Pipeline V2 Deep Analysis — Query 1

**Date:** 2026-05-31 | **F1:** 0.0769 | **Precision:** 0.20 | **Recall:** 0.048 (2/42 gold found)

---

## Executive Summary

The pipeline found only **2 of 42 gold citations** (Art. 212 Abs. 3 StPO, Art. 227 Abs. 1 StPO). Despite fixing max_tokens and adding robust token resolution for the reranker, the core problems are **structural**: wrong court prefix selection, missing BGE/1B_/7B_ directions, a reranker that still scores everything ~0.0097 (uniform = broken), and an executor that repeats near-identical queries producing the same results.

---

## 1. RERANKER — STILL COMPLETELY BROKEN (P0 CRITICAL)

### Symptom
All 68 candidates received scores in range **0.0096–0.0097** (variance < 0.0001). Cutoff is 0.2. NOTHING passes.

```
Score range: 0.0097 → 0.0096
Above cutoff (0.2): 0
Below cutoff (dropped): 68
```

### Root Cause Analysis
The "robust token ID resolution" we added was NOT active during this run — the log shows scores are still uniform ~0.0097, identical to the prior run. This means either:

1. **The notebook wasn't re-executed** after our fix (the cells with the new `_resolve_token_id` weren't re-run)
2. **OR** "Yes"/"No" resolve correctly via `convert_tokens_to_ids` but the model's logits for these tokens are dominated by other tokens → the softmax over just [yes_id, no_id] gives ~50/50 regardless of input

### Evidence of broken scoring
- Default-injected citations (Art. 29 BV, Art. 78 BGG, Art. 80 BGG, Art. 50 StGB) score **0.0097**
- Actual relevant StPO articles score **0.0096**
- The difference is **0.0001** — this is numerical noise, NOT meaningful ranking

### What the reranker SHOULD do
For a query about "Untersuchungshaft Kollusionsgefahr Haftverlängerung":
- Art. 221 StPO (Haftgründe) should score **>0.9**
- Art. 227 StPO (Haftverlängerung) should score **>0.8**
- Art. 50 StGB (Urteilsbegründung) should score **<0.1**

### Fix Required
**The reranker is fundamentally not discriminating.** Likely causes:
1. Token IDs still wrong (verify `[Qwen3Reranker] yes_id=X, no_id=Y` in cell output)
2. The `apply_chat_template` output may not end with the right generation prefix for this model
3. The model may need a different prompt format (not `"Given a query, determine if the document is relevant."`)
4. The `-1` logit position (last token) may not be where the model puts its yes/no decision — some models need a `generate()` call first

### Impact
Because reranker scores are uniform and ALL below cutoff (0.2), the pipeline falls back to a **top-10 by highest score** selection — but since scores are uniform, this is essentially random ordering. The final 10 citations are just the first 10 in the list order (defaults first, then direction-1 results).

---

## 2. PLANNER — ONLY 3 DIRECTIONS, MISSING CRITICAL CORPORA

### What the planner produced
| # | Corpus | Filter | Problem |
|---|--------|--------|---------|
| 1 | laws | StPO | ✓ Correct |
| 2 | courts | **6B_** | ❌ WRONG PREFIX — should be **1B_** and **7B_** |
| 3 | laws | BGG | ⚠ Partially useful but misses StBOG |

### What was needed (from gold citations)
The gold set contains:
- **12× 1B_ decisions** (pre-trial detention = 1B_ Abteilung, NOT 6B_!)
- **5× 7B_ decisions** (newer prefix for criminal procedural matters)
- **7× BGE IV / BGE I** (Leitentscheide)
- **19× StPO articles** (Art. 135, 140, 212, 221, 222, 227, 382, 385, 390, 393, 396, 422, 428)
- **2× StBOG articles** (Art. 37, 39)
- **1× StGB article** (Art. 140)
- **1× BGG article** (Art. 100)

### BUG 1: Wrong court prefix (6B_ instead of 1B_/7B_)
**This is the #1 killer.** The planner chose `6B_` (Strafrechtliche Abteilung — substantive criminal law: sentencing, conviction appeals) instead of:
- `1B_` — Öffentlich-rechtliche Abteilung **Haftbeschwerden** (pre-trial detention appeals)
- `7B_` — Newer designation for same matters

The planner's own system prompt CORRECTLY states:
> "Fragen zu Strafrecht/Strafprozess → BGE IV + 6B_ + **1B_ (Haft)**"

But the model ignored this guidance. **Untersuchungshaft is ALWAYS 1B_, never 6B_.**

### BUG 2: Only 3 directions (minimum is 3, but this question needs 5-6)
Missing directions that should have been generated:
- `corpus: courts, filter: [1B_, 7B_]` — Haftbeschwerden decisions
- `corpus: courts, filter: [BGE_IV, BGE_I]` — Leading cases on detention
- `corpus: laws, filter: [StBOG]` — Organization of criminal authorities

### BUG 3: No BGE direction at all
The gold contains **11 BGE citations** (BGE 132 I 21, BGE 133 I 168, BGE 133 I 270, BGE 137 IV 122, BGE 139 IV 270, BGE 143 IV 168). The planner generated ZERO directions searching BGE_IV or BGE_I.

### BUG 4: Direction 3 is wasteful
Searching BGG (Bundesgerichtsgesetz) with queries like "Kollusionsgefahr Haftverlängerung" returns irrelevant procedural boilerplate (Art. 47 on deadlines, Art. 123 on revision). BGG articles don't discuss detention conditions — they're about Federal Court procedure.

### Why the planner failed
The system prompt has an example showing `1B_` for Haft, but the model chose `6B_` anyway. Reasons:
1. The taxonomy section lists `6B_` under "STRAFRECHTLICHE ABTEILUNG" but doesn't have a separate heading for "HAFTBESCHWERDEN = 1B_"
2. The classification rules say "BGE IV + 6B_ + 1B_ (Haft)" — the "(Haft)" annotation is too subtle for a 7B model
3. The model lacks internal knowledge that `Untersuchungshaft` = `1B_` not `6B_`

---

## 3. EXECUTOR — QUERY REPETITION, NO DIVERSITY

### Direction 1 (StPO laws) — Stale iterations
| Iter | Query | New results? |
|------|-------|-------------|
| 0 (seed) | "Untersuchungshaft Kollusionsgefahr Haftverlängerung Verhältnismässigkeit" | 10 hits ✓ |
| 1 | "Kollusionsgefahr Haftverlängerung Untersuchungshaft Verhältnismässigkeit **Strafprozessrecht**" | Same top-4 ❌ |
| 2 | "**Risiko von Kollusion** Haftverlängerung Untersuchungshaft Verhältnismäßigkeit Strafprozessrecht" | Same top-4 ❌ |
| 3 | TIMEOUT | — |

**Problem:** All 3 queries are semantically identical (just word reordering + synonyms). The executor doesn't explore different ASPECTS (e.g., "Haftentlassungsgesuch Voraussetzungen", "Beschwerdelegitimation Haftentscheid", "amtliche Verteidigung Haftverfahren").

**Result:** 30 raw citations → only **13 unique** (57% duplication)

### Direction 2 (6B_ courts) — Completely wrong corpus
All results are about **Strafzumessung** (sentencing), NOT Haft:
- "Strafzumessung nach Art. 47 ff. StGB"
- "Grundsätze der Strafzumessung"
- "bedingte Entlassung"
- "Probezeit"

**Not a single result is about detention.** This is because `6B_` cases are about substantive criminal law, not procedural detention.

### Direction 3 (BGG laws) — Off-topic results
Searching BGG with detention keywords returns unrelated articles:
- Art. 47 (Fristen — deadline rules)
- Art. 123 (Revision)
- Art. 130 (transitional provisions)
- Art. 68 (Parteientschädigung)

The executor even **fell back to English** in Iter 3: "Swiss law pre-trial detention collusion proportionality legal concepts" — violating the German-only query rule and producing garbage results.

---

## 4. EMBEDDING/RETRIEVAL — SEMANTIC SIMILARITY TOO LOW

### Score analysis
All retrieval scores are **extremely low**:
- Best hit in Direction 1: **0.032** (Art. 226 Abs. 4 StPO)
- Best hit in Direction 2: **0.016** (6B_ cases)
- Best hit in Direction 3: **0.030** (BGG articles)

For comparison, a healthy dense retrieval system should produce scores **>0.5** for relevant documents.

### Possible causes
1. **Embedding model mismatch:** Qwen3-Embedding-0.6B may not understand legal German well
2. **Query prompt template:** The `prompt_query_law` prefix ("Instruct: Given German legal search terms...") may be confusing the embedding model
3. **Document encoding quality:** If documents were encoded with a different prefix than queries, asymmetric similarity results
4. **Dimensionality:** 1024-dim with FAISS IndexFlatIP (inner product) — are embeddings normalized? If not, IP ≠ cosine similarity

### Critical missing article: Art. 221 StPO
The MOST important article for this question (Art. 221 — defining detention grounds: Fluchtgefahr, Kollusionsgefahr, Wiederholungsgefahr) was **never retrieved** in any of 30 search iterations across Direction 1. Yet Art. 226, 227, 229 (all nearby procedural articles) were found. This suggests:
- Art. 221 may not be semantically close to the query in embedding space
- OR it might have been retrieved but with a different Absatz number (the gold wants "Art. 221 Abs. 1 StPO" and "Art. 221 Abs. 2 StPO")

---

## 5. AGGREGATION LOGIC — FALLBACK MASKS FAILURES

### Flow when reranker fails
```
Reranker scores all < 0.2 cutoff
  → 0 citations pass
    → Fallback: take top-10 by score
      → Since all scores are ~0.0097, this is just list-order (defaults first)
```

### Defaults injection — partially misguided
The pipeline injects 9 "always-cited" defaults for `criminal` case type:
```
Art. 42 Abs. 2 BGG    — ⚠ not in gold
Art. 95 BGG           — ⚠ not in gold
Art. 100 Abs. 1 BGG   — ✓ IN GOLD (but still dropped by reranker!)
Art. 105 Abs. 1 BGG   — ⚠ not in gold
Art. 29 Abs. 2 BV     — ⚠ not in gold
Art. 78 Abs. 1 BGG    — ⚠ not in gold
Art. 80 Abs. 1 BGG    — ⚠ not in gold
Art. 81 Abs. 1 BGG    — ⚠ not in gold (but it IS in gold for this query!)
Art. 50 StGB          — ⚠ not in gold
```

Wait — looking more carefully at the gold: `Art. 382 Abs. 1 StPO` is in gold (Beschwerdelegitimation). The defaults inject generic BGG legitimation articles instead of the StPO-specific ones. And `Art. 100 Abs. 1 BGG` IS in gold but was dropped because the reranker scored it 0.0097 (below 0.2).

---

## 6. CITATION FORMAT MISMATCHES

### Art. 221 extracted from question text
The pipeline extracts "Art. 221 Abs. 1 lit. b StPO" from the question but the gold expects "Art. 221 Abs. 1 StPO" (without lit. b). If the matching logic requires exact string match, this explicit extraction might produce a false positive or miss.

### Art. 222 StPO — was found but not in final output
Looking at Direction 1 results: `Art. 222 StPO (score=0.015)` appeared in Iter 0 results. But in the final 13 unique citations for Direction 1, it IS listed. So it was a candidate for reranking — but scored 0.0096 and was dropped.

---

## 7. TIMING & EFFICIENCY

| Phase | Time | Notes |
|-------|------|-------|
| Planner LLM | 64.93s | Very slow for 7B Q4 — is GPU offloading working? |
| Direction 1 (3 iters) | 15.2s | OK |
| Direction 2 (3 iters) | 18.1s | Wasted on wrong corpus |
| Direction 3 (4 iters) | 17.4s | Mostly irrelevant |
| Reranker | 0.78s | Fast but useless (broken scoring) |
| **Total** | **116.5s** | Too slow for 10 queries at competition time |

---

## 8. COMPLETE BUG INVENTORY

| # | Severity | Component | Bug | Impact |
|---|----------|-----------|-----|--------|
| 1 | **P0** | Reranker | All scores ~0.0097, uniform, nothing above 0.2 cutoff | Reranker is a no-op; random top-10 selected |
| 2 | **P0** | Planner | Uses `6B_` for detention cases instead of `1B_`/`7B_` | Entire Direction 2 (22 unique citations) is WRONG corpus |
| 3 | **P0** | Planner | No BGE direction (BGE_IV, BGE_I) | Misses 11 gold BGE citations |
| 4 | **P0** | Planner | Missing `7B_` prefix entirely | Misses 5 gold citations (7B_496, 7B_231, 7B_69, 7B_301, 7B_12) |
| 5 | **P1** | Executor | Repeats semantically-identical queries | 57% duplication, no new results after iter 0 |
| 6 | **P1** | Executor | Falls back to English queries (Dir 3, Iter 3) | Returns garbage from German corpus |
| 7 | **P1** | Planner | Missing StBOG in filter_codes | Misses Art. 37/39 StBOG (2 gold citations) |
| 8 | **P1** | Planner | Missing StGB in filter_codes (only has it in BGG direction) | Misses Art. 140 Abs. 1 StGB |
| 9 | **P2** | Retrieval | Art. 221 StPO never retrieved despite being THE key article | Embedding similarity too low for direct detention article |
| 10 | **P2** | Retrieval | All scores very low (0.01–0.03) | Suggests embedding quality/alignment issue |
| 11 | **P2** | Defaults | Injects wrong defaults (BGG procedural vs StPO procedural) | Takes slots from potentially correct citations |
| 12 | **P2** | Aggregation | Top-10 fallback when reranker fails gives random results | No principled selection when reranker is broken |
| 13 | **P3** | Executor | Timeout at exactly 3 iterations limits exploration | With better query diversity, more iters would help |
| 14 | **P3** | Format | "Art. 221 Abs. 1 lit. b StPO" extracted vs gold "Art. 221 Abs. 1 StPO" | Potential matching failure |

---

## 9. WHAT THE PIPELINE SHOULD HAVE PRODUCED

### Ideal plan for this question
```json
{
  "directions": [
    {"priority": 1, "corpus": "laws", "filter_codes": ["StPO"], "reasoning": "Haftrecht Art. 212-240"},
    {"priority": 2, "corpus": "courts", "filter_codes": ["1B_", "7B_"], "reasoning": "Haftbeschwerden"},
    {"priority": 3, "corpus": "courts", "filter_codes": ["BGE_IV", "BGE_I"], "reasoning": "BGE zu Haft"},
    {"priority": 4, "corpus": "laws", "filter_codes": ["StPO", "BGG", "StBOG"], "reasoning": "Verfahren+Zuständigkeit"},
    {"priority": 5, "corpus": "laws", "filter_codes": ["StGB"], "reasoning": "Materielle Straftatbestände"},
    {"priority": 6, "corpus": "courts", "filter_codes": ["6B_"], "reasoning": "Strafrecht materiell (Raub/Diebstahl)"}
  ]
}
```

### Ideal executor queries for Direction 2 (1B_/7B_)
- "Kollusionsgefahr konkret Haftgrund Verdunkelung Beeinflussung Zeugen"
- "Haftverlängerung Verhältnismässigkeit Dauer Untersuchungshaft Haftentlassung"
- "Haftprüfung Zwangsmassnahmengericht Verlängerung Antrag Staatsanwaltschaft"
- "amtliche Verteidigung Kosten Haftbeschwerde Entschädigung"

---

## 10. RECOMMENDED FIXES (Priority Order)

### P0-A: Fix reranker (MUST before anything else)
1. **Verify token IDs:** Re-run the reranker cell. Check printed output `[Qwen3Reranker] yes_id=X, no_id=Y`
2. **Test with known pair:** Run `reranker.predict([("Untersuchungshaft Haftgrund", "Art. 221 StPO text...")])` — if still ~0.5, the model is broken
3. **Alternative approach:** Instead of P(yes)/P(no) logits, use the model's hidden state similarity or switch to a cross-encoder reranker (e.g., `BAAI/bge-reranker-v2-m3`)
4. **Nuclear option:** If Qwen3-Reranker can't be fixed, **remove reranker entirely** and use RRF scores directly — even RRF-only would outperform a broken reranker

### P0-B: Fix planner court prefix routing
1. **Hardcode routing rule:** If question mentions "Haft/Untersuchungshaft/detention" → ALWAYS include `1B_` and `7B_` in directions
2. **Strengthen taxonomy:** Add explicit entry: "1B_ = Haftbeschwerden, Zwangsmassnahmen" prominently in system prompt
3. **Add post-processing:** After planner outputs, validate filter_codes against the question keywords. If "Haft" detected but no `1B_/7B_`, auto-inject a direction

### P0-C: Add BGE direction
1. **Force BGE:** Every plan should have at least one BGE direction (BGE_IV for criminal, BGE_I for public law, BGE_III for civil)
2. **System prompt rule:** Add "IMMER mindestens eine BGE-Richtung einschliessen"

### P1-A: Fix executor query diversity
1. **Diversity prompt:** Tell executor "Deine neue Query MUSS ein ANDERES Konzept abdecken als vorherige Queries"
2. **Dedup check:** If new query produces >80% overlap with prior results, force different approach
3. **Aspect decomposition:** Seed multiple sub-concepts: [detention grounds, proportionality, procedural standing, costs, defense counsel]

### P1-B: Fix executor English fallback
1. **Hard constraint:** Add to executor prompt: "NIEMALS englische Wörter in der Query verwenden"
2. **Post-processing:** Strip any English words before embedding

### P2-A: Improve retrieval for key articles
1. **BM25 weight:** Increase BM25 component in RRF fusion — BM25 should find "Art. 221" by keyword even if embedding fails
2. **Explicit article lookup:** If question mentions "Art. 221", directly add it to candidates (already partially done for explicit citations)

### P2-B: Better defaults injection
1. **StPO defaults for Haft cases:** Art. 221, 222, 382, 393, 396 StPO
2. **Case-type-specific:** Don't use generic criminal defaults (Art. 50 StGB) for procedural detention cases

---

## 11. SCORE CEILING ANALYSIS

Even if ALL bugs were fixed, what's the theoretical maximum?

| Component | Current contribution | Fixed contribution |
|-----------|---------------------|-------------------|
| Direction 1 (StPO) | 2/42 found | ~12/42 (Art. 212, 221, 222, 227, 135, 382, 385, 390, 393, 396, 422, 428) |
| Direction 2 (1B_/7B_) | 0/42 | ~12/42 (all 1B_ and 7B_ decisions) |
| Direction 3 (BGE) | 0/42 | ~8/42 (BGE 132, 133, 137, 139, 143) |
| Direction 4 (BGG/StBOG) | 0/42 | ~5/42 (BGG 100, StBOG 37, 39) |
| Defaults | 0/42 | ~3/42 (standard defaults that happen to be in gold) |
| StGB direction | 0/42 | ~2/42 (Art. 140) |
| **Total theoretical** | **2/42** | **~35-38/42** |

**With fixes, F1 could go from 0.077 → ~0.65-0.75.**

---

## 12. TOKEN/TIMING BUDGET CHECK

| Metric | Value | Budget | Status |
|--------|-------|--------|--------|
| System prompt tokens | ~4,466 | 16,384 ctx | ✓ OK |
| User message tokens | ~2,148 | — | ✓ OK |
| Total planner input | ~6,619 | 16,384 | ✓ OK (40% of ctx) |
| Planner output tokens | ~1,200 (est.) | 1,500 max | ✓ OK (not truncated) |
| Executor prompt tokens | ~1,500-1,750 | 16,384 | ✓ OK |
| Executor output tokens | ~80-120 | 400 max | ✓ OK (not truncated) |

**Token limits are no longer a bottleneck** — the planner JSON was parsed successfully.

---

## 13. SUMMARY OF ROOT CAUSES

```
F1 = 0.077
├── Reranker broken (scores uniform) → No filtering, random top-10
├── Wrong court prefix (6B_ not 1B_/7B_) → 0 relevant court decisions found
├── No BGE direction → 0 of 11 BGE citations found
├── Executor repeats queries → Only 13 unique from 30 raw (Dir 1)
├── Executor wrong corpus (Dir 2) → 22 results all about Strafzumessung
├── Key articles not retrieved (Art. 221) → Core citation missing
└── Defaults poorly targeted → Slots wasted on wrong articles
```

**The three fixes that would have the biggest impact:**
1. Fix reranker → proper filtering would promote good candidates
2. Use 1B_/7B_ instead of 6B_ → access correct court decisions
3. Add BGE_IV/BGE_I direction → access leading cases
