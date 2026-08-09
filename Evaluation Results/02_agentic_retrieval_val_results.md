# 02_agentic_retrieval_baseline — Validation Results

**Notebook:** `02_agentic_retrieval_baseline.ipynb`  
**Architecture:** ReAct Agent + BM25 keyword search (laws + courts)  
**Model:** Mistral-7B-Instruct-v0.2 Q4_K_M  
**Search:** BM25Okapi (100K courts, 175K laws)  
**Date:** 2026-07-29  
**Dataset:** val.csv (10 queries)

---

## Macro Scores (Competition Metric)

| Metric | Val (10 queries) | Public LB (20 test) | Private LB (20 test) |
|--------|-----------------|---------------------|----------------------|
| **Macro F1** | **0.0152** | **0.00439** | **0.00731** |
| Macro Precision | 0.0091 | — | — |
| Macro Recall | 0.0571 | — | — |

| Metric | Value |
|--------|-------|
| Micro F1 | 0.0138 |
| Micro Precision | 0.0083 |
| Micro Recall | 0.0398 |

---

## Per-Query Breakdown

| Query ID | Topic | TP | FP | FN | Gold | F1 |
|----------|-------|----|----|-----|------|------|
| val_001 | Pre-trial detention (StPO) | 2 | 118 | 40 | 42 | ~0.025 |
| val_002 | Disability/vocational rehab (IVG) | 0 | 122 | 36 | 36 | 0.000 |
| val_003 | Pre-trial detention Rivera | 2 | 149 | 45 | 47 | ~0.020 |
| val_004 | Holographic will (ZGB) | 1 | 165 | 9 | 10 | ~0.011 |
| val_005 | Parental contact rights | 3 | 77 | 8 | 11 | ~0.063 |
| val_006 | Gratuitous help / liability | 1 | 108 | 17 | 18 | ~0.017 |
| val_007 | Heirship / chronometer | 1 | 118 | 18 | 19 | ~0.014 |
| val_008 | Town council conflict | 0 | 99 | 29 | 29 | 0.000 |
| val_009 | Child maintenance | 0 | 142 | 14 | 14 | 0.000 |
| val_010 | Belize investment vehicle | 0 | 93 | 25 | 25 | 0.000 |

---

## Totals

| Metric | Count |
|--------|-------|
| Total True Positives | 10 |
| Total False Positives | 1191 |
| Total False Negatives | 241 |
| Total Gold Citations | 251 |
| Avg predictions/query | ~119 |

---

## True Positives Found (10 total)

| Citation | Query |
|----------|-------|
| BGE 137 IV 122 E. 4.2 | val_001 (detention) |
| Art. 39 Abs. 1 StBOG | val_001 (detention) |
| BGE 143 IV 330 E. 2.1 | val_003 (detention Rivera) |
| BGE 143 IV 316 E. 3.2 | val_003 (detention Rivera) |
| BGE 131 III 601 E. 3.1 | val_004 (will) |
| BGE 130 III 585 E. 2.1 | val_005 (parental contact) |
| BGE 130 III 585 E. 2.2.1 | val_005 (parental contact) |
| BGE 131 III 209 E. 5 | val_005 (parental contact) |
| BGE 137 III 539 E. 5.2 | val_006 (gratuitous help) |
| Art. 245 Abs. 2 OR | val_007 (heirship) |

---

## Comparison vs Notebook 01

| Metric | 01 (Direct Gen) | 02 (Agentic BM25) | Change |
|--------|-----------------|-------------------|--------|
| **Macro F1** | 0.0200 | **0.0152** | -24% ❌ |
| Total TP | 2 | **10** | +5× ✅ |
| Total FP | 21 | **1191** | +57× ❌ |
| Avg predictions/query | ~2.3 | ~119 | +52× |
| Precision | 0.1000 | 0.0091 | -91% |
| Recall | 0.0111 | **0.0571** | +5× ✅ |

---

## Analysis

**Why F1 is LOWER than notebook 01 despite finding 5× more TPs:**

The agent finds 10 correct citations (vs 2 in nb01) — recall improved 5×. But it also outputs **~119 predictions per query** (vs ~2.3 in nb01). This tanks precision from 10% to 0.9%.

**F1 penalizes low precision heavily:**
```
Query val_001: 2 TP but 118 FP → P=0.017, R=0.048 → F1=0.025
  If it only predicted those 2 correct ones: P=1.000, R=0.048 → F1=0.091 (4× better)
```

**Root cause:** The agent returns ALL BM25 results (top_k=40 per tool call × 3 iterations × 2 tools = ~240 raw results). No filtering, no reranking, no score threshold.

**Key Observations:**
1. BM25 CAN find some correct citations (10 TP proves retrieval works for some queries)
2. But without filtering, the signal is buried in ~119 noise results per query
3. The agent searches in German (good) but BM25 has the compound word problem
4. Court citations (7B_, 1B_ docket-style) are almost never found — BM25 can't match them
5. BGE leading cases are found when query keywords overlap with the German text

**What this tells us for next notebooks:**
- Need score thresholding or reranking to filter the 240 raw results down to 20-30
- BM25 alone retrieves ~4% of gold (10/251) — need semantic search for the rest
- The agent architecture works (finds citations) but output volume must be controlled
