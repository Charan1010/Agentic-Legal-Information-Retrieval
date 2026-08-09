"""Fix _push_to_dataset to properly handle 403 and fallback to create."""
import json

NB = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb"

with open(NB, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find and replace the push logic in the cell that has _push_to_dataset
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    if "def _push_to_dataset" not in src:
        continue
    
    # Replace the old fallback condition + hard check block
    old_lines = [
        '    # If dataset doesn\'t exist yet, create it\n',
        '    if result.returncode != 0 and ("404" in result.stderr or "not found" in result.stderr.lower()):\n',
    ]
    new_lines = [
        '    # If dataset doesn\'t exist yet or version fails (403/404), create it\n',
        '    if result.returncode != 0 and ("404" in result.stderr or "not found" in result.stderr.lower() or "403" in result.stdout or "Forbidden" in result.stdout):\n',
    ]
    
    new_source = []
    i = 0
    while i < len(cell["source"]):
        line = cell["source"][i]
        if '("404" in result.stderr or "not found" in result.stderr.lower())' in line:
            # Replace this line with expanded condition
            new_source.append('    if result.returncode != 0 and ("404" in result.stderr or "not found" in result.stderr.lower() or "403" in result.stdout or "Forbidden" in result.stdout):\n')
            i += 1
            continue
        # Also fix the hard check to be non-fatal but still print clearly
        elif "return  # non-fatal: local cache is fine" in line:
            new_source.append('        print("  \\u26a0\\ufe0f  Push failed — local files saved to /kaggle/working/cache/ (will retry at next checkpoint)")\n')
            new_source.append('        return\n')
            i += 1
            continue
        new_source.append(line)
        i += 1
    
    cell["source"] = new_source
    print("Fixed _push_to_dataset: expanded 403/Forbidden fallback + non-fatal return")
    break

with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Done")
