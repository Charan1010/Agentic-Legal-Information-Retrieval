"""Patch Cell 11 (ReAct Agent) in the notebook with the new structured agent."""
import json
from pathlib import Path

NB_PATH = Path("notebooks/03_hyde_kaggle.ipynb")
NEW_CELL_PATH = Path("scripts/new_agent_cell.py")

# Read notebook
with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Read new cell source
with open(NEW_CELL_PATH, "r", encoding="utf-8") as f:
    new_source = f.read()

# Find the target cell
target_idx = None
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        src = "".join(cell["source"])
        if "CELL 10: REACT AGENT" in src:
            target_idx = i
            break

if target_idx is None:
    raise ValueError("Could not find 'CELL 10: REACT AGENT' cell")

# Convert to notebook source format (list of lines with \n)
lines = new_source.split("\n")
source_lines = [line + "\n" for line in lines[:-1]]  # all but last get \n
source_lines.append(lines[-1])  # last line without trailing \n

# Replace
nb["cells"][target_idx]["source"] = source_lines
nb["cells"][target_idx]["outputs"] = []

# Write back
with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Patched cell at index {target_idx}")
print(f"  New source: {len(source_lines)} lines")
print(f"  Key changes:")
print(f"    - GBNF grammar constrains output to valid JSON")
print(f"    - Pydantic AgentAction model validates parsed output")
print(f"    - Single action per turn (no multi-action parsing)")
print(f"    - Observations: summary only (count + top-5 citation IDs)")
print(f"    - No extract_citations_from_text (citations from tools only)")
