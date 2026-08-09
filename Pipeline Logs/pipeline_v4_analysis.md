# Pipeline V4 Debug Log — Grounded Analysis

**Run:** 2026-05-31 14:14:04 | **Query count:** 1 | **Total time:** 122s  
**Result:** P=0.067 | R=0.095 | **F1=0.078** (catastrophically low)

---

## Executive Summary

The pipeline retrieved 60 citations but only **4 matched gold** (4/42 recall). The failure is systemic across all 3 phases: the planner under-generated directions, the executor repeated itself without diversifying, and the reranker's 0.2 cutoff killed all search results while keeping only procedural defaults that mostly weren't in gold.

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
| BGE (Leitentscheide) | BGE 132 I 21, 133 I 168/270, 137 IV 122, 139 IV 270, 143 IV 168 | 13 |
| 1B_ (Einzelfälle) | 1B_210/2023, 1B_536/2018, 1B_90/2021, 1B_15/2023, 1B_357/2022, 1B_28/2022 E. 4.1 | 6 |
| 7B_ (Bundesstrafgericht) | 7B_496/2025, 7B_231/2025, 7B_69/2024, 7B_301/2024, 7B_12/2025 | 5 |

**Key insight:** Gold expects broad coverage across 8 distinct legal sub-domains, not just "Haft + Kollusionsgefahr."

---

## Phase-by-Phase Failure Analysis

### PHASE 1: PLANNER — Only 3 Directions (should have been 6)

**What it produced:**
1. ✅ StPO (Haft) — correct, but only 1 seed query
2. ✅ 1B_ (Einzelfälle) — correct
3. ✅ BGE_IV (Leitentscheide) — partially correct (should also include BGE_I)

**What it MISSED (catastrophic gaps):**
| Missing Direction | Gold Citations Missed | Impact |
|---|---|---|
| Rechtsmittel (StPO Art. 382-397) | Art. 382/385/390/393/396 = **5 citations** | High |
| Kosten (StPO Art. 422-432) | Art. 422/428 = **3 citations** | High |
| Verteidigung (StPO Art. 135) | Art. 135 Abs. 3/4 = **2 citations** | Medium |
| StGB materiell | Art. 140 Abs. 1 (Raub) = **1 citation** | Medium |
| 7B_ Bundesstrafgericht | 7B_496/2025, 7B_231/2025 etc. = **5 citations** | High |
| StBOG | Art. 37/39 StBOG = **2 citations** | Medium |
| BGE_I (not just BGE_IV) | BGE 132 I 21, 133 I 168/270 = **5 citations** | High |

**Root cause:** The planner generated the MINIMUM (3) instead of the maximum (6) directions. The CHECKLIST in the prompt explicitly says:
> STRAFPROZESS (Haft): MUSS = StPO + 1B_ + BGE_IV + Rechtsmittel + amtliche Verteidigung

The model ignored this checklist — it only produced the first 3 items and stopped.

**Why?** Likely causes:
- The Beispiel 1 in the prompt shows 6 directions for "extension of pre-trial detention" — almost the SAME question. The WARNUNG says don't copy, but the model might have instead *under-produced* to avoid looking like a copy.
- `max_tokens_planner=1500` may be too tight for 6 directions with verbose sachverhalt (the sachverhalt alone was ~1000 chars).
- Temperature 0.1 makes the model conservative.

---

### PHASE 2: EXECUTORS — Repetitive Queries, No Diversification

#### Direction 1 (StPO laws): 4 iterations, 13 unique citations
**Problem:** All 4 iterations searched variations of the same concept:
- Iter 0: `"Untersuchungshaft Haftgrund Kollusionsgefahr Verhältnismässigkeit"`
- Iter 1: `"Kollusionsgefahr Untersuchungshaft Haftgrund Verhältnismässigkeit Art. 221 StPO"`
- Iter 2: `"Haftgrund Kollusionsgefahr Untersuchungshaft Verhältnismässigkeit Art. 221 StPO Prüfungshaftgrundlage"`
- Iter 3: `"Haftgrund Kollusionsgefahr Untersuchungshaft Prüfungshaftgrundlage Verhältnismässigkeit Art. 221 StPO"`

**Result:** Same 10 articles returned repeatedly (Art. 226, 229, 221, 220). The executor never pivoted to Rechtsmittel, Kosten, or Verteidigung articles.

**What it found:** Art. 221 Abs. 1 ✅, Art. 212 Abs. 3 ✅, Art. 221 Abs. 2 ✅  
**What it missed within StPO:** Art. 222, Art. 227 Abs. 1, Art. 382, Art. 385, Art. 390, Art. 393, Art. 396, Art. 422, Art. 428, Art. 135

**Root cause:** The executor prompt doesn't instruct diversification. The LLM "thought" field is just placeholder text (`"Deine Überlegung was du suchen willst und warum"`) — it's not actually reasoning about what's missing.

#### Direction 2 (1B_ courts): 4 iterations, 24 unique citations
**Problem:** Found many Kollusionsgefahr cases (1B_406/2016, 1B_218/2018, etc.) — but NONE of them are in the gold set.

**Why?** The gold 1B_ citations are from specific cases:
- 1B_210/2023 E. 4.1
- 1B_536/2018 E. 5.1
- 1B_90/2021 E. 2.1 / E. 2.4
- 1B_15/2023 E. 3.1
- 1B_357/2022 E. 3.1
- 1B_28/2022 E. **4.1** (not E. 4.4 which was found)

The pipeline found 1B_28/2022 E. 4.4 but gold wants E. 4.1 — **different Erwägung of the same case.** This suggests the retrieval found the right case but wrong section.

#### Direction 3 (BGE_IV): 3 iterations + timeout, 23 unique citations
**Problem:** Scores are extremely low (0.014-0.016) — barely above noise. The BGE_IV corpus seems poorly embedded for Haft queries.

**Critical miss:** Gold expects BGE 137 IV 122 (the KEY Haft Leitentscheid with E. 4.1/4.2/6.2/6.4). The search never found it despite searching "Haft Grundsatz Leitentscheid Kollusionsgefahr."

**Also missed:** Gold expects BGE from BGE_I (not BGE_IV!):
- BGE 132 I 21 E. 3.2 / 3.2.1 / 3.2.2 — persönliche Freiheit
- BGE 133 I 168 E. 4.1 — Haftdauer
- BGE 133 I 270 E. 3.4.2

**Root cause:** The planner searched ONLY BGE_IV, but Haft-Grundsätze also sit in BGE_I (public law / fundamental rights). The routing guide mentions this but the planner didn't follow it.

---

### PHASE 3: RERANKER — Broken Scoring + Aggressive Cutoff

**The core disaster:**
- 11 citations scored 0.3000 (all defaults + Art. 221 Abs. 1 StPO)
- All 59 other citations scored 0.014-0.032
- Cutoff at 0.2 → only the 11 "defaults" survive reranking

**This means the reranker didn't actually rerank.** The Qwen3-Reranker-0.6B produced scores that are either ~0.3 (for injected defaults) or ~0.02 (for everything else). The gap between 0.3 and 0.032 is enormous — suggests the reranker only gives high scores to very short, generic text and penalizes longer case excerpts.

**Then all 60 citations were output anyway** (max_final_citations=60), so the cutoff was cosmetic — the output included everything regardless. But the ORDERING was wrong: defaults at top, actual relevant cases buried at positions 12-60.

**Default injection analysis:**
| Injected Default | In Gold? | Verdict |
|---|---|---|
| Art. 42 Abs. 2 BGG | ❌ | FALSE POSITIVE |
| Art. 95 BGG | ❌ | FALSE POSITIVE |
| Art. 100 Abs. 1 BGG | ✅ | TRUE POSITIVE |
| Art. 105 Abs. 1 BGG | ❌ | FALSE POSITIVE |
| Art. 29 Abs. 2 BV | ❌ | FALSE POSITIVE |
| Art. 78 Abs. 1 BGG | ❌ | FALSE POSITIVE |
| Art. 80 Abs. 1 BGG | ❌ | FALSE POSITIVE |
| Art. 81 Abs. 1 BGG | ❌ | FALSE POSITIVE |
| Art. 10 Abs. 2 BV | ❌ | FALSE POSITIVE |
| Art. 31 Abs. 3 BV | ❌ | FALSE POSITIVE |

**10 defaults injected, only 1 correct = 10% hit rate.** The defaults are too broad and pump false positives.

---

## What We Got Right ✅

| Citation Found | How Found | Assessment |
|---|---|---|
| Art. 221 Abs. 1 StPO | Direction 1, all 4 iterations | Core haft article — correctly identified |
| Art. 221 Abs. 2 StPO | Direction 1, iteration 1 | Wiederholungsgefahr — relevant secondary ground |
| Art. 212 Abs. 3 StPO | Direction 1, iterations 0 & 2 | Proportionality of detention duration — key |
| Art. 100 Abs. 1 BGG | Default injection | 30-day deadline — standard procedural |

**Pattern:** Only the most direct/obvious articles were found. Everything requiring structural legal reasoning (Rechtsmittel cascade, Kosten, Verteidigung) was missed.

---

## What Went Wrong — Root Cause Tree

```
F1 = 0.078
├── LOW RECALL (4/42 = 9.5%)
│   ├── Planner: Only 3 directions (should be 6)
│   │   ├── Missing: Rechtsmittel direction → lost 5 gold citations
│   │   ├── Missing: Kosten/Entschädigung direction → lost 3 gold citations
│   │   ├── Missing: Verteidigung direction → lost 2 gold citations
│   │   ├── Missing: StGB direction → lost Art. 140 (Raub)
│   │   ├── Missing: 7B_ direction → lost 5 gold citations
│   │   └── Missing: BGE_I direction → lost 5 gold citations (persönliche Freiheit BGEs)
│   ├── Executor: Repetitive queries (no diversification)
│   │   ├── 4 iterations of near-identical "Kollusionsgefahr Haftgrund" queries
│   │   └── Never explored Rechtsmittel/Kosten even within StPO filter
│   └── Search quality: BGE_IV embedding quality poor for Haft
│       ├── BGE 137 IV 122 never surfaced (THE key Haft-BGE)
│       └── Scores 0.014-0.016 = near-random
│
└── LOW PRECISION (4/60 = 6.7%)
    ├── Default injection: 10 defaults added, only 1 correct (9 false positives)
    ├── Reranker non-functional: All defaults get 0.3, all real results get 0.02
    └── Many 1B_ cases found but WRONG Erwägung (e.g., E. 4.4 vs gold E. 4.1)
```

---

## Specific Recommendations (Priority Order)

### 1. FIX PLANNER: Force 6 directions for Strafprozess/Haft (CRITICAL)

The prompt CHECKLIST says "MUSS: StPO + 1B_ + BGE_IV + Rechtsmittel + amtliche Verteidigung" but the model only produced 3. Options:
- **A)** Increase `max_tokens_planner` from 1500 → 2500 (the verbose sachverhalt consumed most budget)
- **B)** Add to GBNF grammar: minimum 5 directions for criminal/haft topics
- **C)** Post-process: if plan has <5 directions AND question mentions "Haft/detention", inject missing required directions programmatically

### 2. FIX EXECUTOR: Prevent query repetition (CRITICAL)

The executor generated 4 near-identical queries. Fixes:
- **A)** Add "ALREADY SEARCHED" context showing previous queries (already partially done but not effective)
- **B)** Add explicit rule: "VERBOTEN: Wiederholung von >50% der Begriffe aus vorherigen Queries"
- **C)** Give the executor awareness of which StPO sub-domains to explore (Haft vs Rechtsmittel vs Kosten)

### 3. FIX RERANKER: Lower cutoff or fix scoring (HIGH)

The 0.2 cutoff killed everything. The reranker assigns ~0.3 to defaults and ~0.02 to real results — there's no meaningful discrimination.
- **A)** Lower `rerank_score_cutoff` to 0.01 or remove it entirely
- **B)** Don't score defaults through the reranker (they always get max score, distorting ranking)
- **C)** Consider removing the reranker and relying on RRF scores from retrieval

### 4. FIX DEFAULTS: Reduce false positive injection (MEDIUM)

10 defaults injected, 9 are wrong. The criminal defaults are too broad.
- **A)** Reduce criminal defaults to only: Art. 100 Abs. 1 BGG, Art. 78 Abs. 1 BGG (the 2 that actually appear most often)
- **B)** Make defaults conditional: only inject if NOT already found in search results
- **C)** Move defaults to a separate "always-include" pool that doesn't count against max_final_citations

### 5. ADD BGE_I SEARCH: Haft BGEs live in both BGE_I and BGE_IV (MEDIUM)

Gold has 5 BGE citations from BGE_I (public law, fundamental rights):
- BGE 132 I 21 (persönliche Freiheit bei Haft)
- BGE 133 I 168, BGE 133 I 270

The planner only searched BGE_IV. Fix: routing guide should emphasize that Haft-Grundrechte are in BGE_I.

### 6. ADD 7B_ DIRECTION: Gold has 5 citations from Bundesstrafgericht (MEDIUM)

7B_496/2025, 7B_231/2025, 7B_69/2024, 7B_301/2024, 7B_12/2025 — all recent Bundesstrafgericht decisions on Haft. The planner never generated a 7B_ direction. The DIVERSITÄTS-REGEL mentions "f) Bundesstrafgericht — bei organisierter Kriminalität" but doesn't say "also for Haft cases handled by BStGer."

---

## Precision Problem Deep-Dive

### Why did we find the WRONG 1B_ cases?

We found many "generic" Kollusionsgefahr cases (1B_406/2016, 1B_218/2018, etc.) but gold wants specific recent ones (1B_210/2023, 1B_90/2021). This suggests:

1. The gold citations are from the **actual decision being asked about** — they reference what THAT specific court cited
2. Our pipeline searches generically and finds "any case about Kollusionsgefahr" rather than cases CITED BY the particular decision
3. This is a fundamental retrieval problem: we need to find what a specific case WOULD cite, not just topically similar cases

### Why did defaults hurt precision?

The default injection assumes every criminal case cites Art. 42 BGG, Art. 95 BGG, Art. 105 BGG, Art. 81 BGG, etc. But this specific case apparently doesn't cite most of those. Defaults should be validated against training data hit rates.

---

## Score Reconciliation

| Metric | Value | Meaning |
|--------|-------|---------|
| Total predicted | 60 | Max allowed (max_final_citations=60) |
| True Positives | 4 | Art. 221/1, Art. 221/2, Art. 212/3, Art. 100/1 BGG |
| False Positives | 56 | 9 wrong defaults + 24 wrong 1B_ + 12 wrong StPO articles + 11 wrong BGE |
| False Negatives | 38 | 5 Rechtsmittel + 3 Kosten + 2 Verteidigung + 5 7B_ + 5 BGE_I + 6 1B_ + ... |
| Precision | 4/60 = 0.067 | Most predictions wrong |
| Recall | 4/42 = 0.095 | Barely found anything |

---

## What This Tells Us About the Gold Standard

The gold citations follow a **"full case anatomy" pattern:**
1. **Substantive law** (Art. 140 StGB = the crime)
2. **Haft articles** (Art. 221, 222, 227, 212 = detention procedural basis)
3. **Rechtsmittel cascade** (Art. 382, 385, 390, 393, 396 = appeals chain)
4. **Costs** (Art. 422, 428 = cost allocation)
5. **Defense rights** (Art. 135 = appointed counsel)
6. **Organization** (Art. 37/39 StBOG = court organization)
7. **BGG procedural** (Art. 100 = deadline)
8. **Leading cases** (BGE 137 IV 122, BGE 132 I 21 = foundational precedent)
9. **Recent cases** (7B_ 2024/2025 = current BStGer practice)
10. **Specific Erwägungen** (E. 4.1, not E. 4.4 = exact reasoning section)

Our pipeline only covered category 2 (partially) and 7 (one citation). **We missed 8 out of 10 categories.**

---

## Token Budget Note

- System prompt: 18,359 chars (~4,589 tokens)
- User message (context + question): 13,095 chars (~3,273 tokens)
- **Total input: 31,471 chars (~7,867 tokens)**
- Available for generation: 16,384 - 7,867 = **8,517 tokens** ← plenty

The overflow issue from earlier is FIXED. The system prompt includes both examples and the WARNUNG. No token overflow occurred.

---

## Conclusion

This is not a token or infrastructure problem — it's a **coverage problem**. The pipeline found the obvious (Art. 221 Haft) but missed the structural legal reasoning that a real Swiss attorney would know: every Haft case necessarily involves Rechtsmittel, Kosten, Verteidigung, and organizational law. The planner's CHECKLIST contains this knowledge but the model didn't follow it. Fix priority: force more directions → diversify executor queries → fix reranker scoring.
