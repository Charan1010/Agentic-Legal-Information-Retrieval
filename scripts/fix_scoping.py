"""Fix scoping issue in defaults_injected (sims undefined when defaults is empty)."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

cell16 = nb['cells'][16]
src = cell16['source']

# The block was inserted as a single multiline string element.
# Fix: move defaults_injected inside the if block, add else clause
for i, line in enumerate(src):
    if 'SMART DEFAULT FILTERING' in line:
        # Replace the whole block with a properly scoped version
        old_block = src[i]
        new_block = old_block.replace(
            '    defaults_injected = [d for d, s in zip(defaults, sims) if s >= DEFAULTS_SIM_THRESHOLD] if defaults else []\n',
            '        defaults_injected = [d for d, s in zip(defaults, sims) if s >= DEFAULTS_SIM_THRESHOLD]\n'
            '    else:\n'
            '        defaults_injected = []\n'
        )
        src[i] = new_block
        print(f'Fixed scoping: defaults_injected now inside if/else block (line {i})')
        break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print('Done.')
