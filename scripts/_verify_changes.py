"""Verify all changes applied correctly."""
import json

with open('notebooks/03_hyde_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)

# Check Cell 6 (CONFIG)
cell6 = ''.join(nb['cells'][5]['source'])
print('=== CONFIG checks ===')
print('  Qwen3-Reranker-0.6B:', 'Qwen/Qwen3-Reranker-0.6B' in cell6)
print('  final_rerank_top_n 50:', 'final_rerank_top_n": 50' in cell6)
print('  rerank_per_search False:', 'rerank_per_search' in cell6)
print('  OLD BGE gone:', 'BAAI/bge-reranker' not in cell6)

# Check Cell 11 (FAISS/reranker loading)
cell11 = ''.join(nb['cells'][10]['source'])
print('\n=== Reranker loading checks ===')
print('  Qwen3Reranker class:', 'class Qwen3Reranker' in cell11)
print('  AutoModelForCausalLM:', 'AutoModelForCausalLM' in cell11)
print('  OLD CrossEncoder gone:', 'CrossEncoder' not in cell11)
print('  RERANKER_TASK_INSTRUCTION:', 'RERANKER_TASK_INSTRUCTION' in cell11)

# Check Cell 13 (hybrid_search)
cell13 = ''.join(nb['cells'][12]['source'])
print('\n=== Hybrid search checks ===')
print('  Per-search rerank REMOVED:', 'Cross-encoder reranking on fused' not in cell13)
print('  DISABLED comment:', 'Per-search reranking DISABLED' in cell13)

# Check Cell 14 (run_agent)
cell14 = ''.join(nb['cells'][14]['source'])
print('\n=== Final rerank checks ===')
print('  SCORE_CUTOFF = 0.1:', 'SCORE_CUTOFF = 0.1' in cell14)
print('  OLD -1.0 gone:', 'SCORE_CUTOFF = -1.0' not in cell14)
print('  TEXT_TRUNCATE:', 'TEXT_TRUNCATE' in cell14)
print('  final_rerank_top_n 50:', 'final_rerank_top_n", 50' in cell14)

# Summary
all_good = all([
    'Qwen/Qwen3-Reranker-0.6B' in cell6,
    'rerank_per_search' in cell6,
    'class Qwen3Reranker' in cell11,
    'CrossEncoder' not in cell11,
    'Per-search reranking DISABLED' in cell13,
    'SCORE_CUTOFF = 0.1' in cell14,
    'SCORE_CUTOFF = -1.0' not in cell14,
])
print(f'\n{"ALL CHANGES VERIFIED" if all_good else "SOME CHANGES MISSING"}')
