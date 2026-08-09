# 03_hyde_retrieval — Ablation Test Results

**Notebook:** `03_hyde_retrieval.ipynb`  
**Date:** 2026-08-04  
**Platform:** Kaggle T4 GPU  
**Dataset:** val.csv (10 queries)

---

## Ablation Results

| Test | HyDE | Few-Shot | Type Boost | Val Macro F1 | Public LB | Private LB |
|------|------|----------|------------|-------------|-----------|------------|
| **1** | OFF | OFF | OFF | **0.0017** | TBD | TBD |
| **2** | ON | OFF | OFF | TBD | TBD | TBD |
| **3** | ON | ON | OFF | TBD | TBD | TBD |
| **4** | ON | ON | ON | TBD | TBD | TBD |
| **5** | OFF | OFF | ON | TBD | TBD | TBD |

---

## Test 1: All Features OFF (Baseline)

**Config:** `hyde_enabled=False, few_shot_enabled=False, type_boost_enabled=False`

```
Macro F1 (PRIMARY): 0.0017
Macro Precision:    0.0010
Macro Recall:       0.0091

Micro F1:           0.0012
Micro Precision:    0.0007
Micro Recall:       0.0040
```

**Note:** This is LOWER than notebook 02's val F1 (0.0152). The HyDE tool wrapper, even when bypassed (`hyde_enabled=False`), passes the raw English query to `hierarchical_bm25_search()` which uses the same naive tokenizer. The difference from nb02 may be due to:
- Different output formatting (CCH `[TYPE]` labels in results)
- Agent prompt includes type registry injection (longer prompt = different behavior)
- The `hierarchical_bm25_search` function vs raw `index.search()` may handle edge cases differently

---

## Comparison Across All Notebooks

| Notebook | Architecture | Val Macro F1 | Public LB | Private LB |
|----------|-------------|-------------|-----------|------------|
| 01 (Direct Gen) | LLM from memory | 0.0200 | 0.02435 | 0.02842 |
| 02 (Agentic BM25) | ReAct + BM25 tools | 0.0152 | 0.00439 | 0.00731 |
| **03 Test 1** (All OFF) | HyDE wrapper + BM25 | **0.0017** | — | — |
| 03 Test 2 (HyDE only) | HyDE + BM25 | TBD | — | — |
| 03 Test 3 (HyDE+FS) | HyDE + Few-Shot + BM25 | TBD | — | — |
| 03 Test 4 (All ON) | HyDE + Few-Shot + Type Boost | TBD | — | — |
