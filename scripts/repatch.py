"""Re-patch Cell 11 with updated grammar. Self-contained - no imports from other scripts."""
import json
from pathlib import Path

NB_PATH = Path(r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb")
NEW_CELL_PATH = Path(r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\scripts\new_agent_cell.py")

# Read notebook
with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Read new cell source
with open(NEW_CELL_PATH, "r", encoding="utf-8") as f:
    new_source = f.read()

# Find the target cell (look for STRUCTURED REACT or old REACT AGENT)
target_idx = None
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        src = "".join(cell["source"])
        if "CELL 10:" in src and ("REACT AGENT" in src or "STRUCTURED REACT" in src):
            target_idx = i
            break

if target_idx is None:
    raise ValueError("Could not find REACT AGENT cell")

# Convert to notebook source format
lines = new_source.split("\n")
source_lines = [line + "\n" for line in lines[:-1]]
source_lines.append(lines[-1])

# Replace
nb["cells"][target_idx]["source"] = source_lines
nb["cells"][target_idx]["outputs"] = []

# Write back
with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"OK - patched cell {target_idx}, {len(source_lines)} lines")
