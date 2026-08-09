"""Remove per-search reranking from hybrid_search in cell 13."""
import json

NB_PATH = 'notebooks/03_hyde_kaggle.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][13]
lines = cell['source']

# Find the per-search reranking section (lines 90-103)
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if '# ---- Cross-encoder reranking on fused candidates ----' in line:
        start_idx = i
    if start_idx and 'return results' in line:
        end_idx = i
        break

if start_idx is None:
    print("ERROR: Could not find per-search reranking section")
    exit(1)

print(f"Removing per-search reranking: lines {start_idx}-{end_idx-1}")

# Replace with disabled comment + return
new_lines = [
    '\n',
    '    # ---- Per-search reranking DISABLED ----\n',
    '    # WHY: Reranker was ACTIVELY HARMFUL here — promoted wrong codes (JStPO, ZISG)\n',
    '    # over correct StPO articles. Agent keyword queries are not natural-language\n',
    '    # questions, so cross-encoders/rerankers scramble the good RRF order.\n',
    '    # Only rerank at the FINAL stage with the original query from val/test CSV.\n',
    '\n',
    '    return results\n',
]

cell['source'] = lines[:start_idx] + new_lines + lines[end_idx+1:]

# Verify - line 34 in docstring still mentions it (that's fine), but the code section is gone
new_src = ''.join(cell['source'])
assert '# ---- Cross-encoder reranking on fused candidates ----' not in new_src
assert 'Per-search reranking DISABLED' in new_src
assert 'return results' in new_src

# Also fix the docstring reference (line 34)
for i, line in enumerate(cell['source']):
    if '4. Cross-encoder reranking on fused top candidates' in line:
        cell['source'][i] = '    4. (DISABLED) Return RRF-ordered results directly\n'
        break

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("SUCCESS: Per-search reranking removed from hybrid_search")
