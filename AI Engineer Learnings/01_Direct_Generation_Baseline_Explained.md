# 01: Direct Generation Baseline — Cell-by-Cell Breakdown

> **Notebook:** `01_direct_generation_baseline.ipynb`  
> **Architecture:** Prompt an LLM to directly generate legal citations (no retrieval)  
> **Result:** This is the simplest possible approach — and it fails badly. Understanding WHY it fails teaches you when RAG is necessary.

---

## The Big Picture

```
┌────────────────────────────────────────────────┐
│  English Legal Question                         │
│  "What are the requirements for a valid         │
│   contract under Swiss law?"                    │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  LLM (Mistral-7B)                              │
│  Prompt: "Generate Swiss legal citations..."    │
│                                                │
│  Output: ["Art. 1 OR", "Art. 11 OR", ...]      │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  Regex Parser                                   │
│  Extract structured citations from raw text     │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  Output: submission.csv                         │
│  query_id, predicted_citations                  │
└────────────────────────────────────────────────┘
```

**Why this approach exists:** It establishes a baseline. Every RAG system should be compared against "just ask the LLM directly." If your complex RAG pipeline doesn't beat this, your retrieval is broken.

---

## Cell 1: Markdown Header

```markdown
# Direct Generation Baseline for Omnilex Legal Retrieval
```

**Purpose:** Documents the notebook's approach. Always start notebooks with a clear description of what it does and what it needs.

**Interview Insight:** In production ML, documentation in notebooks is crucial. Reviewers should understand the approach without reading code.

---

## Cell 2: Setup & Configuration

```python
import os
import sys
from pathlib import Path

# === CONFIGURATION ===
DATASET_MODE = "val"  # "val" or "test"

# Detect environment
KAGGLE_ENV = "KAGGLE_KERNEL_RUN_TYPE" in os.environ

if KAGGLE_ENV:
    DATA_PATH = Path("/kaggle/input/omnilex-data")
    MODEL_PATH = Path("/kaggle/input/llama-model")
    OUTPUT_PATH = Path("/kaggle/working")
else:
    REPO_ROOT = Path(".").resolve().parent
    DATA_PATH = REPO_ROOT / "data"
    MODEL_PATH = REPO_ROOT / "models"
    OUTPUT_PATH = REPO_ROOT / "output"
```

### Concepts Explained

**1. Environment Detection**
```python
KAGGLE_ENV = "KAGGLE_KERNEL_RUN_TYPE" in os.environ
```
- Kaggle sets this environment variable when running on their platform
- This pattern lets the same notebook run locally AND on Kaggle without changes
- **Interview Q:** "How do you handle different deployment environments?"  
  **A:** "Environment detection via env vars, with path configuration per environment."

**2. `pathlib.Path` vs string paths**
```python
DATA_PATH = Path("/kaggle/input/omnilex-data")
```
- `Path` objects handle OS differences (Windows `\` vs Linux `/`) automatically
- Support operations like `path / "subdir" / "file.csv"` (clean concatenation)
- **Always use `pathlib`** in modern Python — interviewers notice string path manipulation as a red flag

**3. Dual-mode configuration (val vs test)**
```python
DATASET_MODE = "val"
IS_VALIDATION_MODE = DATASET_MODE == "val"
```
- During development: run on validation set (has gold labels for scoring)
- For submission: switch to test set
- **Pattern:** Never hardcode "test.csv" everywhere. Use a single config variable.

---

## Cell 3: Model Configuration

```python
CONFIG = {
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "n_ctx": 4096,
    "n_threads": 4,
    "n_gpu_layers": -1,
    "max_tokens": 512,
    "temperature": 0.0,
}
```

### Concepts Explained

**1. GGUF Format**
- GGUF = binary format for quantized LLMs, used by `llama.cpp`
- `Q4_K_M` = 4-bit quantization with K-means, medium quality
- **Why quantize?** Mistral-7B at full precision = 14GB. At Q4 = ~4GB. Fits on Kaggle T4 (16GB VRAM)
- **Interview Q:** "What's the tradeoff of quantization?"  
  **A:** "Reduces memory 3-4× at the cost of ~2-5% quality degradation. Q4_K_M is the sweet spot for 7B models."

**2. `n_ctx`: Context Window**
```python
"n_ctx": 4096
```
- Maximum number of tokens the model can process in one call (input + output combined)
- Mistral-7B supports up to 32768, but 4096 is conservative for a simple generation task
- **Rule of thumb:** Set n_ctx to the minimum you need. Larger = more VRAM.

**3. `n_gpu_layers`: GPU Offloading**
```python
"n_gpu_layers": -1  # -1 = offload ALL layers to GPU
```
- LLMs have many transformer layers (Mistral-7B has 32)
- Each layer can be on CPU or GPU independently
- `-1` = put everything on GPU (fastest, but needs VRAM)
- `0` = pure CPU (slow, ~10× slower than GPU)
- `20` = first 20 layers on GPU, rest on CPU (partial offload)

**4. `max_tokens`: Output Length Limit**
```python
"max_tokens": 512
```
- The maximum number of tokens the model is allowed to **generate** (output only — doesn't count the prompt)
- This is SEPARATE from `n_ctx`. Think of it this way:
  ```
  n_ctx = 4096          ← total window (input + output combined)
  prompt = ~800 tokens  ← your question + system prompt
  max_tokens = 512      ← cap on how much the model can write back
  actual limit = min(max_tokens, n_ctx - prompt_length) = min(512, 3296) = 512
  ```
- **Too low (e.g., 128):** Output gets truncated mid-sentence → broken JSON, incomplete citation lists
- **Too high (e.g., 4096):** Model wastes time generating padding/repetition after it's done
- **512 for this task:** Enough for ~15-20 citations in list format. A single citation like `"Art. 221 Abs. 1 StPO"` ≈ 10-12 tokens.
- **What happens when you hit the limit:** Generation stops abruptly. If the model was mid-word, you get garbage: `["Art. 221 Abs. 1 StPO", "Art. 22` ← truncated, unparseable
- **Interview Q:** "What's the difference between `n_ctx` and `max_tokens`?"  
  **A:** "`n_ctx` is the total context window (input + output). `max_tokens` caps only the output. The input consumes `n_ctx - max_tokens` worth of space. If your prompt is 3000 tokens and n_ctx is 4096, you have at most 1096 tokens for output regardless of what max_tokens says."

**5. `temperature`: Randomness Control**
```python
"temperature": 0.0  # Deterministic output
```
- `temperature=0.0` → always pick the highest-probability token (greedy decoding)
- `temperature=0.7` → introduce randomness (creative writing)
- `temperature=1.0` → raw probability distribution
- **For retrieval/factual tasks:** Always use 0.0 or very low (0.1). You want consistency, not creativity.

**Interview Q:** "When would you use temperature > 0?"  
**A:** "Creative tasks (story writing, brainstorming), data augmentation, or when you want diverse outputs from the same prompt. Never for factual extraction."

---

## Cell 4: Load the LLM

```python
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

llm = None

if LLAMA_AVAILABLE:
    model_file = MODEL_PATH / CONFIG["model_file"]
    if not model_file.exists():
        gguf_files = list(MODEL_PATH.glob("*.gguf"))
        if gguf_files:
            model_file = gguf_files[0]

    if model_file and model_file.exists():
        llm = Llama(
            model_path=str(model_file),
            n_ctx=CONFIG["n_ctx"],
            n_threads=CONFIG["n_threads"],
            n_gpu_layers=CONFIG["n_gpu_layers"],
            verbose=False,
        )
```

### Concepts Explained

**1. Graceful Degradation Pattern**
```python
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
```
- If the library isn't installed, notebook still runs (in mock mode)
- **Why this matters:** Kaggle environments may not have your library. Always handle missing dependencies gracefully.
- **Pattern name:** "Graceful degradation" — the system works at reduced capacity rather than crashing.

**2. File Discovery with `glob`**
```python
gguf_files = list(MODEL_PATH.glob("*.gguf"))
```
- Instead of hardcoding a filename, search for any matching file
- **Why:** Model filenames change between versions. Auto-discovery is more robust.
- `*.gguf` = any file ending in `.gguf`
- `**/*.gguf` = recursive (searches subdirectories too)

**3. `llama-cpp-python` — The Inference Engine**
```python
llm = Llama(model_path=str(model_file), ...)
```
- This is a Python binding for `llama.cpp` (C++ inference engine)
- Supports GGUF quantized models
- Runs on CPU + GPU (via CUDA, Metal, or Vulkan)
- **Alternative:** `transformers` library (HuggingFace) — more features but slower for local inference
- **Interview Q:** "Why use llama.cpp instead of HuggingFace transformers?"  
  **A:** "llama.cpp is optimized for inference speed with quantized models. Transformers is better for fine-tuning and full-precision models."

---

## Cell 5: The Prompt (Most Important Cell)

```python
SYSTEM_PROMPT = """You are a Swiss legal citation expert. Output ONLY a Python list of citations.

CITATION FORMATS:
- Federal laws: "Art. X ABBREV" where ABBREV is ZGB, OR, StGB, BV, etc.
- Court decisions: "BGE X Y Z" or "BGE X Y Z E. N" with consideration number

OUTPUT FORMAT: Python list like ["citation1", "citation2", ...]

EXAMPLES:
Query: What are the requirements for a valid contract under Swiss law?
["Art. 1 OR", "Art. 11 OR", "Art. 12 OR", "BGE 119 II 449 E. 2"]
...
"""
```

### Concepts Explained

**1. Prompt Engineering — Few-Shot Prompting**
- The prompt gives 5 complete examples (query → expected output)
- This is "5-shot prompting" — the LLM learns the output format from examples
- **0-shot:** No examples (just instructions)
- **1-shot:** One example
- **Few-shot (3-5):** Multiple examples — best for format adherence

**Interview Q:** "How many shots do you need?"  
**A:** "For format compliance (JSON, lists), 2-3 shots usually suffice. For domain knowledge (knowing correct citations), few-shot can't help — the model either has the knowledge or it doesn't."

**2. Structured Output Format**
```
OUTPUT FORMAT: Python list like ["citation1", "citation2", ...]
```
- Forces the LLM to output parseable format (Python list)
- **Why Python list?** Easy to parse with `ast.literal_eval()`
- **Alternative:** JSON format (more standard in production)
- **Better alternative:** GBNF grammar (forces valid syntax at token level — used in later notebooks)

**3. Citation Format Specification**
```
- Federal laws: "Art. X ABBREV"
- Court decisions: "BGE X Y Z E. N"
```
- Tells the model EXACTLY what format to use
- Without this, LLM might output: "Article 1 of the Swiss Code of Obligations" (unparseable)
- **Lesson:** Be hyper-specific about output format. LLMs follow instructions literally.

**4. The Regex Parser — `extract_citations()`**

```python
# BGE pattern: BGE 141 II 345 E. 3.2
bge_pattern = r'BGE\s+(\d+)\s+([IVX]+[a-z]?)\s+(\d+)(?:\s+E\.\s*([\d.a-z/]+))?'

# Article pattern: Art. 221 Abs. 1 StPO
art_pattern = rf'Art\.?\s*(\d+[a-z]?)(?:\s+(Abs\.?\s*\d+))?...\s+({LAW_ABBREVS})\b'
```

**Why regex extraction is needed:**
- Even with clear prompts, LLMs don't always output perfect format
- Model might write: `"Art 221 Abs1 StPO"` instead of `"Art. 221 Abs. 1 StPO"`
- Regex normalizes these variations into canonical form
- **This is defensive programming** — never trust LLM output format

**Regex breakdown (BGE pattern):**
```
BGE           → literal text "BGE"
\s+           → one or more whitespace characters
(\d+)         → capture group: volume number (e.g., "141")
\s+           → whitespace
([IVX]+[a-z]?)→ capture group: roman numeral part (e.g., "II", "IVa")
\s+           → whitespace
(\d+)         → capture group: page number (e.g., "345")
(?:...)? → optional group: consideration number
  E\.\s*      → literal "E." + optional space
  ([\d.a-z/]+)→ capture: "3.2" or "2a" or "1/2"
```

**Interview Q:** "How do you handle unstructured LLM output?"  
**A:** "Layer 1: Constrain output format via prompt engineering. Layer 2: Parse with regex for normalization. Layer 3: Validate against known schema (reject invalid citations). In production, use grammar-constrained decoding (GBNF) to eliminate invalid output at generation time."

**5. The `generate_citations()` Function**

```python
def generate_citations(query: str) -> list[str]:
    prompt = f"[INST] {SYSTEM_PROMPT}\n\nQuery: {query} [/INST]"
    
    response = llm(
        prompt,
        max_tokens=CONFIG["max_tokens"],
        temperature=CONFIG["temperature"],
        stop=["[INST]", "</s>", "Query:", "\n\n"],
    )
    
    raw_output = response["choices"][0]["text"].strip()
```

**Key details:**

**a) Instruction Format `[INST]...[/INST]`**
- Mistral-7B-Instruct uses this specific chat template
- `[INST]` = start of user instruction
- `[/INST]` = end of instruction → model starts generating
- **Every instruct model has a different template.** Using the wrong one = garbage output.
- Llama uses `<s>[INST]`, ChatGPT uses `{"role": "user"}`, etc.

**b) Stop Tokens**
```python
stop=["[INST]", "</s>", "Query:", "\n\n"]
```
- Tell the model to STOP generating when it produces any of these strings
- Without stop tokens, model might continue generating more examples, explanations, etc.
- `</s>` = end-of-sequence token (model's natural stop)
- `"Query:"` = prevent model from generating another example

**c) Response Structure**
```python
response["choices"][0]["text"]
```
- llama.cpp returns OpenAI-compatible response format
- `choices` = list of generated completions (usually 1)
- `[0]["text"]` = the actual generated text
- **This mirrors the OpenAI API format** — important for production portability

---

## Cell 6: Test Generation

```python
test_query = "What are the requirements for a valid contract under Swiss law?"
raw_citations = generate_citations(test_query)
```

**Purpose:** Sanity check — verify the model produces parseable output before running on all queries.

**Best Practice:** Always test on a single example before batch processing. This catches:
- Prompt format issues (wrong template)
- Parsing failures (regex doesn't match output)
- Model loading issues (wrong quantization, insufficient VRAM)

---

## Cell 7: Load Test Data

```python
import pandas as pd
test_df = pd.read_csv(QUERY_FILE)
```

**Simple but important:**
- Loads the competition's query file (10 validation queries or 40 test queries)
- Checks for `gold_citations` column (only present in validation mode)
- **Interview Q:** "How do you handle train/val/test splits in competitions?"  
  **A:** "Develop on validation set (has labels), submit on test set (no labels). Never look at test labels."

---

## Cell 8: Batch Generation

```python
for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
    query_id = row["query_id"]
    query_text = row["query"]
    raw_citations = generate_citations(query_text)
    predicted = ";".join(raw_citations) if raw_citations else " "
    predictions.append({"query_id": query_id, "predicted_citations": predicted})
```

### Concepts Explained

**1. `tqdm` — Progress Bars**
```python
from tqdm.notebook import tqdm
for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
```
- Shows progress (essential for long-running LLM generation)
- `total=len(test_df)` → accurate ETA estimation
- `.notebook` variant renders nicely in Jupyter

**2. Citation Joining Format**
```python
predicted = ";".join(raw_citations) if raw_citations else " "
```
- Competition expects citations separated by `;`
- Empty predictions = single space `" "` (competition's format requirement)
- **This is competition-specific** — always read submission format carefully

---

## Cell 9: Save Submission

```python
submission_path = OUTPUT_PATH / "submission.csv"
predictions_df.to_csv(submission_path, index=False)
```

- Standard CSV output: `query_id,predicted_citations`
- `index=False` → don't write row numbers (competition doesn't want them)

---

## Why This Approach FAILS (The Key Learning)

| Problem | Why | Impact |
|---------|-----|--------|
| **Hallucination** | LLM generates citations from training data that may not exist | ~60% of generated citations are wrong |
| **No grounding** | Model never sees the actual legal documents | Can't find articles it wasn't trained on |
| **No retrieval** | Relies entirely on parametric knowledge | Misses recent decisions, obscure articles |
| **Format errors** | Despite regex, some outputs are unparseable | Lost citations = lost recall |
| **Language gap** | Question in English, legal knowledge in German/French | Model conflates similar concepts |

**The fundamental lesson:**
> **Direct generation = hallucination.** For factual tasks (legal, medical, technical), you MUST ground the model's output in retrieved documents. This is WHY RAG exists.

---

## Interview Questions This Notebook Prepares You For

1. **"What's the simplest baseline for a retrieval task?"**  
   → Direct generation. Ask the LLM to produce answers from parametric knowledge. This establishes the lower bound.

2. **"Why can't you just use an LLM without retrieval?"**  
   → Hallucination. The model generates plausible-looking citations that don't exist. In legal/medical domains, this is unacceptable.

3. **"How do you handle structured output from an LLM?"**  
   → Three layers: (1) Prompt engineering for format, (2) Regex parsing for normalization, (3) Grammar constraints (GBNF) for guaranteed validity.

4. **"What's the purpose of temperature=0?"**  
   → Deterministic output. For factual tasks, we want the single most likely answer, not creative diversity.

5. **"How do you make code work across environments (local vs cloud)?"**  
   → Environment detection via env vars + path configuration per environment.

6. **"What's quantization and when do you use it?"**  
   → Reduces model size 3-4× (FP16 → Q4) at ~2-5% quality cost. Essential for fitting large models on consumer GPUs or Kaggle T4s.

7. **"What's the difference between llama.cpp and HuggingFace transformers?"**  
   → llama.cpp: optimized C++ inference engine for GGUF quantized models. Transformers: full Python ecosystem for training + inference at full precision. Use llama.cpp for deployment speed, transformers for research flexibility.

---

## Key Takeaways

| # | Principle | Applied Here |
|---|-----------|-------------|
| 1 | Always start with the simplest baseline | Direct generation = simplest possible approach |
| 2 | Never trust LLM output format | Regex parser handles format variations |
| 3 | Use temperature=0 for factual tasks | Prevents hallucination variance |
| 4 | Environment-agnostic code | Kaggle/local detection pattern |
| 5 | Test on single example before batch | Cell 6 validates before Cell 8 runs all queries |
| 6 | Graceful degradation | Mock mode if library unavailable |
| 7 | This approach has a ceiling | Without retrieval, you can't exceed LLM's training knowledge |

---

## What Comes Next

This notebook proves that direct generation isn't enough. The next notebook (`02_agentic_retrieval_baseline.ipynb`) adds **retrieval** — the model searches actual legal documents before generating citations. This is the foundation of RAG (Retrieval-Augmented Generation).

The progression:
```
01: Generate from memory (this notebook) → fails (hallucination)
02: Search then generate (basic RAG) → better but limited
03: HyDE + iterative search (advanced RAG) → ceiling hit by embedding quality
04: Planner decomposition (agentic RAG) → best results but fragile
```
