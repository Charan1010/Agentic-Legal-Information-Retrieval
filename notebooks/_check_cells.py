import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))
    if 'CELL 4: LOAD LLM' in src:
        print(f"=== Cell index {i} (CELL 4: LOAD LLM) ===")
        print(src)
        print("=" * 60)
    if 'CELL 7: FAISS' in src:
        print(f"=== Cell index {i} (CELL 7: FAISS) ===")
        print(src[:600])
        print("=" * 60)
