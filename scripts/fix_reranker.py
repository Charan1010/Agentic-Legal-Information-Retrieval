"""Fix Qwen3Reranker yes/no token IDs - use 'Yes'/'No' instead of 'yes'/'no'."""
import json

nb_path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the reranker cell (Cell 9)
target_cell = None
for cell in nb['cells']:
    source = ''.join(cell.get('source', []))
    if 'class Qwen3Reranker' in source:
        target_cell = cell
        break

if target_cell is None:
    print('ERROR: Could not find Qwen3Reranker cell')
    exit(1)

source_text = ''.join(target_cell['source'])

# Fix: Change "yes" -> "Yes" and "no" -> "No"
old_yes = 'self.yes_id = self.tokenizer.convert_tokens_to_ids("yes")'
new_yes = 'self.yes_id = self.tokenizer.convert_tokens_to_ids("Yes")'

old_no = 'self.no_id = self.tokenizer.convert_tokens_to_ids("no")'
new_no = 'self.no_id = self.tokenizer.convert_tokens_to_ids("No")'

if old_yes in source_text:
    source_text = source_text.replace(old_yes, new_yes)
    print('Fix applied: "yes" -> "Yes"')
else:
    print('FAILED: Could not find yes_id line')

if old_no in source_text:
    source_text = source_text.replace(old_no, new_no)
    print('Fix applied: "no" -> "No"')
else:
    print('FAILED: Could not find no_id line')

# Also add diagnostic logging to confirm token IDs at init time
old_init_end = 'self.no_id = self.tokenizer.convert_tokens_to_ids("No")\n'
new_init_end = '''self.no_id = self.tokenizer.convert_tokens_to_ids("No")
        # Diagnostic: verify token IDs are valid (not UNK)
        print(f"[Qwen3Reranker] yes_id={self.yes_id}, no_id={self.no_id}")
        if self.yes_id == self.tokenizer.unk_token_id:
            print("[WARNING] yes_id is UNK! Trying alternatives...")
            for candidate in ["Yes", "yes", "YES", "true", "True"]:
                tid = self.tokenizer.convert_tokens_to_ids(candidate)
                print(f"  '{candidate}' -> {tid} (unk={tid == self.tokenizer.unk_token_id})")
        if self.no_id == self.tokenizer.unk_token_id:
            print("[WARNING] no_id is UNK! Trying alternatives...")
            for candidate in ["No", "no", "NO", "false", "False"]:
                tid = self.tokenizer.convert_tokens_to_ids(candidate)
                print(f"  '{candidate}' -> {tid} (unk={tid == self.tokenizer.unk_token_id})")
'''

if new_init_end.split('\n')[0] in source_text:
    # Just add the diagnostic after the no_id line
    source_text = source_text.replace(
        'self.no_id = self.tokenizer.convert_tokens_to_ids("No")\n',
        new_init_end
    )
    print('Added token ID diagnostic logging')
else:
    print('Could not add diagnostic logging (no_id line not found after fix)')

# Write back
source_lines = target_cell['source']
new_lines = [line + '\n' for line in source_text.split('\n')]
if source_lines and not source_lines[-1].endswith('\n'):
    new_lines[-1] = new_lines[-1].rstrip('\n')
target_cell['source'] = new_lines

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('Notebook saved successfully')
