"""Fix court section key matching in 04_planner_director.ipynb.

Problem: _find_section_keys uses case-insensitive SUBSTRING matching.
  - "i. öffentlich-rechtliche" matches BOTH "I. ÖFFENTLICH-RECHTLICHE ABTEILUNG" 
    AND "II. ÖFFENTLICH-RECHTLICHE ABTEILUNG" (because "i. öffentlich" is a 
    substring of "ii. öffentlich...")
    
Solution: Use EXACT section keys from routing_guide_courts.txt directly, 
eliminating all substring matching for court sections.
"""
import json
from pathlib import Path

nb_path = Path(__file__).parent.parent / "notebooks" / "04_planner_director.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find Cell 13 (the large planner cell with _COURT_DIVISION_MATCHERS)
target_cell = None
for cell in nb["cells"]:
    src = "".join(cell.get("source", []))
    if "_COURT_DIVISION_MATCHERS" in src:
        target_cell = cell
        break

if target_cell is None:
    print("ERROR: Could not find target cell")
    exit(1)

src = "".join(target_cell["source"])

# ─── Fix 1: Replace _COURT_DIVISION_MATCHERS block with direct _COURT_TO_SECTIONS ───
old_block_1 = (
    '# \u2500\u2500\u2500 Courts: Map court divisions \u2192 court section keys \u2500\u2500\u2500\n'
    '_COURT_DIVISION_MATCHERS: dict[str, list[str]] = {\n'
    '    "COURT_STRAFPROZESS": ["\u00f6ffentlich-rechtliche abteilung"],  # 1B_ lives in I. \u00d6ffentlich-rechtliche\n'
    '    "COURT_OEFFENTLICH": ["\u00f6ffentlich-rechtliche abteilung", "ii. \u00f6ffentlich"],  # 1C_, 2C_\n'
    '    "COURT_ZIVIL": ["zivilrechtliche"],  # 4A_, 5A_\n'
    '    "COURT_STRAF": ["strafrechtliche"],  # 6B_\n'
    '    "COURT_SOZIAL": ["sozialversicherung"],  # 8C_, 9C_\n'
    '}\n'
    '\n'
    '_COURT_TO_SECTIONS: dict[str, list[str]] = {}\n'
    'for _cdiv, _matchers in _COURT_DIVISION_MATCHERS.items():\n'
    '    _COURT_TO_SECTIONS[_cdiv] = _find_section_keys(_COURT_SECTIONS, _matchers)\n'
    '\n'
    '# Court header (classification rules \u2014 always useful)\n'
    '_COURT_HEADER_KEYS = _find_section_keys(_COURT_SECTIONS, ["routing", "gerichts-routing", "klassifikation"])\n'
    'if not _COURT_HEADER_KEYS:\n'
    '    _COURT_HEADER_KEYS = [list(_COURT_SECTIONS.keys())[0]] if _COURT_SECTIONS else []'
)

new_block_1 = (
    '# \u2500\u2500\u2500 Courts: Map court divisions \u2192 court section keys (EXACT keys, no substring matching) \u2500\u2500\u2500\n'
    '# Using exact section header strings from routing_guide_courts.txt to avoid\n'
    '# substring ambiguity (e.g. "i. \u00f6ffentlich" matching "ii. \u00f6ffentlich...")\n'
    '_COURT_TO_SECTIONS: dict[str, list[str]] = {\n'
    '    "COURT_STRAFPROZESS": ["I. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],       # 1B_ detention/coercive\n'
    '    "COURT_VERWALTUNG":   ["I. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],       # 1C_ admin/planning\n'
    '    "COURT_OEFFENTLICH":  ["II. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],      # 2C_ foreigners/tax/health\n'
    '    "COURT_VERTRAG":      ["ZIVILRECHTLICHE ABTEILUNGEN"],                  # 4A_ contracts\n'
    '    "COURT_FAMILIE":      ["ZIVILRECHTLICHE ABTEILUNGEN"],                  # 5A_ family/inheritance\n'
    '    "COURT_ZIVIL":        ["ZIVILRECHTLICHE ABTEILUNGEN"],                  # 4A_+5A_ combined\n'
    '    "COURT_STRAF":        ["STRAFRECHTLICHE ABTEILUNG"],                    # 6B_ criminal\n'
    '    "COURT_SOZIAL":       ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],    # 8C_+9C_ combined\n'
    '    "COURT_SOZIAL_IV":    ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],    # 8C_ IV/UV/ALV\n'
    '    "COURT_SOZIAL_RENTEN":["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],    # 9C_ AHV/KV/EL\n'
    '}\n'
    '\n'
    '# Court header (classification rules \u2014 always useful)\n'
    '_COURT_HEADER_KEYS = ["GERICHTS-ROUTING (search_courts)"]'
)

if old_block_1 not in src:
    print("ERROR: old_block_1 not found in source")
    idx = src.find("_COURT_DIVISION_MATCHERS")
    if idx >= 0:
        print(f"Found _COURT_DIVISION_MATCHERS at pos {idx}")
        print(repr(src[idx-50:idx+600]))
    exit(1)

src = src.replace(old_block_1, new_block_1)
print("Fix 1 applied: _COURT_TO_SECTIONS with exact keys")

# ─── Fix 2: Replace _COURT_KW_TO_SECTIONS ───
old_block_2 = (
    '# Map court keywords \u2192 which court sections to include\n'
    '_COURT_KW_TO_SECTIONS: dict[str, list[str]] = {\n'
    '    "COURT_STRAFPROZESS": _find_section_keys(_COURT_SECTIONS, ["i. \u00f6ffentlich-rechtliche"]),\n'
    '    "COURT_VERWALTUNG": _find_section_keys(_COURT_SECTIONS, ["i. \u00f6ffentlich-rechtliche"]),\n'
    '    "COURT_OEFFENTLICH": _find_section_keys(_COURT_SECTIONS, ["ii. \u00f6ffentlich-rechtliche"]),\n'
    '    "COURT_VERTRAG": _find_section_keys(_COURT_SECTIONS, ["zivilrechtliche"]),\n'
    '    "COURT_FAMILIE": _find_section_keys(_COURT_SECTIONS, ["zivilrechtliche"]),\n'
    '    "COURT_STRAF": _find_section_keys(_COURT_SECTIONS, ["strafrechtliche"]),\n'
    '    "COURT_SOZIAL_IV": _find_section_keys(_COURT_SECTIONS, ["sozialversicherung"]),\n'
    '    "COURT_SOZIAL_RENTEN": _find_section_keys(_COURT_SECTIONS, ["sozialversicherung"]),\n'
    '}'
)

new_block_2 = (
    '# Map court keywords \u2192 which court sections to include (EXACT keys, no substring matching)\n'
    '_COURT_KW_TO_SECTIONS: dict[str, list[str]] = {\n'
    '    "COURT_STRAFPROZESS": ["I. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],\n'
    '    "COURT_VERWALTUNG":   ["I. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],\n'
    '    "COURT_OEFFENTLICH":  ["II. \u00d6FFENTLICH-RECHTLICHE ABTEILUNG"],\n'
    '    "COURT_VERTRAG":      ["ZIVILRECHTLICHE ABTEILUNGEN"],\n'
    '    "COURT_FAMILIE":      ["ZIVILRECHTLICHE ABTEILUNGEN"],\n'
    '    "COURT_STRAF":        ["STRAFRECHTLICHE ABTEILUNG"],\n'
    '    "COURT_SOZIAL_IV":    ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],\n'
    '    "COURT_SOZIAL_RENTEN":["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],\n'
    '}'
)

if old_block_2 not in src:
    print("ERROR: old_block_2 not found in source")
    idx = src.find("_COURT_KW_TO_SECTIONS")
    if idx >= 0:
        print(f"Found _COURT_KW_TO_SECTIONS at pos {idx}")
        print(repr(src[idx-50:idx+700]))
    exit(1)

src = src.replace(old_block_2, new_block_2)
print("Fix 2 applied: _COURT_KW_TO_SECTIONS with exact keys")

# ─── Fix 3: Update _DOMAIN_TO_COURT_DIVISIONS to use correct keys ───
old_block_3 = (
    '_DOMAIN_TO_COURT_DIVISIONS: dict[str, list[str]] = {\n'
    '    "STRAFRECHT": ["COURT_STRAF"],\n'
    '    "STRAFPROZESS": ["COURT_STRAFPROZESS", "COURT_STRAF"],\n'
    '    "ZIVILRECHT": ["COURT_ZIVIL"],\n'
    '    "PROZESSRECHT": ["COURT_ZIVIL", "COURT_STRAF"],  # procedural spans all\n'
    '    "SOZIALVERSICHERUNG": ["COURT_SOZIAL"],\n'
    '    "OEFFENTLICHES_RECHT": ["COURT_OEFFENTLICH"],\n'
    '    "STEUERRECHT": ["COURT_OEFFENTLICH"],\n'
    '    "FINANZMARKTRECHT": ["COURT_OEFFENTLICH"],\n'
    '    "WEITERE": ["COURT_OEFFENTLICH", "COURT_STRAF"],\n'
    '}'
)

new_block_3 = (
    '_DOMAIN_TO_COURT_DIVISIONS: dict[str, list[str]] = {\n'
    '    "STRAFRECHT": ["COURT_STRAF"],\n'
    '    "STRAFPROZESS": ["COURT_STRAFPROZESS", "COURT_STRAF"],\n'
    '    "ZIVILRECHT": ["COURT_VERTRAG", "COURT_FAMILIE"],\n'
    '    "PROZESSRECHT": ["COURT_VERTRAG", "COURT_STRAF"],  # procedural spans civil + criminal\n'
    '    "SOZIALVERSICHERUNG": ["COURT_SOZIAL_IV", "COURT_SOZIAL_RENTEN"],\n'
    '    "OEFFENTLICHES_RECHT": ["COURT_OEFFENTLICH", "COURT_VERWALTUNG"],\n'
    '    "STEUERRECHT": ["COURT_OEFFENTLICH"],\n'
    '    "FINANZMARKTRECHT": ["COURT_OEFFENTLICH"],\n'
    '    "WEITERE": ["COURT_OEFFENTLICH", "COURT_STRAF"],\n'
    '}'
)

if old_block_3 not in src:
    print("ERROR: old_block_3 not found in source")
    idx = src.find("_DOMAIN_TO_COURT_DIVISIONS")
    if idx >= 0:
        print(f"Found at pos {idx}")
        print(repr(src[idx:idx+500]))
    exit(1)

src = src.replace(old_block_3, new_block_3)
print("Fix 3 applied: _DOMAIN_TO_COURT_DIVISIONS updated")

# Write back — preserve source line format
target_cell["source"] = [line + "\n" for line in src.split("\n")]
# Last line shouldn't have trailing newline if original didn't
if target_cell["source"][-1] == "\n":
    target_cell["source"] = target_cell["source"][:-1]

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\nAll 3 fixes applied and notebook saved!")
print("\nSummary of changes:")
print("  1. Removed _COURT_DIVISION_MATCHERS (substring-based) → direct _COURT_TO_SECTIONS dict with exact keys")
print("  2. _COURT_KW_TO_SECTIONS now uses exact keys instead of _find_section_keys()")
print("  3. _DOMAIN_TO_COURT_DIVISIONS updated: COURT_ZIVIL→COURT_VERTRAG/FAMILLE, COURT_SOZIAL→IV/RENTEN")
print("  4. _COURT_HEADER_KEYS hardcoded to exact key: 'GERICHTS-ROUTING (search_courts)'")
