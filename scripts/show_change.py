import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell_num, cell in enumerate(nb['cells'], 1):
    if cell['cell_type'] == 'code':
        src = ''.join(cell['source'])
        if 'LAW_TYPES_FOR_PROMPT' in src:
            print(f"=== Found in cell #{cell_num} ===")
            # Print lines around the change
            lines = cell['source']
            for i, line in enumerate(lines):
                if 'LAW_TYPES' in line or 'Top-40' in line or '[:40]' in line:
                    # Show context: 2 before, the line, 2 after
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    for j in range(start, end):
                        marker = ">>>" if ('LAW_TYPES' in lines[j] or 'Top-40' in lines[j] or '[:40]' in lines[j]) else "   "
                        print(f"  {marker} L{j:3d}: {lines[j].rstrip()}")
                    print()
            break
