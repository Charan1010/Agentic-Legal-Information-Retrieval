"""Replace inline routing guides with file-read approach - direct JSON manipulation."""
import json
import sys

NB = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'
OUT = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\scripts\_result.txt'

try:
    with open(NB, encoding='utf-8') as f:
        nb = json.load(f)

    # Find cell 14 (CELL 10: STRUCTURED REACT AGENT)
    cell = nb['cells'][14]
    lines = cell['source']

    # Find boundaries in the source array
    guide_comment_idx = None
    routing_laws_idx = None
    routing_courts_idx = None
    agent_prompt_idx = None

    for i, line in enumerate(lines):
        if '# ---- Swiss Legal Corpus Routing Guide' in line:
            guide_comment_idx = i
        if 'ROUTING_GUIDE_LAWS = """' in line:
            routing_laws_idx = i
        if 'ROUTING_GUIDE_COURTS = """' in line:
            routing_courts_idx = i
        if 'AGENT_SYSTEM_PROMPT = f"""' in line:
            agent_prompt_idx = i

    result = f"guide_comment_idx={guide_comment_idx}\n"
    result += f"routing_laws_idx={routing_laws_idx}\n"
    result += f"routing_courts_idx={routing_courts_idx}\n"
    result += f"agent_prompt_idx={agent_prompt_idx}\n"
    result += f"total_lines={len(lines)}\n"

    if None in (guide_comment_idx, routing_laws_idx, routing_courts_idx, agent_prompt_idx):
        result += "ERROR: Could not find all markers\n"
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write(result)
        sys.exit(1)

    # The inline guide runs from guide_comment_idx to agent_prompt_idx-1
    # We need to find the closing """ of ROUTING_GUIDE_COURTS
    courts_end_idx = None
    for i in range(routing_courts_idx + 1, agent_prompt_idx):
        if lines[i].strip() == '"""':
            courts_end_idx = i

    result += f"courts_end_idx={courts_end_idx}\n"

    # Build replacement: file-read code
    file_read_lines = [
        "# ---- Load Swiss Legal Routing Guide from external files ----\n",
        "# Keeps prompt cell clean; edit data/routing_guide_laws.txt and data/routing_guide_courts.txt directly\n",
        "_GUIDE_DIR = DATA_PATH  # Same as competition data path\n",
        "_laws_guide_path = _GUIDE_DIR / \"routing_guide_laws.txt\"\n",
        "_courts_guide_path = _GUIDE_DIR / \"routing_guide_courts.txt\"\n",
        "\n",
        "if _laws_guide_path.exists():\n",
        "    ROUTING_GUIDE_LAWS = _laws_guide_path.read_text(encoding=\"utf-8\")\n",
        "    print(f\"  Loaded routing_guide_laws.txt ({len(ROUTING_GUIDE_LAWS)} chars)\")\n",
        "else:\n",
        "    ROUTING_GUIDE_LAWS = \"\"\n",
        "    print(f\"  WARNING: {_laws_guide_path} not found — routing guide disabled for laws\")\n",
        "\n",
        "if _courts_guide_path.exists():\n",
        "    ROUTING_GUIDE_COURTS = _courts_guide_path.read_text(encoding=\"utf-8\")\n",
        "    print(f\"  Loaded routing_guide_courts.txt ({len(ROUTING_GUIDE_COURTS)} chars)\")\n",
        "else:\n",
        "    ROUTING_GUIDE_COURTS = \"\"\n",
        "    print(f\"  WARNING: {_courts_guide_path} not found — routing guide disabled for courts\")\n",
        "\n",
    ]

    # Replace: keep lines before guide_comment, insert file_read_lines, then lines from agent_prompt onward
    new_lines = lines[:guide_comment_idx] + file_read_lines + lines[agent_prompt_idx:]

    cell['source'] = new_lines

    # Verify
    new_src = ''.join(new_lines)
    assert 'routing_guide_laws.txt' in new_src
    assert 'routing_guide_courts.txt' in new_src
    assert 'ROUTING_GUIDE_LAWS' in new_src
    assert 'ROUTING_GUIDE_COURTS' in new_src
    assert '{ROUTING_GUIDE_LAWS}' in new_src  # still in f-string
    assert 'StBOG' not in new_src  # inline content gone

    # Syntax check
    compile(new_src, '<cell14>', 'exec')
    result += "SYNTAX OK\n"

    with open(NB, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    result += f"SUCCESS: Old lines={len(lines)}, New lines={len(new_lines)}\n"
    result += f"Removed {len(lines) - len(new_lines)} inline guide lines\n"

except Exception as e:
    result = f"ERROR: {type(e).__name__}: {e}\n"
    import traceback
    result += traceback.format_exc()

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(result)
