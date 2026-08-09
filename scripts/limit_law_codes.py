"""Limit LAW_TYPES_FOR_PROMPT to top-40 codes in the planner notebook."""
import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

found = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        src = cell['source']
        for i, line in enumerate(src):
            if 'LAW_TYPES_FOR_PROMPT = ' in line:
                # Found it - replace the 4-line block (join + genexpr + if + close-paren)
                old = src[i:i+4]
                print(f'Found at source line {i}, old block:')
                for l in old:
                    print(f'  {repr(l)}')
                new_block = [
                    '# Top-40 law codes only (saves ~7800 chars vs full 200+ list)\n',
                    'LAW_TYPES_FOR_PROMPT = ", ".join(\n',
                    '    f"{t}({c})" for t, c in sorted(\n',
                    '        [(k, v) for k, v in law_type_counts.items() if k != "OTHER" and v >= 10],\n',
                    '        key=lambda x: -x[1]\n',
                    '    )[:40]\n',
                    ')\n',
                ]
                src[i:i+4] = new_block
                print('Replaced with:')
                for l in new_block:
                    print(f'  {repr(l)}')
                found = True
                break
        if found:
            break

if not found:
    print("ERROR: Could not find LAW_TYPES_FOR_PROMPT in any cell!")
    exit(1)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('\nDone - notebook saved with top-40 law codes limit')
