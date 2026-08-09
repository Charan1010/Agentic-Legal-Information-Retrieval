"""
Make Qwen3Reranker robust: if convert_tokens_to_ids("Yes"/"No") returns UNK,
fall back to tokenizer.encode() to find the correct token ID.
"""
import json

nb_path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the reranker cell
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

# Replace the yes_id/no_id assignment + diagnostic block with a robust version
old_block = '''        self.yes_id = self.tokenizer.convert_tokens_to_ids("Yes")
        self.no_id = self.tokenizer.convert_tokens_to_ids("No")
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
                print(f"  '{candidate}' -> {tid} (unk={tid == self.tokenizer.unk_token_id})")'''

new_block = '''        # Robust token ID resolution for yes/no scoring
        self.yes_id = self._resolve_token_id("Yes", ["yes", "YES", "true", "True"])
        self.no_id = self._resolve_token_id("No", ["no", "NO", "false", "False"])
        print(f"[Qwen3Reranker] yes_id={self.yes_id}, no_id={self.no_id}")

    def _resolve_token_id(self, primary: str, fallbacks: list) -> int:
        """Resolve a token string to its ID, trying multiple strategies."""
        unk = self.tokenizer.unk_token_id
        # Strategy 1: convert_tokens_to_ids (works if it's a single vocab entry)
        tid = self.tokenizer.convert_tokens_to_ids(primary)
        if tid != unk:
            print(f"  [token] '{primary}' -> {tid} (via convert_tokens_to_ids)")
            return tid
        # Strategy 2: encode and take last token (handles BPE splits)
        encoded = self.tokenizer.encode(primary, add_special_tokens=False)
        if encoded:
            tid = encoded[-1]  # last token usually captures the word
            print(f"  [token] '{primary}' -> {tid} (via encode, full={encoded})")
            return tid
        # Strategy 3: try fallbacks
        for fb in fallbacks:
            tid = self.tokenizer.convert_tokens_to_ids(fb)
            if tid != unk:
                print(f"  [token] '{primary}' failed, using '{fb}' -> {tid}")
                return tid
            encoded = self.tokenizer.encode(fb, add_special_tokens=False)
            if encoded:
                tid = encoded[-1]
                print(f"  [token] '{primary}' failed, using '{fb}' -> {tid} (via encode)")
                return tid
        raise ValueError(f"Could not resolve any token ID for '{primary}' or fallbacks {fallbacks}")'''

if old_block in source_text:
    source_text = source_text.replace(old_block, new_block)
    print('Robust token ID resolution applied')
else:
    print('FAILED: Could not find old block')
    if 'self.yes_id' in source_text:
        idx = source_text.index('self.yes_id')
        print(f'  Context around self.yes_id: {repr(source_text[idx:idx+200])}')

# Write back
source_lines = target_cell['source']
new_lines = [line + '\n' for line in source_text.split('\n')]
if source_lines and not source_lines[-1].endswith('\n'):
    new_lines[-1] = new_lines[-1].rstrip('\n')
target_cell['source'] = new_lines

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('Notebook saved successfully')
