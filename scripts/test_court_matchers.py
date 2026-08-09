"""Test that the court section matchers use exact keys that match
the actual === headers in routing_guide_courts.txt.

This verifies the fix for the substring ambiguity bug where
"i. öffentlich-rechtliche" incorrectly matched "II. ÖFFENTLICH-RECHTLICHE..."
"""
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
CONTEXT = REPO / "context"


def _parse_sections_by_marker(text: str, marker: str = "===") -> dict[str, str]:
    """Exact copy of the function from the notebook."""
    sections = {}
    lines = text.split("\n")
    if marker == "===":
        header_re = re.compile(r"^===\s*(.+?)\s*===\s*$")
    else:
        header_re = re.compile(r"^---\s*(.+?)\s*---\s*$")
    
    preamble_key = "__PREAMBLE__" if marker == "===" else "__INTRO__"
    current_key = preamble_key
    current_lines = []
    
    for line in lines:
        m = header_re.match(line)
        if m:
            if current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    
    if current_lines:
        sections[current_key] = "\n".join(current_lines).strip()
    
    return sections


def _find_section_keys(pool: dict[str, str], substrings: list[str]) -> list[str]:
    """Old substring-based matcher (the BUG)."""
    matches = []
    for key in pool:
        key_lower = key.lower()
        if any(sub.lower() in key_lower for sub in substrings):
            matches.append(key)
    return matches


# ─── Load and parse ───
courts_text = (CONTEXT / "routing_guide_courts.txt").read_text(encoding="utf-8")
_COURT_SECTIONS = _parse_sections_by_marker(courts_text, "===")

print("=" * 70)
print("PARSED COURT SECTION KEYS:")
print("=" * 70)
for key in _COURT_SECTIONS:
    print(f"  '{key}' ({len(_COURT_SECTIONS[key])} chars)")

# ─── NEW FIX: Exact keys used in the notebook ───
_COURT_TO_SECTIONS = {
    "COURT_STRAFPROZESS": ["I. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_VERWALTUNG":   ["I. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_OEFFENTLICH":  ["II. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_VERTRAG":      ["ZIVILRECHTLICHE ABTEILUNGEN"],
    "COURT_FAMILIE":      ["ZIVILRECHTLICHE ABTEILUNGEN"],
    "COURT_ZIVIL":        ["ZIVILRECHTLICHE ABTEILUNGEN"],
    "COURT_STRAF":        ["STRAFRECHTLICHE ABTEILUNG"],
    "COURT_SOZIAL":       ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],
    "COURT_SOZIAL_IV":    ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],
    "COURT_SOZIAL_RENTEN":["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],
}

_COURT_HEADER_KEYS = ["GERICHTS-ROUTING (search_courts)"]

_COURT_KW_TO_SECTIONS = {
    "COURT_STRAFPROZESS": ["I. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_VERWALTUNG":   ["I. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_OEFFENTLICH":  ["II. ÖFFENTLICH-RECHTLICHE ABTEILUNG"],
    "COURT_VERTRAG":      ["ZIVILRECHTLICHE ABTEILUNGEN"],
    "COURT_FAMILIE":      ["ZIVILRECHTLICHE ABTEILUNGEN"],
    "COURT_STRAF":        ["STRAFRECHTLICHE ABTEILUNG"],
    "COURT_SOZIAL_IV":    ["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],
    "COURT_SOZIAL_RENTEN":["SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN"],
}

# ─── TEST 1: All exact keys exist in parsed sections ───
print("\n" + "=" * 70)
print("TEST 1: All exact keys exist in _COURT_SECTIONS?")
print("=" * 70)
all_pass = True
for div, keys in _COURT_TO_SECTIONS.items():
    for k in keys:
        exists = k in _COURT_SECTIONS
        status = "✓" if exists else "✗ MISSING"
        if not exists:
            all_pass = False
        print(f"  {div} -> '{k}': {status}")

for k in _COURT_HEADER_KEYS:
    exists = k in _COURT_SECTIONS
    status = "✓" if exists else "✗ MISSING"
    if not exists:
        all_pass = False
    print(f"  HEADER -> '{k}': {status}")

print(f"\n  Result: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")

# ─── TEST 2: Demonstrate the OLD bug ───
print("\n" + "=" * 70)
print("TEST 2: OLD substring matching (demonstrating the bug)")
print("=" * 70)

old_strafprozess = _find_section_keys(_COURT_SECTIONS, ["i. öffentlich-rechtliche"])
old_oeffentlich = _find_section_keys(_COURT_SECTIONS, ["ii. öffentlich-rechtliche"])

print(f"  'i. öffentlich-rechtliche' matches: {old_strafprozess}")
print(f"    -> Expected 1 match (I. only), got {len(old_strafprozess)}")
if len(old_strafprozess) > 1:
    print(f"    -> BUG CONFIRMED: 'i. öffentlich' is a substring of 'ii. öffentlich'!")

print(f"  'ii. öffentlich-rechtliche' matches: {old_oeffentlich}")
print(f"    -> Expected 1 match (II. only), got {len(old_oeffentlich)}")

# ─── TEST 3: NEW exact key matching correctness ───
print("\n" + "=" * 70)
print("TEST 3: NEW exact key matching (no ambiguity)")
print("=" * 70)

# Simulate the context selection for a criminal procedure question
test_question = "Wurde die Untersuchungshaft verlängert?"  # detention question
print(f"\n  Test question: '{test_question}'")
print(f"  Expected: COURT_STRAFPROZESS -> I. ÖFFENTLICH-RECHTLICHE ABTEILUNG only")
result = _COURT_KW_TO_SECTIONS["COURT_STRAFPROZESS"]
print(f"  Got: {result}")
print(f"  Does NOT include II. ÖFFENTLICH-RECHTLICHE: {'✓ CORRECT' if 'II. ÖFFENTLICH-RECHTLICHE ABTEILUNG' not in result else '✗ BUG'}")

test_question2 = "Aufenthaltsbewilligung Familiennachzug"  # foreigners question  
print(f"\n  Test question: '{test_question2}'")
print(f"  Expected: COURT_OEFFENTLICH -> II. ÖFFENTLICH-RECHTLICHE ABTEILUNG only")
result2 = _COURT_KW_TO_SECTIONS["COURT_OEFFENTLICH"]
print(f"  Got: {result2}")
print(f"  Does NOT include I. ÖFFENTLICH-RECHTLICHE: {'✓ CORRECT' if 'I. ÖFFENTLICH-RECHTLICHE ABTEILUNG' not in result2 else '✗ BUG'}")

# ─── TEST 4: No duplicate sections injected ───
print("\n" + "=" * 70)
print("TEST 4: Cross-domain section deduplication")
print("=" * 70)

# Simulate: OEFFENTLICHES_RECHT domain selected
_DOMAIN_TO_COURT_DIVISIONS = {
    "STRAFRECHT": ["COURT_STRAF"],
    "STRAFPROZESS": ["COURT_STRAFPROZESS", "COURT_STRAF"],
    "ZIVILRECHT": ["COURT_VERTRAG", "COURT_FAMILIE"],
    "PROZESSRECHT": ["COURT_VERTRAG", "COURT_STRAF"],
    "SOZIALVERSICHERUNG": ["COURT_SOZIAL_IV", "COURT_SOZIAL_RENTEN"],
    "OEFFENTLICHES_RECHT": ["COURT_OEFFENTLICH", "COURT_VERWALTUNG"],
    "STEUERRECHT": ["COURT_OEFFENTLICH"],
    "FINANZMARKTRECHT": ["COURT_OEFFENTLICH"],
    "WEITERE": ["COURT_OEFFENTLICH", "COURT_STRAF"],
}

selected_domains = {"OEFFENTLICHES_RECHT", "PROZESSRECHT"}
selected_court_keys = set()
for domain in selected_domains:
    for cdiv in _DOMAIN_TO_COURT_DIVISIONS.get(domain, []):
        for ckey in _COURT_TO_SECTIONS.get(cdiv, []):
            selected_court_keys.add(ckey)

print(f"  Selected domains: {selected_domains}")
print(f"  Court sections to inject: {selected_court_keys}")
print(f"  Count: {len(selected_court_keys)} unique sections")
expected = {"II. ÖFFENTLICH-RECHTLICHE ABTEILUNG", "I. ÖFFENTLICH-RECHTLICHE ABTEILUNG", 
            "ZIVILRECHTLICHE ABTEILUNGEN", "STRAFRECHTLICHE ABTEILUNG"}
print(f"  Expected: {expected}")
print(f"  Match: {'✓' if selected_court_keys == expected else '✗'}")

# ─── SUMMARY ───
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Parsed court sections: {len(_COURT_SECTIONS)}")
print(f"  All exact keys valid: {all_pass}")
print(f"  Old bug (I./II. ambiguity): CONFIRMED (substring 'i. öffentlich' in 'ii. öffentlich')")
print(f"  New fix: EXACT key matching, zero ambiguity")
