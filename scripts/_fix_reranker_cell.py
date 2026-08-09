"""Fix the mangled Qwen3Reranker section in cell 10."""
import json

NB_PATH = 'notebooks/03_hyde_kaggle.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][10]
lines = cell['source']

# Keep lines 0-69 (everything before the reranker section is fine)
good_prefix = lines[:69]

# Replace lines 69+ with the correct code
correct_suffix = [
    '\n',
    '# ---- NOW load Qwen3-Reranker (generative yes/no, NOT CrossEncoder) ----\n',
    '# WHY: CrossEncoder loads Qwen3 as sequence classification with random head = garbage scores.\n',
    '# Qwen3-Reranker is a causal LM that judges relevance by generating "yes" or "no".\n',
    'from transformers import AutoModelForCausalLM, AutoTokenizer\n',
    'import torch.nn.functional as F\n',
    '\n',
    'RERANKER_TASK_INSTRUCTION = (\n',
    '    "Given a legal question, retrieve all relevant Swiss legal citations "\n',
    '    "including federal statutes (SR) and Federal Court decisions (BGE)"\n',
    ')\n',
    'TEXT_TRUNCATE = 2048\n',
    '\n',
    'class Qwen3Reranker:\n',
    '    """Qwen3-Reranker-0.6B using correct AutoModelForCausalLM approach."""\n',
    '\n',
    '    SYSTEM_PROMPT = (\n',
    '        \'Judge whether the Document meets the requirements based on the \'\n',
    '        \'Query and the Instruct provided. Note that the answer can only be \'\n',
    '        \'"yes" or "no".\'\n',
    '    )\n',
    '\n',
    '    def __init__(self, model_name, device=\'cuda\', dtype=torch.float16):\n',
    '        self.tokenizer = AutoTokenizer.from_pretrained(\n',
    '            model_name, padding_side=\'left\', trust_remote_code=True,\n',
    '        )\n',
    '        if self.tokenizer.pad_token is None:\n',
    '            self.tokenizer.pad_token = self.tokenizer.eos_token\n',
    '        self.model = AutoModelForCausalLM.from_pretrained(\n',
    '            model_name, torch_dtype=dtype, trust_remote_code=True,\n',
    '        ).to(device).eval()\n',
    '        self.device = device\n',
    '        self.yes_id = self.tokenizer.convert_tokens_to_ids(\'yes\')\n',
    '        self.no_id = self.tokenizer.convert_tokens_to_ids(\'no\')\n',
    '\n',
    '    def _format_pair(self, instruction, query, document):\n',
    '        return (\n',
    '            f\'<|im_start|>system\\n{self.SYSTEM_PROMPT}<|im_end|>\\n\'\n',
    '            f\'<|im_start|>user\\n\'\n',
    '            f\'<Instruct>: {instruction}\\n\'\n',
    '            f\'<Query>: {query}\\n\'\n',
    '            f\'<Document>: {document}\\n\'\n',
    '            f\'<|im_end|>\\n\'\n',
    '            f\'<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n\'\n',
    '        )\n',
    '\n',
    '    @torch.no_grad()\n',
    '    def predict(self, pairs, batch_size=8, instruction=None, show_progress_bar=False):\n',
    '        """Score query-document pairs. Returns list of relevance scores (0-1)."""\n',
    '        if instruction is None:\n',
    '            instruction = RERANKER_TASK_INSTRUCTION\n',
    '        all_scores = []\n',
    '        for start in range(0, len(pairs), batch_size):\n',
    '            batch = pairs[start:start + batch_size]\n',
    '            prompts = [\n',
    '                self._format_pair(instruction, q, d[:TEXT_TRUNCATE])\n',
    '                for q, d in batch\n',
    '            ]\n',
    '            inputs = self.tokenizer(\n',
    '                prompts, padding=True, truncation=True,\n',
    '                max_length=4096, return_tensors=\'pt\',\n',
    '            ).to(self.device)\n',
    '            logits = self.model(**inputs).logits[:, -1, :]\n',
    '            yes_no = torch.stack(\n',
    '                [logits[:, self.no_id], logits[:, self.yes_id]], dim=1\n',
    '            )\n',
    '            probs = F.softmax(yes_no, dim=1)\n',
    '            scores = probs[:, 1].cpu().numpy()  # P(yes)\n',
    '            all_scores.extend(scores.tolist())\n',
    '        return all_scores\n',
    '\n',
    '\n',
    '# ---- Load reranker ----\n',
    '_reranker = None\n',
    'if CONFIG["rerank_enabled"]:\n',
    '    try:\n',
    '        print(f"Loading reranker: {CONFIG[\'rerank_model\']} (Qwen3 generative yes/no)...")\n',
    '        _reranker = Qwen3Reranker(CONFIG["rerank_model"], device="cuda:1")\n',
    '        print(f"  Reranker loaded on cuda:1 (P(yes) scoring)")\n',
    '    except Exception as e:\n',
    '        print(f"  \\u26a0\\ufe0f Reranker failed to load: {e}")\n',
    '        _reranker = None\n',
    '        print(f"  Continuing WITHOUT reranker (FAISS-only retrieval)")\n',
    'else:\n',
    '    print("  Reranker: DISABLED")\n',
    '\n',
    'print(f"  Embedding model: {CONFIG[\'embed_model\']} ({dim}d, fp16)")\n',
    'print(f"  Document prompts: law-specific + court-specific")\n',
    'print(f"\\nCorpus FAISS: laws={faiss_law_index.ntotal:,}, courts={faiss_court_index.ntotal:,} vectors ({dim}d)")\n',
    '_save_checkpoint(FAISS_LAWS_PATH, FAISS_COURTS_PATH)\n',
]

cell['source'] = good_prefix + correct_suffix

# Verify
new_src = ''.join(cell['source'])
assert 'class Qwen3Reranker:' in new_src
assert 'def __init__(self, model_name' in new_src
assert 'def predict(self, pairs' in new_src
assert '_reranker = Qwen3Reranker' in new_src
# No interleaved garbage
assert 'def __init__(self, model_name, device=\'cuda\', dtype=torch.float16):print' not in new_src

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("SUCCESS: Qwen3Reranker cell fixed (lines 69+ rewritten)")
