"""Remove co-citation and E.-section code from the notebook."""
import json

NB_PATH = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Remove Cell 10 entirely (co-citation graph + E.-section index + expand functions)
cell_10 = nb["cells"][10]
print(f"Removing Cell 10: first line = {cell_10['source'][0].strip()[:80]}")
nb["cells"].pop(10)

# 2. Now Cell 15 became Cell 14 (shifted by 1). Find and remove the expand_citations call.
# Search for it explicitly to be safe
removed_lines = 0
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    new_source = []
    skip_next_empty = False
    for line in cell["source"]:
        if "expand_citations(deduped" in line:
            print(f"Removing line: {line.strip()}")
            removed_lines += 1
            skip_next_empty = True
            continue
        if "co-citation graph + E.-section siblings" in line:
            print(f"Removing line: {line.strip()}")
            removed_lines += 1
            skip_next_empty = True
            continue
        if skip_next_empty and line.strip() == "":
            skip_next_empty = False
            continue
        skip_next_empty = False
        new_source.append(line)
    cell["source"] = new_source

print(f"\nRemoved Cell 10 + {removed_lines} lines from agent cell")

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Notebook saved.")
