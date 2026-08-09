"""Replace inline routing guide file-read code with multi-path search version."""
import json

NB = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'
OUT = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\scripts\_result2.txt'

try:
    with open(NB, encoding='utf-8') as f:
        nb = json.load(f)

    # Find the agent cell (cell index 14 = 15th cell, 0-indexed)
    cell = nb['cells'][14]
    lines = cell['source']
    result = f"Cell 14 has {len(lines)} lines\n"

    # Find the old file-read block
    old_start = None
    old_end = None
    for i, line in enumerate(lines):
        if '# ---- Load Swiss Legal Routing Guide from external files' in line:
            old_start = i
        if old_start and 'AGENT_SYSTEM_PROMPT = f"""' in line:
            old_end = i
            break

    result += f"old_start={old_start}, old_end={old_end}\n"

    if old_start is None or old_end is None:
        result += "ERROR: Could not find boundaries\n"
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write(result)
        raise SystemExit(1)

    # New replacement block
    new_block = [
        '# ---- Load Swiss Legal Routing Guide from external .txt files ----\n',
        '# Keeps this cell clean; edit routing_guide_laws.txt and routing_guide_courts.txt directly.\n',
        '# On Kaggle: upload the .txt files as a utility dataset named "routing-guides"\n',
        '_GUIDE_SEARCH_PATHS = [\n',
        '    Path("."),                                          # Kaggle working dir / local CWD\n',
        '    Path("/kaggle/input/routing-guides"),               # Kaggle utility dataset\n',
        '    DATA_PATH,                                         # Competition data dir (fallback)\n',
        '    Path("../data"),                                   # Local dev (notebook in notebooks/)\n',
        ']\n',
        '\n',
        'def _find_guide(filename):\n',
        '    for p in _GUIDE_SEARCH_PATHS:\n',
        '        candidate = p / filename\n',
        '        if candidate.exists():\n',
        '            return candidate\n',
        '    return None\n',
        '\n',
        '_laws_guide_path = _find_guide("routing_guide_laws.txt")\n',
        '_courts_guide_path = _find_guide("routing_guide_courts.txt")\n',
        '\n',
        'if _laws_guide_path:\n',
        '    ROUTING_GUIDE_LAWS = _laws_guide_path.read_text(encoding="utf-8")\n',
        '    print(f"  Loaded {_laws_guide_path} ({len(ROUTING_GUIDE_LAWS)} chars)")\n',
        'else:\n',
        '    ROUTING_GUIDE_LAWS = ""\n',
        '    print("  WARNING: routing_guide_laws.txt not found — guide disabled")\n',
        '\n',
        'if _courts_guide_path:\n',
        '    ROUTING_GUIDE_COURTS = _courts_guide_path.read_text(encoding="utf-8")\n',
        '    print(f"  Loaded {_courts_guide_path} ({len(ROUTING_GUIDE_COURTS)} chars)")\n',
        'else:\n',
        '    ROUTING_GUIDE_COURTS = ""\n',
        '    print("  WARNING: routing_guide_courts.txt not found — guide disabled")\n',
        '\n',
    ]

    # Replace: keep lines before old_start, add new block, keep from old_end onward
    new_lines = lines[:old_start] + new_block + lines[old_end:]
    cell['source'] = new_lines

    # Verify
    new_src = ''.join(new_lines)
    assert '_GUIDE_SEARCH_PATHS' in new_src
    assert '_find_guide' in new_src
    assert 'AGENT_SYSTEM_PROMPT = f"""' in new_src
    assert '{ROUTING_GUIDE_LAWS}' in new_src
    assert '{ROUTING_GUIDE_COURTS}' in new_src

    # Syntax check
    compile(new_src, '<cell14>', 'exec')
    result += "SYNTAX OK\n"

    with open(NB, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    result += f"SUCCESS: {len(lines)} -> {len(new_lines)} lines (removed {len(lines)-len(new_lines)} old lines)\n"

except Exception as e:
    import traceback
    result = f"ERROR: {e}\n{traceback.format_exc()}"

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(result)
