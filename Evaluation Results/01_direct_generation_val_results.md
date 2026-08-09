# 01_direct_generation_baseline — Validation Results

**Notebook:** `01_direct_generation_baseline.ipynb`  
**Architecture:** Direct LLM generation (no retrieval, no corpus access)  
**Model:** Mistral-7B-Instruct-v0.2 Q4_K_M  
**Date:** 2026-07-29  
**Dataset:** val.csv (10 queries)

---

## Macro Scores (Competition Metric)

| Metric | Val (10 queries) | Public LB (20 test) | Private LB (20 test) |
|--------|-----------------|---------------------|----------------------|
| **Macro F1** | **0.0200** | **0.02435** | **0.02842** |

---

## Per-Query Breakdown

| Query ID | Query (truncated) | Predicted | Gold | TP | FP | FN | P | R | F1 |
|----------|-------------------|-----------|------|----|----|-----|-------|--------|-------|
| val_001 | Pre-trial detention extension (StPO) | 0 | 42 | 0 | 0 | 42 | 0.000 | 0.000 | 0.000 |
| val_002 | Disability/vocational rehab (IVG) | 0 | 36 | 0 | 0 | 36 | 0.000 | 0.000 | 0.000 |
| val_003 | Pre-trial detention Rivera (StPO) | 0 | 47 | 0 | 0 | 47 | 0.000 | 0.000 | 0.000 |
| val_004 | Holographic will validity (ZGB) | 4 | 10 | 0 | 4 | 10 | 0.000 | 0.000 | 0.000 |
| val_005 | Parental contact rights | 0 | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| val_006 | Gratuitous help / installer liability | 2 | 18 | 2 | 0 | 16 | 1.000 | 0.111 | **0.200** |
| val_007 | Heirship / vintage chronometer | 11 | 19 | 0 | 11 | 19 | 0.000 | 0.000 | 0.000 |
| val_008 | Town council member conflict | 0 | 29 | 0 | 0 | 29 | 0.000 | 0.000 | 0.000 |
| val_009 | Child maintenance calculation | 0 | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 0.000 |
| val_010 | Belize investment vehicle | 6 | 25 | 0 | 6 | 25 | 0.000 | 0.000 | 0.000 |

---

## Totals

| Metric | Count |
|--------|-------|
| Total True Positives | 2 |
| Total False Positives | 21 |
| Total False Negatives | 249 |
| Total Gold Citations | 251 |

---

## True Positives Found

| Citation | Query |
|----------|-------|
| Art. 248 Abs. 1 OR | val_006 (gratuitous help) |
| Art. 364 Abs. 1 OR | val_006 (gratuitous help) |

---

## False Positives Generated (Hallucinated)

| Citation | Query | Issue |
|----------|-------|-------|
| Art. 472 ZGB | val_004 | Wrong article (gold wants Art. 467, 469, 471, 505) |
| BGE 133 III 181 E. 2 | val_004 | Hallucinated — not in gold |
| BGE 138 III 178 E. 2 | val_004 | Hallucinated — not in gold |
| BGE 141 II 345 E. 3.1 | val_004 | Hallucinated — not in gold |
| Art. 11 ZPO | val_010 | Wrong law code |
| Art. 12 STGB | val_010 | Wrong case ("STGB" vs "StGB" — case mismatch) |
| Art. 13 STGB | val_010 | Wrong case |
| BGE 123 IV 345 E. 3 | val_010 | Hallucinated |
| BGE 131 II 112 E. 1 | val_010 | Hallucinated |
| BGE 138 II 586 E. 2 | val_010 | Hallucinated |
| + 11 more from val_007 | val_007 | All hallucinated |

---

## Analysis

**Why F1 = 0.02:**
- 8/10 queries produced **zero** predictions (LLM couldn't generate Swiss-specific citations)
- Only 2 true positives found across all 10 queries (both from val_006 — contract law, which Mistral knows best)
- 21 false positives — all hallucinated citations that don't match gold strings
- 249 false negatives — the LLM simply doesn't know these specific articles/cases

**Key Insight:** Direct generation from LLM memory is essentially useless for Swiss legal citation retrieval. The model:
1. Doesn't know specific Swiss article numbers at paragraph granularity (Abs. level)
2. Hallucinates BGE case numbers that don't exist
3. Can't produce the exact citation format matching the corpus
4. Has no access to the actual legal documents

**This is the baseline to beat with retrieval-augmented approaches.**
