"""
Add post-processing to planner output:
1. Deduplicate filter codes across directions (earlier directions keep theirs)
2. Enrich single-filter directions with related codes from a lookup table
Modifies cell 15 (run_planner) and cell 19 (run_planner_logged).
"""
import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# The enrichment + dedup code block to insert AFTER directions list is built, BEFORE Plan() construction
ENRICH_DEDUP_BLOCK = '''
    # --- POST-PROCESSING: Deduplicate filters + Enrich single-code directions ---
    # Related codes: if direction has only 1 filter, add its natural companions
    _RELATED_CODES = {
        "StPO": ["BStKR", "JStPO"],
        "StGB": ["JStG"],
        "OR": ["ZGB"],
        "ZGB": ["OR"],
        "BGG": ["BV"],
        "BV": ["BGG"],
        "IVG": ["ATSG"],
        "ATSG": ["IVG", "IVV"],
        "AIG": ["BV"],
        "DBG": ["StHG"],
        "StHG": ["DBG"],
        "1B_": ["7B_"],
        "7B_": ["1B_"],
        "6B_": ["BGE_IV"],
        "BGE_IV": ["6B_"],
        "8C_": ["9C_", "BGE_V"],
        "9C_": ["8C_", "BGE_V"],
        "BGE_V": ["8C_", "9C_"],
        "4A_": ["4D_", "BGE_III"],
        "5A_": ["BGE_III"],
        "2C_": ["BGE_I", "BGE_II"],
    }
    
    used_codes = set()
    for direction in directions:
        # Deduplicate: remove codes already used by higher-priority directions
        original = direction.filter_codes[:]
        direction.filter_codes = [c for c in direction.filter_codes if c not in used_codes]
        
        # Enrich: if only 1 code remains, add related codes
        if len(direction.filter_codes) == 1:
            base = direction.filter_codes[0]
            for related in _RELATED_CODES.get(base, []):
                if related not in used_codes and related not in direction.filter_codes:
                    if related in law_code_to_indices or related in court_code_to_indices:
                        direction.filter_codes.append(related)
        
        # Track all codes this direction now owns
        used_codes.update(direction.filter_codes)
    # --- END POST-PROCESSING ---
'''

# Convert to notebook source lines
enrich_lines = [line + '\n' for line in ENRICH_DEDUP_BLOCK.split('\n')]

def patch_cell(cell_idx, label):
    """Insert the dedup block right before the Plan() construction."""
    src = nb['cells'][cell_idx]['source']
    
    # Find the line with "plan = Plan(" or "return Plan("
    insert_idx = None
    for i, line in enumerate(src):
        if 'Plan(' in line and ('plan = Plan(' in line or 'return Plan(' in line):
            # Check this is the final Plan construction (not a comment or string)
            if 'sachverhalt' in ''.join(src[i:i+3]):
                insert_idx = i
                break
    
    if insert_idx is None:
        print(f"  WARNING: Could not find Plan() construction in {label}")
        return False
    
    # Insert the block before Plan()
    src[insert_idx:insert_idx] = enrich_lines
    print(f"  {label}: Inserted dedup+enrich block at source line {insert_idx}")
    return True

# Cell 15 = index 14 (run_planner)
print("Patching cell 15 (run_planner)...")
patch_cell(14, "Cell 15")

# Cell 19 = index 18 (run_planner_logged)
print("Patching cell 19 (run_planner_logged)...")
patch_cell(18, "Cell 19")

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\nDone! Saved notebook with dedup + enrich post-processing.")
