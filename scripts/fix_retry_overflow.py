"""Fix context overflow in planner retry logic (cells 14 and 18)."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# ═══ Fix 1: Cell 14 (run_planner - non-logged) ═══
cell14 = nb['cells'][14]
src14 = ''.join(cell14['source'])

old_retry_14 = '''    except json.JSONDecodeError:
        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"
        response2 = llm(prompt2, max_tokens=CONFIG["max_tokens_planner"],
                        temperature=0.0, grammar=planner_grammar, stop=["[INST]", "</s>"])
        raw2 = response2["choices"][0]["text"].strip()
        try:
            data = json.loads(raw2)
        except json.JSONDecodeError:
            return None'''

new_retry_14 = '''    except json.JSONDecodeError:
        # Guard: retry only if appended prompt fits in context window
        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"
        if len(prompt2) // 4 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 100:
            return None  # Would overflow context — skip to fallback
        response2 = llm(prompt2, max_tokens=CONFIG["max_tokens_planner"],
                        temperature=0.0, grammar=planner_grammar, stop=["[INST]", "</s>"])
        raw2 = response2["choices"][0]["text"].strip()
        try:
            data = json.loads(raw2)
        except json.JSONDecodeError:
            return None'''

if old_retry_14 in src14:
    src14 = src14.replace(old_retry_14, new_retry_14, 1)
    cell14['source'] = [src14]
    print("Fix 1 (cell 14 run_planner): Applied")
else:
    print("Fix 1 (cell 14): Pattern not found — checking alternate...")
    # Try with the actual escaped string as it appears in the notebook
    if 'prompt2 = prompt + "\\n" + raw' in src14:
        print("  Found prompt2 line — applying manual fix")
        src14 = src14.replace(
            '        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"\n        response2 = llm(prompt2',
            '        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"\n        if len(prompt2) // 4 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 100:\n            return None  # Would overflow context\n        response2 = llm(prompt2',
            1
        )
        cell14['source'] = [src14]
        print("  Applied alternate fix")
    else:
        print("  NOT FOUND")

# ═══ Fix 2: Cell 18 (run_planner_logged) ═══
cell18 = nb['cells'][18]
src18 = ''.join(cell18['source'])

old_retry_18 = '        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"\n        response2 = llm(prompt2'
new_retry_18 = '        prompt2 = prompt + "\\n" + raw + "\\n[INST] Output NUR valides JSON. [/INST]"\n        if len(prompt2) // 4 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 100:\n            L.debug("  ✗ Retry would overflow context window — returning None")\n            return None\n        response2 = llm(prompt2'

if old_retry_18 in src18:
    src18 = src18.replace(old_retry_18, new_retry_18, 1)
    cell18['source'] = [src18]
    print("Fix 2 (cell 18 run_planner_logged): Applied")
else:
    print("Fix 2 (cell 18): Pattern not found")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print("\nDone.")
