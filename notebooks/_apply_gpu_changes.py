"""Modify 03_hyde_kaggle.ipynb to add multi-GPU support for T4 x2."""
import json

path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'

with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Cell 4 (LOAD LLM) and Cell 7 (FAISS SEMANTIC)
for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))
    
    if 'CELL 4: LOAD LLM' in src:
        print(f"Found CELL 4 at index {i}")
        cell['source'] = [
            "# === CELL 4: LOAD LLM ===\n",
            "from llama_cpp import Llama\n",
            "import torch\n",
            "\n",
            "# Detect GPU count for multi-GPU split\n",
            "_n_gpus = torch.cuda.device_count()\n",
            "print(f\"GPUs detected: {_n_gpus} \\u2014 {[torch.cuda.get_device_name(i) for i in range(_n_gpus)]}\")\n",
            "\n",
            "# Find model file\n",
            "model_file = MODEL_PATH / CONFIG[\"model_file\"]\n",
            "if not model_file.exists():\n",
            "    gguf_files = list(MODEL_PATH.rglob(\"*.gguf\"))\n",
            "    if gguf_files:\n",
            "        model_file = gguf_files[0]\n",
            "    else:\n",
            "        raise FileNotFoundError(f\"No GGUF model found in {MODEL_PATH}\")\n",
            "\n",
            "print(f\"Loading model: {model_file.name}\")\n",
            "llm = Llama(\n",
            "    model_path=str(model_file),\n",
            "    n_ctx=CONFIG[\"n_ctx\"],\n",
            "    n_threads=CONFIG[\"n_threads\"],\n",
            "    n_gpu_layers=CONFIG[\"n_gpu_layers\"],\n",
            "    main_gpu=0,  # Pin LLM to GPU 0\n",
            "    verbose=False,\n",
            ")\n",
            "gc.collect()\n",
            "print(f\"Model loaded \\u2014 GPU 0, layers: {CONFIG['n_gpu_layers']}\")\n",
        ]
        print("  -> Updated with multi-GPU support (main_gpu=0, torch GPU detection)")
    
    elif 'CELL 7: FAISS SEMANTIC SEARCH' in src:
        print(f"Found CELL 7 at index {i}")
        # Keep the embedding/reranking part but change device assignments
        new_src = [
            "# === CELL 7: FAISS SEMANTIC SEARCH + SENTENCE-TRANSFORMER ===\n",
            "import faiss\n",
            "from sentence_transformers import SentenceTransformer\n",
            "\n",
            "# GPU assignment: LLM on GPU 0, embedder + reranker on GPU 1 (if 2 GPUs available)\n",
            "_embed_device = \"cuda:1\" if _n_gpus >= 2 else \"cuda:0\"\n",
            "_rerank_device = \"cuda:1\" if _n_gpus >= 2 else \"cuda:0\"\n",
            "print(f\"Multi-GPU split: LLM\\u2192cuda:0, Embedder\\u2192{_embed_device}, Reranker\\u2192{_rerank_device}\")\n",
            "\n",
            "print(\"Loading sentence-transformer model...\")\n",
            "_st_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=_embed_device)\n",
            "_st_model.max_seq_length = 512\n",
            "print(f\"  Model loaded: dim={_st_model.get_sentence_embedding_dimension()}, device={_embed_device}\")\n",
            "\n",
            "# ---- Cross-encoder reranker ----\n",
            "from sentence_transformers import CrossEncoder\n",
            "_reranker = None\n",
            "if CONFIG[\"rerank_enabled\"]:\n",
            "    try:\n",
            "        print(f\"Loading reranker: {CONFIG['rerank_model']}...\")\n",
            "        _reranker = CrossEncoder(CONFIG[\"rerank_model\"], max_length=512, device=_rerank_device)\n",
            "        print(f\"  Reranker loaded on {_rerank_device}\")\n",
            "    except Exception as e:\n",
            "        print(f\"  \\u26a0\\ufe0f Reranker failed to load: {e}\")\n",
            "        print(f\"  Continuing WITHOUT reranker (FAISS-only retrieval)\")\n",
            "        _reranker = None\n",
            "else:\n",
            "    print(\"  Reranker: DISABLED\")\n",
            "\n",
            "# ---- Embed main corpus for search ----\n",
            "def embed_corpus(documents, desc=\"Embedding\", batch_size=512):\n",
            "    texts = [f\"{d.get('citation','')}: {d.get('text','')}\" for d in documents]\n",
            "    print(f\"  {desc}: {len(texts):,} docs, batch_size={batch_size}\")\n",
            "    t0 = time.time()\n",
            "    embeddings = _st_model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=batch_size)\n",
            "    print(f\"  Done in {time.time()-t0:.1f}s ({len(texts)/(time.time()-t0):.0f} docs/sec)\")\n",
            "    return embeddings.astype('float32')\n",
            "\n",
            "# Laws embeddings\n",
            "if FAISS_LAWS_PATH.exists():\n",
            "    print(f\"Loading cached law embeddings...\")\n",
            "    with open(FAISS_LAWS_PATH, 'rb') as f:\n",
            "        law_corpus_embeddings = pickle.load(f)\n",
            "else:\n",
            "    law_corpus_embeddings = embed_corpus(laws_documents, desc=\"Laws\")\n",
            "    with open(FAISS_LAWS_PATH, 'wb') as f:\n",
            "        pickle.dump(law_corpus_embeddings, f)\n",
            "    _save_checkpoint(FAISS_LAWS_PATH)\n",
            "\n",
            "# Courts embeddings\n",
            "if FAISS_COURTS_PATH.exists():\n",
            "    print(f\"Loading cached court embeddings...\")\n",
            "    with open(FAISS_COURTS_PATH, 'rb') as f:\n",
            "        court_corpus_embeddings = pickle.load(f)\n",
            "else:\n",
            "    court_corpus_embeddings = embed_corpus(courts_documents, desc=\"Courts\")\n",
            "    with open(FAISS_COURTS_PATH, 'wb') as f:\n",
            "        pickle.dump(court_corpus_embeddings, f)\n",
            "    _save_checkpoint(FAISS_COURTS_PATH)\n",
            "\n",
            "# Build corpus FAISS indices\n",
            "dim = _st_model.get_sentence_embedding_dimension()\n",
            "faiss_law_index = faiss.IndexFlatIP(dim)\n",
            "faiss_law_index.add(law_corpus_embeddings)\n",
            "\n",
            "faiss_court_index = faiss.IndexFlatIP(dim)\n",
            "faiss_court_index.add(court_corpus_embeddings)\n",
            "\n",
            "# Free raw embeddings from memory\n",
            "del law_corpus_embeddings, court_corpus_embeddings\n",
            "gc.collect()\n",
            "\n",
            "_save_checkpoint(FAISS_LAWS_PATH, FAISS_COURTS_PATH)\n",
            "print(f\"\\nCorpus FAISS: laws={faiss_law_index.ntotal:,}, courts={faiss_court_index.ntotal:,} vectors ({dim}d)\")\n",
            "print(f\"  (No few-shot FAISS index \\u2014 PRF uses corpus index directly)\")\n",
        ]
        cell['source'] = new_src
        print("  -> Updated with cuda:1 for embedder and reranker")

# Write back
with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("\nDone! Notebook saved.")
