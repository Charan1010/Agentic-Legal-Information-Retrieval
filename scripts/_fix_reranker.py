"""Fix the final reranking section in cell 14 of the notebook."""
import json

NB_PATH = 'notebooks/03_hyde_kaggle.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][14]
src_lines = cell['source']
src = ''.join(src_lines)

# Find the section to replace by looking for the key markers
marker_start = '    # ---- Final reranking using first HyDE doc'
marker_end = '        print(f"  [Final] {len(deduped_results)} unique citations (no final rerank needed)")'

# Find line indices
start_idx = None
end_idx = None
for i, line in enumerate(src_lines):
    if marker_start in line:
        start_idx = i
    if marker_end in line and start_idx is not None:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"ERROR: Could not find markers. start={start_idx}, end={end_idx}")
    print("Searching for SCORE_CUTOFF...")
    for i, line in enumerate(src_lines):
        if 'SCORE_CUTOFF' in line:
            print(f"  Line {i}: {repr(line)}")
    exit(1)

print(f"Found section at lines {start_idx}-{end_idx}")
print(f"  Start: {repr(src_lines[start_idx][:80])}")
print(f"  End: {repr(src_lines[end_idx][:80])}")

# New replacement lines
new_lines = [
    '    # ---- Final reranking with Qwen3-Reranker (generative yes/no) ----\n',
    '    # WHY only here (not per-search): The original query from val/test CSV is natural\n',
    '    # language (English). Rerankers work on (question, document) pairs.\n',
    '    # Agent keyword queries like "Untersuchungshaft StPO" are NOT questions.\n',
    '    final_top_n = CONFIG.get("final_rerank_top_n", 50)\n',
    '    if _reranker and CONFIG.get("rerank_enabled") and len(deduped_results) > 0:\n',
    '        rerank_query = query  # original natural-language query from CSV\n',
    '        pairs = [(rerank_query, r.get("text", "")[:TEXT_TRUNCATE]) for r in deduped_results]\n',
    '        final_scores = _reranker.predict(pairs, show_progress_bar=False)\n',
    '        for doc, fs in zip(deduped_results, final_scores):\n',
    '            doc["_final_rerank_score"] = float(fs)\n',
    '        deduped_results.sort(key=lambda d: d["_final_rerank_score"], reverse=True)\n',
    '        \n',
    '        # Score cutoff \u2014 Qwen3 outputs P(yes) in [0,1]. 0.1 = "10% confident relevant"\n',
    '        # WHY 0.1: Gold has 42 citations, need high recall. Only filter obvious garbage.\n',
    '        SCORE_CUTOFF = 0.1\n',
    '        before_cutoff = len(deduped_results)\n',
    '        deduped_results = [r for r in deduped_results if r.get("_final_rerank_score", 0) > SCORE_CUTOFF]\n',
    '        deduped_results = deduped_results[:final_top_n]\n',
    '        if verbose:\n',
    '            print(f"  [Final rerank] {len(seen)} unique -> cutoff dropped {before_cutoff - len(deduped_results)} -> kept {len(deduped_results)}")\n',
    '    elif verbose and len(deduped_results) > 0:\n',
    '        print(f"  [Final] {len(deduped_results)} unique citations (no final rerank needed)")\n',
]

# Replace
cell['source'] = src_lines[:start_idx] + new_lines + src_lines[end_idx+1:]

# Verify
new_src = ''.join(cell['source'])
assert 'SCORE_CUTOFF = 0.1' in new_src, "Replacement failed!"
assert 'SCORE_CUTOFF = -1.0' not in new_src, "Old cutoff still present!"
assert 'TEXT_TRUNCATE' in new_src, "TEXT_TRUNCATE not present!"

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("SUCCESS: Final reranking section replaced")
print(f"  - SCORE_CUTOFF: -1.0 -> 0.1")
print(f"  - final_rerank_top_n default: 25 -> 50")
print(f"  - Uses TEXT_TRUNCATE and Qwen3 P(yes) scoring")
