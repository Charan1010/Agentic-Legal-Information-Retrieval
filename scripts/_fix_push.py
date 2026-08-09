"""Make _push_to_dataset non-fatal so notebook doesn't crash on push failure."""
import json

NB = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb"

with open(NB, "r", encoding="utf-8") as f:
    nb = json.load(f)

fixed = 0
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    new_source = []
    for line in cell["source"]:
        if "raise RuntimeError(msg)" in line:
            # Replace crash with warning + return
            line = line.replace(
                "raise RuntimeError(msg)",
                "return  # non-fatal: local cache is fine"
            )
            fixed += 1
        new_source.append(line)
    cell["source"] = new_source

with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Fixed {fixed} occurrence(s) of raise RuntimeError -> return")
