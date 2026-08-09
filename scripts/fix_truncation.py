"""Fix truncation issues in 04_planner_director.ipynb:
1. Cell 2: max_tokens_executor 400 -> 800
2. Cell 14: max_chars 7500 -> 12000, sort selected_court_keys for deterministic iteration
"""
import json
from pathlib import Path

nb_path = Path("notebooks/04_planner_director.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# === FIX 1: Cell 2 — Increase max_tokens_executor from 400 to 800 ===
cell2_src = "".join(nb["cells"][2]["source"])
old_val = '"max_tokens_executor": 400,'
new_val = '"max_tokens_executor": 800,'
assert old_val in cell2_src, f"Could not find '{old_val}' in Cell 2"
cell2_src = cell2_src.replace(old_val, new_val)
nb["cells"][2]["source"] = [cell2_src]
print(f"[Cell 2] max_tokens_executor: 400 -> 800")

# === FIX 2a: Cell 14 — Increase max_chars default from 7500 to 12000 ===
cell14_src = "".join(nb["cells"][14]["source"])
old_sig = "def select_planner_context(question: str, max_chars: int = 7500)"
new_sig = "def select_planner_context(question: str, max_chars: int = 12000)"
assert old_sig in cell14_src, f"Could not find function signature in Cell 14"
cell14_src = cell14_src.replace(old_sig, new_sig)
print(f"[Cell 14] max_chars: 7500 -> 12000")

# === FIX 2b: Cell 14 — Sort selected_court_keys for deterministic iteration ===
old_iter = "for ckey in selected_court_keys:"
new_iter = "for ckey in sorted(selected_court_keys):"
assert old_iter in cell14_src, f"Could not find '{old_iter}' in Cell 14"
cell14_src = cell14_src.replace(old_iter, new_iter)
print(f"[Cell 14] selected_court_keys iteration: set -> sorted(set)")

nb["cells"][14]["source"] = [cell14_src]

# === SAVE ===
with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\nSaved: {nb_path}")
print("All 3 fixes applied successfully.")
