"""Fix OOM: reduce batch_size, max_seq_length, and truncate text in embed_corpus."""
import json

NB_PATH = r"C:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def set_source(cell, text):
    """Set cell source from a text string."""
    lines = text.split('\n')
    cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]]

changes = 0

# --- Fix 1: CONFIG embed_max_length 8192 → 512 ---
for cell in nb['cells']:
    src = ''.join(cell['source'])
    if '"embed_max_length": 8192' in src:
        new_src = src.replace('"embed_max_length": 8192', '"embed_max_length": 512')
        set_source(cell, new_src)
        changes += 1
        print("✅ CONFIG: embed_max_length 8192 → 512")
        break

# --- Fix 2: embed_corpus batch_size default 64 → 16, and truncate text ---
for cell in nb['cells']:
    src = ''.join(cell['source'])
    if 'def embed_corpus(documents' in src and 'batch_size=64' in src:
        # Change default batch_size
        new_src = src.replace('batch_size=64', 'batch_size=16')
        
        # Truncate text in embed_corpus: add [:400] to text extraction
        old_texts_line = 'texts = [f"{d.get(\'citation\',\'\')}: {d.get(\'text\',\'\')}" for d in documents]'
        new_texts_line = 'texts = [f"{d.get(\'citation\',\'\')}: {d.get(\'text\',\'\')[:400]}" for d in documents]'
        new_src = new_src.replace(old_texts_line, new_texts_line)
        
        set_source(cell, new_src)
        changes += 1
        print("✅ embed_corpus: batch_size=64→16, text truncated to 400 chars")
        break

print(f"\nTotal changes: {changes}")

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook saved.")
