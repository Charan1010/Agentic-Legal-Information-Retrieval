"""Replace inline routing guides with file-read approach in cell 14."""
import json

NB = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'

with open(NB, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][14]
lines = cell['source']
src = ''.join(lines)

# Find the boundaries of the inline ROUTING_GUIDE_LAWS and ROUTING_GUIDE_COURTS
# They are triple-quoted strings assigned to variables

# Find ROUTING_GUIDE_LAWS = """ ... """
laws_start = None
laws_end = None
courts_start = None
courts_end = None

for i, line in enumerate(lines):
    if 'ROUTING_GUIDE_LAWS = """' in line:
        laws_start = i
    if laws_start and laws_end is None and line.strip() == '"""' and i > laws_start:
        laws_end = i
    if 'ROUTING_GUIDE_COURTS = """' in line:
        courts_start = i
    if courts_start and courts_end is None and line.strip() == '"""' and i > courts_start:
        courts_end = i

print(f"ROUTING_GUIDE_LAWS: lines {laws_start}-{laws_end}")
print(f"ROUTING_GUIDE_COURTS: lines {courts_start}-{courts_end}")

# Also find the comment line before ROUTING_GUIDE_LAWS
comment_start = laws_start
for i in range(laws_start - 1, max(laws_start - 5, 0), -1):
    if '# ---- Swiss Legal' in lines[i] or '# This guide' in lines[i]:
        comment_start = i

print(f"Comment block starts at: {comment_start}")

# Replace the entire inline block (comments + ROUTING_GUIDE_LAWS + ROUTING_GUIDE_COURTS)
# with a file-read approach
file_read_code = '''# ---- Load Swiss Legal Routing Guide from external files ----
# Keeps prompt cell clean; edit data/routing_guide_laws.txt and data/routing_guide_courts.txt directly
_GUIDE_DIR = DATA_PATH  # Same as competition data path
_laws_guide_path = _GUIDE_DIR / "routing_guide_laws.txt"
_courts_guide_path = _GUIDE_DIR / "routing_guide_courts.txt"

if _laws_guide_path.exists():
    ROUTING_GUIDE_LAWS = _laws_guide_path.read_text(encoding="utf-8")
    print(f"  Loaded routing_guide_laws.txt ({len(ROUTING_GUIDE_LAWS)} chars)")
else:
    ROUTING_GUIDE_LAWS = ""
    print(f"  WARNING: {_laws_guide_path} not found — routing guide disabled for laws")

if _courts_guide_path.exists():
    ROUTING_GUIDE_COURTS = _courts_guide_path.read_text(encoding="utf-8")
    print(f"  Loaded routing_guide_courts.txt ({len(ROUTING_GUIDE_COURTS)} chars)")
else:
    ROUTING_GUIDE_COURTS = ""
    print(f"  WARNING: {_courts_guide_path} not found — routing guide disabled for courts")

'''

# Build new lines: everything before the comment block + file-read code + everything after courts_end
new_lines = lines[:comment_start]
for code_line in file_read_code.split('\n'):
    new_lines.append(code_line + '\n')
new_lines.extend(lines[courts_end + 1:])

cell['source'] = new_lines

# Verify
new_src = ''.join(new_lines)
assert 'routing_guide_laws.txt' in new_src
assert 'routing_guide_courts.txt' in new_src
assert 'ROUTING_GUIDE_LAWS' in new_src
assert 'ROUTING_GUIDE_COURTS' in new_src
assert '{ROUTING_GUIDE_LAWS}' in new_src  # still referenced in AGENT_SYSTEM_PROMPT f-string

# Make sure the old inline content is gone
assert 'StBOG (Strafbehördenorganisationsgesetz)' not in new_src, "Inline guide still present!"

# Syntax check
compile(new_src, '<cell14>', 'exec')
print("SYNTAX OK")

with open(NB, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"SUCCESS: Replaced inline guides with file-read approach")
print(f"  Old cell: {len(lines)} lines")
print(f"  New cell: {len(new_lines)} lines")
print(f"  Removed: {len(lines) - len(new_lines)} lines of inline content")
