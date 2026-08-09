# 03: HyDE + Hybrid Retrieval (Kaggle Version) — Cell-by-Cell Breakdown

> **Notebook:** `03_hyde_kaggle.ipynb` (latest version, May 31 2026)  
> **Architecture:** HyDE + FAISS Embeddings + BM25 + RRF Fusion + GBNF-Constrained ReAct Agent  
> **Results:** Run 3 = F1 0.034, Run 4 = F1 0.040 (10 validation queries)  
> **Key Advance over Notebook 02:** Adds semantic search (embeddings), hypothetical document generation (HyDE), and grammar-constrained JSON output

---

## The Evolution: What Changed from Notebook 02

| Feature | Notebook 02 | Notebook 03 |
|---------|-------------|-------------|
| **Search** | BM25 only (keyword) | FAISS (semantic) + BM25 (keyword) + RRF fusion |
| **Embeddings** | None | Qwen3-Embedding-0.6B (1024d) |
| **Query Enhancement** | None | HyDE (generate hypothetical German doc first) |
| **Agent Output** | Free-text parsing with regex | GBNF grammar → guaranteed valid JSON |
| **Validation** | Regex action parsing (fragile) | Pydantic model (type-safe) |
| **PRF** | None | Pseudo-Relevance Feedback (initial results → HyDE context) |
| **Reranker** | None | Qwen3-Reranker-0.6B (attempted, broken) |
| **Context for Agent** | Full search results (truncated) | Compact summary (citations only) |

---

## Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    NOTEBOOK 03: COMPLETE PIPELINE                                 │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         OFFLINE (once at startup)                        │    │
│  │                                                                         │    │
│  │   laws_de.csv ──┐                                                       │    │
│  │   (175K docs)   ├──▶ Qwen3-Embedding ──▶ FAISS Index (175K × 1024d)   │    │
│  │                 │    (GPU 1, fp16)      + BM25 Index (tokenized)        │    │
│  │                 │                                                       │    │
│  │   courts.csv ───┘                                                       │    │
│  │   (200K sample)  ──▶ Qwen3-Embedding ──▶ FAISS Index (200K × 1024d)   │    │
│  │                      (GPU 1, fp16)      + BM25 Index (tokenized)        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    ONLINE (per query, ~15-30 seconds)                    │    │
│  │                                                                         │    │
│  │  English Query                                                          │    │
│  │       │                                                                 │    │
│  │       ▼                                                                 │    │
│  │  ┌──────────────────────────────────────────────────────────┐          │    │
│  │  │ STEP 1: REGEX EXTRACTION                                  │          │    │
│  │  │ If query mentions "Art. 221 StPO" → directly add to output│          │    │
│  │  └───────────────────────┬──────────────────────────────────┘          │    │
│  │                          │                                              │    │
│  │                          ▼                                              │    │
│  │  ┌──────────────────────────────────────────────────────────┐          │    │
│  │  │ STEP 2: ReAct AGENT LOOP (5 iterations, GBNF grammar)    │          │    │
│  │  │                                                           │          │    │
│  │  │  For each iteration:                                      │          │    │
│  │  │   1. LLM generates JSON: {thought, action, query}         │          │    │
│  │  │   2. Grammar FORCES valid JSON (can't hallucinate format) │          │    │
│  │  │   3. Pydantic validates action ∈ {search_laws, courts, done}│        │    │
│  │  │   4. Execute hybrid search:                               │          │    │
│  │  │                                                           │          │    │
│  │  │      German query                                         │          │    │
│  │  │         │                                                 │          │    │
│  │  │         ├──▶ PRF: Raw FAISS search → top 5 results       │          │    │
│  │  │         │         (used as context for HyDE)              │          │    │
│  │  │         │                                                 │          │    │
│  │  │         ├──▶ HyDE: LLM generates hypothetical German doc  │          │    │
│  │  │         │         using PRF snippets as grounding         │          │    │
│  │  │         │                                                 │          │    │
│  │  │         ├──▶ FAISS search (query embedding)     ──┐      │          │    │
│  │  │         ├──▶ FAISS search (HyDE doc embedding)  ──┼─RRF──▶ Merged  │    │
│  │  │         └──▶ BM25 search (keyword matching)     ──┘      │  results │    │
│  │  │                                                           │          │    │
│  │  │   5. Add compact observation to history                   │          │    │
│  │  │   6. Guardrails: skip duplicate queries, force alternation│          │    │
│  │  │                                                           │          │    │
│  │  └───────────────────────┬──────────────────────────────────┘          │    │
│  │                          │                                              │    │
│  │                          ▼                                              │    │
│  │  ┌──────────────────────────────────────────────────────────┐          │    │
│  │  │ STEP 3: COLLECT & DEDUPLICATE                             │          │    │
│  │  │ All citations from all iterations → dedupe → output       │          │    │
│  │  └──────────────────────────────────────────────────────────┘          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  OUTPUT: "Art. 221 Abs. 1 StPO;BGE 137 IV 122;Art. 227 Abs. 1 StPO;..."       │
└─────────────────────────────────────────────────────────────────────────────────┘


TECHNOLOGY STACK:
═════════════════
┌───────────────────┬──────────────────────────────────────────────────────────┐
│ Component          │ Technology                                                │
├───────────────────┼──────────────────────────────────────────────────────────┤
│ LLM (reasoning)   │ Mistral-7B-Instruct-v0.2 Q4_K_M on GPU 0               │
│ Embeddings        │ Qwen3-Embedding-0.6B (1024d, fp16) on GPU 1             │
│ Reranker          │ Qwen3-Reranker-0.6B on GPU 1 (BROKEN — disabled)        │
│ Dense search      │ FAISS IndexFlatIP (inner product, normalized = cosine)   │
│ Sparse search     │ BM25Okapi (rank_bm25 library)                            │
│ Fusion            │ Reciprocal Rank Fusion (k=60)                            │
│ Agent format      │ GBNF grammar → guaranteed JSON                           │
│ Agent validation  │ Pydantic BaseModel (type checking)                       │
│ Query enhancement │ HyDE (hypothetical document generation)                  │
│ PRF               │ Top-5 initial FAISS results as HyDE context              │
│ Platform          │ Kaggle T4×2 GPUs, 30GB RAM, 12hr limit                  │
└───────────────────┴──────────────────────────────────────────────────────────┘
```

---

## Cell-by-Cell Walkthrough

### Cell 1: Markdown Header
Title and Kaggle setup instructions.

### Cell 2: Install Dependencies
```python
!pip install rank-bm25 sentence-transformers faiss-cpu --quiet
!CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --prefer-binary \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
```

**New vs Notebook 02:** Adds `sentence-transformers` (for Qwen3-Embedding) and `faiss-cpu`.

**Interview Q:** "Why `faiss-cpu` instead of `faiss-gpu`?"  
**A:** "FAISS CPU is sufficient for index sizes under 1M vectors. GPU FAISS helps for billion-scale indices. Our 175K laws + 200K courts = 375K vectors — CPU search is <50ms. The GPU is reserved for LLM and embedding model."

---

### Cell 6: Configuration (KEY — all architectural decisions here)

```python
CONFIG = {
    # LLM (GPU 0)
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "n_ctx": 8192,
    "n_gpu_layers": -1,
    
    # Agent
    "max_iterations": 5,            # Up from 3 in nb02!
    "max_tokens": 512,
    "temperature": 0.1,
    "max_observation_chars": 1200,
    "max_conversation_chars": 28000,
    
    # Retrieval
    "top_k_laws": 50,               # Up from 40 in nb02
    "top_k_courts": 50,
    
    # HyDE (NEW)
    "hyde_max_tokens": 300,
    "hyde_temperature": 0.3,
    "hyde_target_chars_law": 500,
    "hyde_target_chars_court": 600,
    "hyde_enabled": True,
    "prf_top_k": 5,                 # Top-5 initial results as HyDE context
    
    # Embeddings (NEW)
    "embed_model": "Qwen/Qwen3-Embedding-0.6B",
    "embed_dim": 1024,
    "embed_max_length": 1024,
    
    # Instruction prompts for embedding (NEW)
    "prompt_doc_law": "Instruct: Represent this Swiss federal statute...",
    "prompt_query_law": "Instruct: Given German legal search terms, retrieve...",
    "prompt_hyde_law": "Instruct: Given a hypothetical Swiss legal text...",
    
    # Reranker (NEW but BROKEN)
    "rerank_model": "Qwen/Qwen3-Reranker-0.6B",
    "rerank_enabled": True,
    "rerank_per_search": False,     # DISABLED — destroys RRF results
}
```

### New Concepts Introduced

**1. Instruction-Tuned Embeddings**
```python
"prompt_doc_law": "Instruct: Represent this Swiss federal statute article..."
"prompt_query_law": "Instruct: Given German legal search terms, retrieve..."
```
- Qwen3-Embedding uses different prompts for documents vs queries
- Document prompt: "Represent this text for retrieval"
- Query prompt: "Find documents matching this query"
- **Why different?** Asymmetric retrieval — queries are short, documents are long. The model needs to know which "side" it's encoding.
- **Interview Q:** "What are instruction-tuned embeddings?"  
  **A:** "Models like Qwen3-Embedding and E5 accept an instruction prefix that tells them HOW to encode. For retrieval, you use different instructions for documents vs queries, creating an asymmetric embedding space where queries naturally land near their relevant documents."

**2. HyDE Parameters**
```python
"hyde_temperature": 0.3,      # More creative than agent (0.1)
"hyde_target_chars_law": 500, # Target length for generated hypothetical doc
```
- HyDE generates CREATIVE text (hypothetical articles) → temperature=0.3
- Agent needs PRECISION (exact tool calls) → temperature=0.1
- **Different temperatures for different purposes** is a production pattern

**3. PRF (Pseudo-Relevance Feedback)**
```python
"prf_top_k": 5,  # Top-5 initial results used as HyDE context
```
- Before HyDE generates a hypothetical doc, it first does a raw search
- Top-5 results from that raw search become CONTEXT for HyDE generation
- **Why?** Grounds HyDE in real corpus vocabulary instead of hallucinating disconnected text
- **Pattern name:** "PRF → HyDE" — use initial retrieval to improve query expansion

---

### Cell 11: FAISS Semantic Search + Qwen3 Embedding

```python
_st_model = SentenceTransformer(
    "Qwen/Qwen3-Embedding-0.6B",
    device="cuda:1",              # Separate GPU from LLM!
    trust_remote_code=True,
    model_kwargs={"torch_dtype": torch.float16},  # fp16 = half VRAM
)

def embed_corpus(documents, doc_type="law", batch_size=8):
    texts = [f"{d['citation']}: {d['text'][:1500]}" for d in documents]
    prompt = CONFIG["prompt_doc_law"] if doc_type == "law" else CONFIG["prompt_doc_court"]
    embeddings = _st_model.encode(texts, prompt=prompt, normalize_embeddings=True)
    return embeddings
```

**Key Concepts:**

**1. GPU Memory Management — Two Models on Two GPUs**
```
GPU 0: Mistral-7B LLM (~4GB VRAM)     — for reasoning + HyDE generation
GPU 1: Qwen3-Embedding (~0.6GB VRAM)  — for embedding queries/documents
```
- Kaggle T4×2 gives you 2 GPUs with 16GB each
- Putting both on GPU 0 would cause OOM (out of memory)
- **Pattern:** Assign models to specific GPUs via `device="cuda:0"` / `device="cuda:1"`

**2. fp16 (Half Precision)**
```python
model_kwargs={"torch_dtype": torch.float16}
```
- Full precision (fp32): each parameter = 4 bytes
- Half precision (fp16): each parameter = 2 bytes → **50% VRAM savings**
- Quality loss: negligible for embeddings (they're normalized anyway)
- **Interview Q:** "When is fp16 safe to use?"  
  **A:** "Almost always safe for inference. Risky for training (gradient underflow). For embeddings that get L2-normalized, fp16 is lossless in practice."

**3. Normalized Embeddings = Cosine Similarity via Inner Product**
```python
embeddings = _st_model.encode(..., normalize_embeddings=True)
faiss_index = faiss.IndexFlatIP(dim)  # Inner Product
```
- When vectors are unit-length (normalized), inner product = cosine similarity
- `IndexFlatIP` (Inner Product) is faster than computing cosine directly
- **Math:** If ||a|| = ||b|| = 1, then a·b = cos(θ)
- **Why not IndexFlatL2?** L2 distance and cosine similarity are equivalent for normalized vectors, but IP is more intuitive (higher = more similar)

**4. Document Truncation**
```python
texts = [f"{d['citation']}: {d['text'][:1500]}" for d in documents]
```
- Each document text is truncated to 1500 chars before embedding
- Qwen3's max_seq_length = 1024 tokens ≈ 2800 chars German text
- 1500 chars safely fits within the token limit
- **Tradeoff:** Longer = more semantic info but slower; 1500 is the sweet spot

---

### Cell 12: BM25 Keyword Index

```python
def _tokenize_german(text):
    text = text.lower()
    tokens = re.findall(r'[a-zäöüß\d]+', text)
    return [t for t in tokens if len(t) > 2]  # Remove short words
```

**Improvement over Notebook 02:**
- Keeps German umlauts (ä, ö, ü, ß) as valid characters
- Removes tokens ≤ 2 chars (articles: "zu", "in", "am" → noise for BM25)
- Still naive (no compound splitting) but slightly better

---

### Cell 13: PRF-Based HyDE Generation (The Big Innovation)

```python
def build_hyde_prompt(query, doc_type="law", prf_snippets=None):
    instruction = (
        "Du bist ein Schweizer Rechtsexperte. "
        "Schreibe einen hypothetischen Schweizer Gesetzesartikel auf Deutsch, "
        "der diese Frage beantworten würde."
    )
    
    if prf_snippets:
        instruction += "\n\nReferenztexte aus der Datenbank:\n"
        for snippet in prf_snippets[:3]:
            instruction += f"- {snippet[:200]}\n"
    
    prompt = f"[INST] {instruction}\n\nFrage: {query} [/INST]"
    return prompt
```

### HyDE Explained (Hypothetical Document Embeddings)

**The Problem:**
- Query: "Under what conditions can pre-trial detention be extended?"
- Corpus: "Art. 227 Abs. 1 StPO: Das zuständige Gericht ordnet die Verlängerung..."
- The query (English, abstract) and the document (German, specific) live in different parts of embedding space

**The HyDE Solution:**
1. Ask the LLM to generate a HYPOTHETICAL document that answers the query
2. The hypothetical doc is in German, uses legal language, looks like a real article
3. Embed the HYPOTHETICAL doc instead of the query
4. Search for real documents similar to the hypothetical one

```
Traditional:  English query ──embed──▶ search space ──▶ find German docs (far away)

HyDE:         English query ──LLM──▶ German hypothetical doc ──embed──▶ search space
                                                                          │
                                                              closer to real German docs!
```

**Why it helps:** The hypothetical doc shares vocabulary and structure with real articles → higher cosine similarity → better retrieval

**PRF Enhancement (this notebook's innovation):**
```
Step 1: Raw FAISS search with query → top-5 results (may be noisy)
Step 2: Feed those top-5 as "Referenztexte" into HyDE prompt
Step 3: LLM generates hypothetical doc GROUNDED in real corpus vocabulary
Step 4: Embed hypothetical doc → FAISS search → better results
```

**Interview Q:** "What's the tradeoff of HyDE?"  
**A:** "Pros: bridges the query-document vocabulary gap, especially cross-lingual. Cons: adds ~2-5s per query (LLM generation), can hallucinate irrelevant content if not grounded. PRF mitigates hallucination by grounding in real documents. The cost is 2 FAISS searches per query instead of 1."

---

### Cell 14: Hybrid Search with RRF Fusion

```python
RRF_K = 60

def reciprocal_rank_fusion(rankings, k=RRF_K):
    rrf_scores = {}
    for ranking in rankings:
        for rank, (doc_idx, _score) in enumerate(ranking):
            if doc_idx not in rrf_scores:
                rrf_scores[doc_idx] = 0.0
            rrf_scores[doc_idx] += 1.0 / (k + rank + 1)
    return rrf_scores

def hybrid_search(query, doc_type="law", top_k=50, hyde_doc=None):
    # 1. FAISS search with query embedding
    # 2. FAISS search with HyDE doc embedding (if available)
    # 3. BM25 keyword search
    # 4. RRF fusion of all rankings
    # 5. Return merged top-K
```

**Three Rankings Fused:**
```
Ranking 1: FAISS(query)     → semantic match with original query
Ranking 2: FAISS(hyde_doc)  → semantic match with hypothetical document
Ranking 3: BM25(query)      → exact keyword match

RRF combines them: a document ranked high in ALL THREE is most likely correct
```

**Why 3 is better than 1:**
- FAISS(query) catches semantic meaning but misses exact terms
- FAISS(hyde) bridges the language gap (German hypothetical → German real)
- BM25 catches exact article numbers and legal abbreviations ("StPO", "Abs. 1")
- A document found by all three is almost certainly relevant

---

### Cell 15: GBNF-Constrained ReAct Agent (Most Important Cell)

```python
# GBNF Grammar — forces EXACTLY this JSON structure
_GBNF_LINES = [
    r'root ::= "{" ws "\"thought\"" ws ":" ws string "," ws ...',
    r'action-val ::= "\"search_laws\"" | "\"search_courts\"" | "\"done\""',
    ...
]
AGENT_GRAMMAR = LlamaGrammar.from_string(AGENT_GRAMMAR_STR)

# Pydantic validation
class AgentAction(BaseModel):
    thought: str
    action: Literal["search_laws", "search_courts", "done"]
    query: str = ""
```

### GBNF Grammar — Guaranteed Valid Output (Interview Must-Know)

**The Problem with Notebook 02's approach:**
```
LLM output: "Thought: I think... Action: search_laws Action Input: query here"
Parsing:     regex to extract action/input → FRAGILE (breaks if format varies)
```

**The GBNF Solution:**
```
LLM output: {"thought": "...", "action": "search_laws", "query": "..."}
Parsing:     json.loads() → GUARANTEED valid (grammar prevents invalid tokens)
```

**How GBNF works:**
- At each token generation step, llama.cpp checks which tokens are VALID according to the grammar
- Invalid tokens get probability = 0 (masked out)
- The LLM can ONLY produce output matching the grammar

```
Grammar says: action-val ::= "\"search_laws\"" | "\"search_courts\"" | "\"done\""

This means the LLM can ONLY output one of these 3 strings for the action field.
It physically cannot hallucinate "search_google" or "answer_directly" — those tokens are masked.
```

**Interview Q:** "How do you guarantee structured output from an LLM?"  
**A:** "Three approaches in increasing reliability: (1) Prompt engineering + regex parsing (fragile). (2) JSON mode with retry on parse failure (better). (3) Grammar-constrained decoding (GBNF/CFG) — physically impossible to produce invalid output. I prefer GBNF for tool-use because it's zero-retry and zero-parse-failure."

### Pydantic Validation (Belt AND Suspenders)

```python
class AgentAction(BaseModel):
    thought: str
    action: Literal["search_laws", "search_courts", "done"]
    query: str = ""

    @field_validator("query")
    @classmethod
    def clean_query(cls, v):
        # Strip article numbers (confuse embeddings)
        v = re.sub(r"Art\.?\s*\d+\s*(Abs\.?\s*\d+)?", "", v).strip()
        return v[:500]  # Soft truncate
```

**Why both GBNF AND Pydantic?**
- GBNF guarantees JSON structure (syntax)
- Pydantic validates field values (semantics): action must be one of 3 values
- Pydantic also TRANSFORMS: strips article numbers from queries, truncates length
- **Pattern:** Grammar for structure, validators for content

### Agent Loop Guardrails

```python
# Guardrail 1: Skip duplicate queries
if action.query in _seen_queries:
    continue  # Don't search the same thing twice

# Guardrail 2: Force tool alternation
if len(_last_tools) >= 2 and _last_tools[-1] == _last_tools[-2] == action.action:
    # If last 2 searches were same tool, force the other one
    action.action = "search_courts" if action.action == "search_laws" else "search_laws"

# Guardrail 3: Minimum search count before "done"
if action.action == "done" and searches_done < 4:
    action.action = "search_courts" if law_searches > court_searches else "search_laws"
```

**Why guardrails?**
- Without them, the 7B model often: repeats the same query 3 times, uses only search_laws (ignores courts), says "done" after 1 search
- Guardrails enforce diversity and minimum coverage
- **Pattern:** Don't trust LLM judgment for operational decisions. Use rules for what MUST happen, LLM for what to search.

### Compact Observation Format (Key Difference from Notebook 02)

```python
def format_observation(tool_name, results, top_n=5):
    """[search_laws: 50 results. Top 5: "Art. 221 StPO", "Art. 227 StPO", ...]"""
    top_citations = [r["citation"][:40] for r in results[:top_n]]
    return f"[{tool_name}: {count} results. Top {top_n}: {cit_str}]"
```

**Notebook 02:** Showed full text excerpts (300 chars each, 5 results = 1500 chars)  
**Notebook 03:** Shows only citation names (5 citations × 40 chars = 200 chars)

**Why?** Agent doesn't need to READ the documents — it just needs to know what was found so it can decide what to search NEXT. The actual citation extraction happens from the full results separately.

---

## Context Window Budget (Notebook 03 vs 02)

```
NOTEBOOK 02:                              NOTEBOOK 03:
n_ctx = 8192                              n_ctx = 8192
max_iterations = 3                        max_iterations = 5
observation = 1200 chars (full text)      observation = ~200 chars (citations only)

Budget per iteration:                     Budget per iteration:
  Response: ~400 tokens                     Response: ~100 tokens (JSON is compact)
  Observation: ~350 tokens                  Observation: ~60 tokens (just names)
  Total: ~750 tokens                        Total: ~160 tokens

3 iterations × 750 = 2250 tokens          5 iterations × 160 = 800 tokens
+ system + query = ~3100 total             + system + query = ~1700 total

RESULT: Tight budget, barely fits         RESULT: Comfortable, room for more
```

**The insight:** By making observations COMPACT (citations only, not full text), notebook 03 fits MORE iterations in the same context window. 5 iterations × compact = less tokens than 3 iterations × verbose.

---

## Why This Architecture Achieved F1 = 0.040 (vs 0.006 in Notebook 02)

| Improvement | Impact | Mechanism |
|---|---|---|
| German-only agent (Run 3) | +5.4× F1 | No code-switching, queries match German corpus |
| FAISS embeddings | Better than BM25 alone | Semantic matching handles paraphrases |
| HyDE + PRF | Bridges English→German gap | Hypothetical German docs are closer to real ones |
| RRF fusion (3 rankings) | More robust | Document found by all 3 methods is almost certainly correct |
| GBNF grammar | Zero parse failures | No wasted iterations on malformed output |
| Guardrails | Forces coverage | Agent searches BOTH laws and courts |

---

## What Still Failed (Ceiling at F1 = 0.040)

| Problem | Root Cause | Why It Can't Be Fixed Here |
|---|---|---|
| Embedding quality | Qwen3-0.6B (small model) can't distinguish "Art. 221" from "Art. 222" | Need larger/fine-tuned embedding model |
| Court corpus 8% | Only 200K of 2.5M courts indexed | Memory/time constraints on Kaggle |
| Reranker broken | Qwen3-Reranker gives uniform scores | Model too small or wrong prompt format |
| Single-thread retrieval | Agent searches one direction at a time | Architecture limitation (sequential) |
| No domain routing | Agent doesn't know which court division handles which case type | Needs domain knowledge (added in notebook 04) |

---

## Key Interview Concepts from This Notebook

| Concept | One-Line Explanation |
|---------|---------------------|
| **HyDE** | Generate hypothetical document, embed it, search for real similar docs |
| **PRF** | Use initial search results as context to improve query/HyDE generation |
| **RRF** | Merge multiple rankings: score = Σ 1/(k + rank) across all lists |
| **GBNF** | Grammar constraint at token level — LLM can only produce valid structure |
| **Instruction embeddings** | Different prompts for documents vs queries in embedding model |
| **Normalized embeddings** | Unit-length vectors → inner product = cosine similarity |
| **fp16** | Half precision — 50% less VRAM, negligible quality loss for inference |
| **Multi-GPU split** | LLM on GPU 0, embeddings on GPU 1 (avoid OOM) |
| **Agent guardrails** | Rules that override LLM decisions (force alternation, minimum searches) |

---

## Interview Questions This Notebook Prepares You For

1. **"Explain HyDE (Hypothetical Document Embeddings)."**  
   → "HyDE bridges the query-document gap by generating a hypothetical document that answers the query, then embedding that doc and searching for real similar ones. It's especially useful for cross-lingual retrieval where the query language differs from the corpus language."

2. **"How does Reciprocal Rank Fusion work?"**  
   → "RRF combines multiple ranked lists without needing score normalization. For each document, its RRF score is the sum of 1/(k + rank) across all rankings. A document ranked high in multiple lists gets a higher combined score. k=60 is standard."

3. **"How do you guarantee JSON output from an LLM?"**  
   → "Grammar-constrained decoding (GBNF). At each token, invalid tokens are masked to probability 0. The LLM physically cannot produce output that violates the grammar. This is more reliable than prompting + regex parsing or retry loops."

4. **"What's the difference between dense and sparse retrieval?"**  
   → "Dense (FAISS): captures semantic meaning, handles paraphrases, but can't distinguish structurally similar documents. Sparse (BM25): exact keyword matching, precise for specific terms like article numbers, but fails on synonyms/paraphrases. Hybrid (RRF fusion) is strictly better than either alone."

5. **"How do you handle multi-GPU deployment?"**  
   → "Assign models to specific devices: LLM on cuda:0 (largest model), embedding model on cuda:1. Load one at a time during batch operations to avoid OOM. Free embeddings after indexing, load reranker only when needed."

6. **"What is Pseudo-Relevance Feedback (PRF)?"**  
   → "Assume the top-K initial results are relevant. Use them as context/examples for query expansion or HyDE generation. This grounds the expansion in real corpus vocabulary instead of hallucination. It's a 'good gets better' technique — fails when initial retrieval is bad."

7. **"How do you prevent an LLM agent from repeating itself?"**  
   → "Three guardrails: (1) Track seen queries — skip duplicates. (2) Force tool alternation — if last 2 calls were same tool, switch. (3) Minimum search count — don't allow 'done' until both corpora have been searched at least twice."
