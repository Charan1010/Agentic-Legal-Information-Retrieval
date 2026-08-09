# Run 1 — Full Pipeline Analysis

## Executive Summary

| Metric | Value |
|--------|-------|
| **Macro F1 (val)** | **0.0062** |
| Test queries processed | 40/40 |
| Val queries processed | 10/10 |
| Avg citations per query | 188.5 |
| Queries with 0 citations | 0 |
| Total runtime | ~105 min (Cell 10: 24 min, Cell 14: 80 min, Cell 16: 25 min) |

**Verdict: Pipeline runs end-to-end but F1 is catastrophically low (< 1%). The system retrieves FAR too many citations and almost none are correct.**

---

## Step-by-Step Cell Outputs

### Cell 2 (pip installs) ✅
- rank-bm25, sentence-transformers, faiss-cpu, llama-cpp-python (cu124)
- Clean install, no errors

### Cell 3 (File listing) ✅
- Competition data: laws_de.csv (73MB), court_considerations.csv (2.4GB), train.csv, test.csv, val.csv
- Mistral 7B GGUF model detected

### Cell 4 (Cache check) ✅
- Cache dir existed from a previous run, pre-built indices available

### Cell 5 (Imports, paths, CONFIG) ✅
- Kaggle environment detected
- CONFIG: max_iterations=3, top_k=40, hyde_enabled=True

### Cell 6 (BM25 Index + Corpus Loading) ✅
- Laws index: 175,933 documents (loaded from cache)
- Courts index: 200,000 documents (random sample from 2.4GB corpus)

### Cell 7 (Load LLM) ✅
- Mistral 7B Q4_K_M loaded, all layers on GPU

### Cell 8 (Few-Shot Bank) ✅
- 656 law types, 58 court types
- 3,279 law examples, 276 court examples (total 3,555)
- All translated to English
- Cached to disk (few_shot_banks.pkl)
- Runtime: ~1 hour (synthetic generation + translation)

### Cell 9 (Type Registry) ✅
- doc_types arrays built
- LAW_TYPES_FOR_PROMPT and COURT_TYPES_FOR_PROMPT populated

### Cell 10 (FAISS Embeddings) ✅
- Sentence-transformer: paraphrase-multilingual-MiniLM-L12-v2, 384d, CUDA
- Few-shot FAISS: law=3,279 vectors, court=276 vectors
- Laws corpus: 175,933 vectors in 324.8s (542 docs/sec)
- Courts corpus: 200,000 vectors in 1,062.4s (188 docs/sec)
- Total embedding time: ~24 min

### Cell 11 (HyDE Functions) ✅
- HyDE cache: 0 entries (fresh start)
- Verbose mode for first 5 queries

### Cell 12 (Hybrid Search Tools) ✅
- Hybrid search (FAISS + BM25 + RRF) ready
- top_k: laws=40, courts=40

### Cell 13 (ReAct Agent) ✅
- System prompt: 5,137 chars
- Max 3 iterations per query

### Cell 14 (Test Predictions) ✅
- 40 queries processed in 79.6 min (~2 min/query)
- Avg citations/query: **188.5** ← THIS IS THE PROBLEM
- HyDE cache: 219 entries
- Checkpoint at query 25: avg 196.6 cits/query

### Cell 15 (Save Submission) ✅
- submission.csv saved to /kaggle/working/

### Cell 16 (Validation) ✅
- 10 val queries in 25.3 min
- **Macro F1: 0.0062**
- Per-query F1: [0.000, 0.003, 0.012, 0.000, 0.007, 0.010, 0.000, 0.009, 0.010, 0.011]
- 3 queries scored exactly 0.000

---

## What Went Well

1. **Pipeline stability**: All 16 cells ran without errors. No crashes, OOM, or kernel deaths.
2. **Caching works**: BM25 indices, FAISS embeddings, few-shot banks, HyDE cache all persist to disk.
3. **Checkpointing works**: Predictions saved every 25 queries, resumable.
4. **Full corpus indexed**: 175k laws + 200k court docs with both BM25 and FAISS.
5. **HyDE generation functional**: 219 cache entries created, generates German hypothetical docs.
6. **No empty predictions**: Every query got at least some citations returned.

---

## What Went Wrong (Root Causes)

### 🔴 CRITICAL: Way Too Many Citations Per Query (188.5 avg)

**Expected**: Competition likely expects 5-20 citations per query.  
**Actual**: 188.5 average, some queries returning 200+.

**Root cause**: The agent runs 3 iterations, each iteration calls `search_laws` AND `search_courts`, each returns `top_k=40` results. The agent collects ALL citations from ALL tool calls:
- 3 iterations × 2 tools × 40 results = **240 max citations per query**
- No deduplication between iterations (beyond exact citation match)
- No filtering/ranking of final citation set

**The tool returns the top 40 FAISS+BM25 results, but these are not all "relevant" — they're just the closest in embedding space. The agent dumps all of them as its answer.**

### 🔴 CRITICAL: Precision is Near Zero

With ~188 predicted citations vs. likely 5-15 gold citations per query:
- Precision ≈ correct_hits / 188 ≈ 0.5-1%
- Even if recall is decent (finding some correct ones), the massive over-prediction kills F1

### 🟡 MODERATE: BM25 and FAISS May Not Be Finding Correct Citations

- Per-query F1 shows some queries at exactly 0.000 — not a single correct citation in 188 predictions
- This suggests the retrieval quality itself is poor for some legal domains
- The 200k court sample (out of millions) may miss relevant documents entirely

### 🟡 MODERATE: Agent Always Uses All Iterations

- The agent doesn't have a "Final Answer" stopping condition that's triggered properly
- It mechanically uses all 3 iterations, accumulating more and more citations
- No confidence threshold to stop early

### 🟡 MODERATE: No Citation Filtering/Reranking

- After retrieval, there's no step to:
  - Filter by relevance score threshold
  - Rerank with a cross-encoder
  - Let the LLM select the most relevant from the candidate set
  - Limit output to top-N most confident

### 🟡 MODERATE: HyDE May Be Generating Off-Target Documents

- HyDE generates a hypothetical document in German, then uses it for BM25
- If the hypothetical document is generic/wrong, it pulls in irrelevant results
- No validation that the HyDE output is actually relevant to the query

---

## Clear Next Steps (Priority Order)

### 1. 🔴 Add Citation Count Limit (IMMEDIATE FIX)
- Cap predictions to top 15-25 citations max per query
- Use the RRF fusion scores to rank and cutoff
- This alone could 5-10x the F1 score

### 2. 🔴 Add Score Threshold Filtering
- Only return citations above a minimum RRF score (e.g., > 0.01)
- Currently every document in top_k is returned regardless of score
- Many of the 188 citations likely have near-zero relevance scores

### 3. 🔴 Reduce top_k from 40 to 10-15
- top_k_laws=40 and top_k_courts=40 is way too aggressive
- With 3 iterations × 2 tools × 40 = 240 potential citations
- Set top_k=10 or top_k=15 → max 60-90 candidates → then filter to 15-25

### 4. 🟡 Add LLM-based Citation Selection (Reranking)
- After collecting all candidates, have the LLM evaluate each citation's relevance
- "Given this query, is this citation relevant? Yes/No"
- Only include citations the LLM confirms as relevant

### 5. 🟡 Reduce Agent Iterations to 2
- 3 iterations with no smart stopping = too much retrieval noise
- Most queries can be answered in 1-2 tool calls per source type
- Or add a "sufficient" check: if first iteration finds high-confidence matches, stop

### 6. 🟡 Deduplicate Better
- Current dedup is exact string match only
- Same law article might appear as "Art. 1 OR" vs "Art. 1 Abs. 1 OR" — both kept
- Add citation normalization before dedup

### 7. 🟡 Evaluate Retrieval Quality Separately
- Before fixing the agent, check: do the correct citations even exist in the top-100 FAISS/BM25 results?
- If gold citations aren't in the candidate pool, no amount of filtering will help
- Run a "recall@100" check on val set

### 8. 🟢 Consider Courts Sample Size
- 200k out of potentially millions — gold court citations may not be in the sample
- If val queries need specific BGE decisions, they must be in the 200k sample
- Consider loading full court corpus (if memory allows) or smarter sampling

### 9. 🟢 HyDE Validation
- Check if HyDE is helping or hurting by running with hyde_enabled=False
- Compare F1 with/without HyDE on val set

---

## Quick Win Estimate

If we just add **citation count cap at 20** + **reduce top_k to 15**:
- Current: 188 predictions, ~1-2 correct → precision=0.5%, F1≈0.006
- With cap: 20 predictions, ~1-2 correct → precision=5-10%, F1≈0.02-0.05
- That's a 5-10x improvement from a 2-line config change

If we also add **score threshold filtering**:
- Could get to 10-15 high-quality predictions → F1 could reach 0.05-0.15

The real ceiling is determined by **whether the correct citations are even in the retrieval pool** — that needs a recall@N analysis.

---

## Files Generated

| File | Path | Size |
|------|------|------|
| submission.csv | /kaggle/working/submission.csv | ~40 rows |
| predictions_checkpoint.pkl | /kaggle/working/predictions_checkpoint.pkl | — |
| val_predictions_checkpoint.pkl | /kaggle/working/val_predictions_checkpoint.pkl | — |
| hyde_cache.pkl | /kaggle/working/cache/hyde_cache.pkl | 219 entries |
| faiss_laws_embeddings.pkl | /kaggle/working/cache/ | ~270 MB |
| faiss_courts_embeddings.pkl | /kaggle/working/cache/ | ~307 MB |
| few_shot_banks.pkl | /kaggle/working/cache/ | ~50 MB |
