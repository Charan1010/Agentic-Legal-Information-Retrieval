"""Fix prompt overflow: reduce context max_chars and fix retry guard."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# === Fix 1: Reduce max_chars from 12000 to 8000 ===
# German legal text tokenizes at ~2.5-3 chars/token (not 4).
# 12000 chars = ~4000-4800 tokens of context.
# System prompt (9178 chars + codes) = ~3500-4000 tokens.
# Total: 8000-8800 tokens for prompt → only 7584-8384 left for output.
# At 8000 chars: ~2667-3200 tokens context + 4000 system = 6667-7200 prompt.
# Leaves 9184-9717 tokens for output — MORE than enough for 3000.

cell14 = nb['cells'][14]
src14 = ''.join(cell14['source'])
src14 = src14.replace(
    'def select_planner_context(question: str, max_chars: int = 12000)',
    'def select_planner_context(question: str, max_chars: int = 8000)'
)
src14 = src14.replace(
    'if len(context) > max_chars:\n        context = context[:max_chars]',
    'if len(context) > max_chars:\n        context = context[:max_chars]'
)
cell14['source'] = [src14]
print("Fix 1: max_chars 12000 -> 8000")

# === Fix 2: Fix retry overflow guard in cell 14 (run_planner) ===
# The // 4 estimate is too optimistic for German text. Use // 3.
src14 = ''.join(cell14['source'])
src14 = src14.replace(
    'if len(prompt2) // 4 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 100:',
    'if len(prompt2) // 3 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 200:'
)
cell14['source'] = [src14]
print("Fix 2: Retry guard in cell 14: //4 -> //3, margin 100 -> 200")

# === Fix 3: Fix retry overflow guard in cell 18 (run_planner_logged) ===
cell18 = nb['cells'][18]
src18 = ''.join(cell18['source'])
src18 = src18.replace(
    'if len(prompt2) // 4 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 100:',
    'if len(prompt2) // 3 > CONFIG["n_ctx"] - CONFIG["max_tokens_planner"] - 200:'
)
cell18['source'] = [src18]
print("Fix 3: Retry guard in cell 18: //4 -> //3, margin 100 -> 200")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print("\nDone. Prompt will now be ~4000 chars shorter → model gets full 3000 tokens for output.")
