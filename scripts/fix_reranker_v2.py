"""Fix reranker in notebook: disable model loading, lower default score, update config."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Fix 1: CONFIG cell (cell index 2) - change rerank_score_cutoff from 0.2 to 0.0
cell2 = nb['cells'][2]
for i, line in enumerate(cell2['source']):
    if '"rerank_score_cutoff": 0.2' in line:
        cell2['source'][i] = '    "rerank_score_cutoff": 0.0,  # DISABLED - reranker bypassed, using RRF scores directly\n'
        print(f'Fix 1: CONFIG rerank_score_cutoff 0.2 -> 0.0 (cell 2, line {i})')
        break
else:
    print('Fix 1: NOT FOUND')

# Fix 2: Reranker loading cell (cell index 8) - skip loading model
cell8 = nb['cells'][8]
for i, line in enumerate(cell8['source']):
    if 'print("Loading reranker' in line:
        # Replace from this line to end with skip logic
        cell8['source'] = cell8['source'][:i] + [
            '# RERANKER DISABLED - Qwen3-Reranker produces uniform scores (~0.01),\n',
            '# nothing passes any meaningful cutoff. Using RRF scores directly in aggregate_and_output.\n',
            '# Skipping model load saves ~1.2GB VRAM on GPU 1.\n',
            'reranker = None\n',
            'print("Reranker: DISABLED (using RRF scores directly - saves 1.2GB VRAM)")\n',
            'print(f"  GPU 1 memory: {torch.cuda.memory_allocated(1)/1e9:.2f} GB allocated")\n',
        ]
        print(f'Fix 2: Reranker loading skipped (cell 8, replaced from line {i})')
        break
else:
    print('Fix 2: NOT FOUND')

# Fix 3: aggregate_and_output cell (cell index 16) - change default score 0.3 -> 0.0
cell16 = nb['cells'][16]
for i, line in enumerate(cell16['source']):
    if 'default_cit, 0.3' in line:
        cell16['source'][i] = '        all_citations.append((default_cit, 0.0))  # Below all real RRF scores - defaults fill tail only\n'
        print(f'Fix 3: Default score 0.3 -> 0.0 (cell 16, line {i})')
        break
else:
    print('Fix 3: NOT FOUND')

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print('Done - notebook saved.')
