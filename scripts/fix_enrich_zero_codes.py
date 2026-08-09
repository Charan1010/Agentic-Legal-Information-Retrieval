"""
Fix enrichment to handle 0-codes case (when dedup strips all codes).
Uses rechtsgebiet field to assign domain-appropriate codes.
Patches both cell 15 (run_planner) and cell 19 (run_planner_logged).
"""
import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Old block (the part from "used_codes = set()" to "# --- END POST-PROCESSING ---")
OLD_LOGIC = '''    used_codes = set()
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
    # --- END POST-PROCESSING ---'''

NEW_LOGIC = '''    # Rechtsgebiet -> fallback codes when dedup strips everything
    _DOMAIN_FALLBACK = {
        "strafprozess": ["StPO", "BStKR", "JStPO"],
        "strafrecht": ["StGB", "JStG"],
        "zivilrecht": ["OR", "ZGB"],
        "familienrecht": ["ZGB", "OR"],
        "prozessrecht": ["BGG", "BV"],
        "verfahrensrecht": ["BGG", "BV", "VwVG"],
        "sozialversicherung": ["IVG", "ATSG", "IVV"],
        "iv": ["IVG", "ATSG"],
        "oeffentliches_recht": ["AIG", "BV", "VwVG"],
        "steuerrecht": ["DBG", "StHG"],
        "finanzmarktrecht": ["FIDLEG", "FINMAG"],
        "strafverfahren": ["StPO", "BStKR"],
        "leitentscheide": ["BGE_I", "BGE_II", "BGE_III", "BGE_IV", "BGE_V"],
    }

    used_codes = set()
    for direction in directions:
        # Deduplicate: remove codes already used by higher-priority directions
        original = direction.filter_codes[:]
        direction.filter_codes = [c for c in direction.filter_codes if c not in used_codes]
        
        # Enrich: if 0 or 1 codes remain after dedup
        if len(direction.filter_codes) == 0:
            # All codes stripped -> assign from rechtsgebiet
            rg = direction.rechtsgebiet.lower().replace("-", "").replace(" ", "_")
            # Try matching domain keys
            fallback = []
            for key, codes in _DOMAIN_FALLBACK.items():
                if key in rg or rg in key:
                    fallback = codes
                    break
            # Add unused fallback codes
            for fc in fallback:
                if fc not in used_codes:
                    if fc in law_code_to_indices or fc in court_code_to_indices:
                        direction.filter_codes.append(fc)
                if len(direction.filter_codes) >= 3:
                    break
        
        if len(direction.filter_codes) == 1:
            # Single code -> add related companions
            base = direction.filter_codes[0]
            for related in _RELATED_CODES.get(base, []):
                if related not in used_codes and related not in direction.filter_codes:
                    if related in law_code_to_indices or related in court_code_to_indices:
                        direction.filter_codes.append(related)
        
        # Track all codes this direction now owns
        used_codes.update(direction.filter_codes)
    # --- END POST-PROCESSING ---'''

old_lines = [l + '\n' for l in OLD_LOGIC.split('\n')]
new_lines = [l + '\n' for l in NEW_LOGIC.split('\n')]

patched = 0
for cell_idx in [14, 18]:  # Cell 15 and Cell 19
    src = nb['cells'][cell_idx]['source']
    # Find the start of "used_codes = set()"
    start_idx = None
    end_idx = None
    for i, line in enumerate(src):
        if 'used_codes = set()' in line and start_idx is None:
            start_idx = i
        if '# --- END POST-PROCESSING ---' in line:
            end_idx = i + 1  # include this line
            break
    
    if start_idx is not None and end_idx is not None:
        src[start_idx:end_idx] = new_lines
        print(f"Cell {cell_idx+1}: Replaced lines {start_idx}-{end_idx} with new logic ({len(new_lines)} lines)")
        patched += 1
    else:
        print(f"Cell {cell_idx+1}: WARNING - could not find block (start={start_idx}, end={end_idx})")

if patched == 2:
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"\nDone! Patched {patched} cells with 0-codes fallback logic.")
else:
    print(f"\nERROR: Only patched {patched}/2 cells. Not saving.")
