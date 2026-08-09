"""Add reranker to the notebook: CONFIG, model loading, per-search rerank, final rerank."""
import json
from pathlib import Path

NB_PATH = Path(r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb")

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]

# ============================================================
# 1. CONFIG CHANGES (Cell 4): top_k 15→30, add reranker settings
# ============================================================
for i, cell in enumerate(cells):
    src = "".join(cell["source"])
    if '"top_k_laws": 15,' in src and '"top_k_courts": 15,' in src:
        new_src = src.replace(
            '"top_k_laws": 15,',
            '"top_k_laws": 30,      # Over-retrieve for reranker'
        ).replace(
            '"top_k_courts": 15,',
            '"top_k_courts": 30,    # Over-retrieve for reranker'
        )
        # Add reranker config after hyde_enabled line
        new_src = new_src.replace(
            '"hyde_enabled": True,\n    "hyde_max_synthetic_types": 9999,',
            '"hyde_enabled": True,\n    "hyde_max_synthetic_types": 9999,\n'
            '    # Reranker\n'
            '    "rerank_model": "BAAI/bge-reranker-v2-m3",\n'
            '    "rerank_top_n": 10,         # Per-search: keep top-10 after reranking\n'
            '    "final_rerank_top_n": 25,   # Final: keep top-25 after reranking all deduped\n'
            '    "rerank_enabled": True,'
        )
        # Update the comment about retrieval
        new_src = new_src.replace(
            '# Retrieval (15 per tool call',
            '# Retrieval (30 per tool call, reranked to 10'
        )
        new_src = new_src.replace(
            '~6 calls = ~90 candidates',
            '~6 calls = ~60 kept'
        )
        cells[i]["source"] = new_src.splitlines(keepends=True)
        # Ensure last line has no trailing newline issues
        if cells[i]["source"] and not cells[i]["source"][-1].endswith("\n"):
            pass  # fine
        print(f"  ✅ Cell {i}: CONFIG updated (top_k=30, reranker settings added)")
        break
else:
    print("  ❌ Could not find CONFIG cell with top_k_laws")

# ============================================================
# 2. ADD RERANKER MODEL LOADING (Cell 9: after sentence-transformer)
# ============================================================
for i, cell in enumerate(cells):
    src = "".join(cell["source"])
    if "SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'" in src and "faiss_law_index" in src:
        # Add reranker loading after the sentence-transformer model load
        old_line = "print(f\"  Model loaded: dim={_st_model.get_sentence_embedding_dimension()}, device=cuda\")"
        reranker_code = (
            'print(f"  Model loaded: dim={_st_model.get_sentence_embedding_dimension()}, device=cuda")\n'
            '\n'
            '# ---- Cross-encoder reranker ----\n'
            'from sentence_transformers import CrossEncoder\n'
            'if CONFIG["rerank_enabled"]:\n'
            '    print(f"Loading reranker: {CONFIG[\'rerank_model\']}...")\n'
            '    _reranker = CrossEncoder(CONFIG["rerank_model"], max_length=512, device="cuda")\n'
            '    print(f"  Reranker loaded on cuda")\n'
            'else:\n'
            '    _reranker = None\n'
            '    print("  Reranker: DISABLED")'
        )
        new_src = src.replace(old_line, reranker_code)
        cells[i]["source"] = new_src.splitlines(keepends=True)
        if cells[i]["source"] and not cells[i]["source"][-1].endswith("\n"):
            pass
        print(f"  ✅ Cell {i}: Reranker model loading added")
        break
else:
    print("  ❌ Could not find sentence-transformer cell")

# ============================================================
# 3. MODIFY faiss_search() — add per-search reranking (Cell 11)
# ============================================================
for i, cell in enumerate(cells):
    src = "".join(cell["source"])
    if "def faiss_search(query, doc_type=" in src and "class LawSearchTool" in src:
        # Replace the faiss_search function
        old_faiss_search = '''def faiss_search(query, doc_type="law", top_k=40, hyde_doc=None):
    """FAISS semantic search with HyDE-enhanced query embedding."""
    if doc_type == "law":
        f_index = faiss_law_index
        docs = laws_documents
        doc_types = laws_doc_types
    else:
        f_index = faiss_court_index
        docs = courts_documents
        doc_types = courts_doc_types

    # Use HyDE doc for embedding if available, else raw query
    faiss_query = hyde_doc if hyde_doc else query
    q_vec = _st_model.encode([faiss_query], normalize_embeddings=True).astype('float32')
    scores, indices = f_index.search(q_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score <= 0:
            continue
        doc = docs[idx].copy()
        doc["_score"] = float(score)
        doc["_type"] = str(doc_types[idx])
        results.append(doc)

    # Verbose for first N queries
    if _query_count < _VERBOSE_FIRST_N:
        top_cits = [r.get("citation","")[:30] for r in results[:3]]
        print(f"    [FAISS {doc_type}] \u2192 {len(results)} results")
        print(f"      Top 3: {top_cits}")

    return results'''

        new_faiss_search = '''def faiss_search(query, doc_type="law", top_k=40, hyde_doc=None):
    """FAISS semantic search with HyDE + cross-encoder reranking."""
    if doc_type == "law":
        f_index = faiss_law_index
        docs = laws_documents
        doc_types = laws_doc_types
    else:
        f_index = faiss_court_index
        docs = courts_documents
        doc_types = courts_doc_types

    # Use HyDE doc for embedding if available, else raw query
    faiss_query = hyde_doc if hyde_doc else query
    q_vec = _st_model.encode([faiss_query], normalize_embeddings=True).astype('float32')
    scores, indices = f_index.search(q_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score <= 0:
            continue
        doc = docs[idx].copy()
        doc["_score"] = float(score)
        doc["_type"] = str(doc_types[idx])
        results.append(doc)

    # Verbose for first N queries
    if _query_count < _VERBOSE_FIRST_N:
        top_cits = [r.get("citation","")[:30] for r in results[:3]]
        print(f"    [FAISS {doc_type}] \u2192 {len(results)} candidates (pre-rerank)")

    # ---- Cross-encoder reranking ----
    rerank_top_n = CONFIG.get("rerank_top_n", 10)
    if _reranker and CONFIG.get("rerank_enabled") and len(results) > 0:
        # Score each (query, doc_text) pair with cross-encoder
        pairs = [(query, r.get("text", "")[:512]) for r in results]
        rerank_scores = _reranker.predict(pairs, show_progress_bar=False)
        for doc, rs in zip(results, rerank_scores):
            doc["_rerank_score"] = float(rs)
        # Sort by reranker score and keep top-N
        results.sort(key=lambda d: d["_rerank_score"], reverse=True)
        results = results[:rerank_top_n]
        if _query_count < _VERBOSE_FIRST_N:
            top_cits = [r.get("citation","")[:30] for r in results[:3]]
            print(f"    [Rerank {doc_type}] \u2192 kept top-{rerank_top_n}: {top_cits}")
    else:
        if _query_count < _VERBOSE_FIRST_N:
            print(f"      Top 3: {top_cits}")

    return results'''

        if old_faiss_search in src:
            new_src = src.replace(old_faiss_search, new_faiss_search)
            cells[i]["source"] = new_src.splitlines(keepends=True)
            if cells[i]["source"] and not cells[i]["source"][-1].endswith("\n"):
                pass
            print(f"  ✅ Cell {i}: faiss_search() updated with per-search reranking")
        else:
            # Try a more flexible match
            print(f"  ⚠️  Cell {i}: faiss_search found but exact match failed. Trying line-by-line...")
            # Replace the whole function by finding start/end
            lines = src.split("\n")
            start_idx = None
            end_idx = None
            for li, line in enumerate(lines):
                if line.startswith("def faiss_search("):
                    start_idx = li
                elif start_idx is not None and (line.startswith("class ") or line.startswith("def ")) and li > start_idx + 5:
                    end_idx = li
                    break
            if start_idx is not None and end_idx is not None:
                new_lines = lines[:start_idx] + new_faiss_search.split("\n") + ["", ""] + lines[end_idx:]
                new_src = "\n".join(new_lines)
                cells[i]["source"] = new_src.splitlines(keepends=True)
                print(f"  ✅ Cell {i}: faiss_search() replaced (line-by-line fallback)")
            else:
                print(f"  ❌ Cell {i}: Could not find faiss_search boundaries")
        break
else:
    print("  ❌ Could not find faiss_search cell")

# ============================================================
# 4. ADD FINAL RERANKING in run_agent() (Cell 12)
# ============================================================
for i, cell in enumerate(cells):
    src = "".join(cell["source"])
    if "def run_agent(query" in src and "Deduplicate citations" in src:
        # Replace the dedup section with dedup + final rerank
        old_dedup = '''    # Deduplicate citations (preserve order)
    seen = set()
    deduped = []
    for c in all_citations:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return deduped, logs'''

        new_dedup = '''    # Deduplicate citations (preserve order, keep best result per citation)
    seen = {}
    for r in all_results:
        cit = r.get("citation", "")
        if not cit:
            continue
        # Keep the result with highest rerank score (or FAISS score as fallback)
        score = r.get("_rerank_score", r.get("_score", 0))
        if cit not in seen or score > seen[cit].get("_rerank_score", seen[cit].get("_score", 0)):
            seen[cit] = r
    deduped_results = list(seen.values())

    # ---- Final reranking against original query ----
    final_top_n = CONFIG.get("final_rerank_top_n", 25)
    if _reranker and CONFIG.get("rerank_enabled") and len(deduped_results) > final_top_n:
        pairs = [(query, r.get("text", "")[:512]) for r in deduped_results]
        final_scores = _reranker.predict(pairs, show_progress_bar=False)
        for doc, fs in zip(deduped_results, final_scores):
            doc["_final_rerank_score"] = float(fs)
        deduped_results.sort(key=lambda d: d["_final_rerank_score"], reverse=True)
        deduped_results = deduped_results[:final_top_n]
        if verbose:
            print(f"  [Final rerank] {len(seen)} unique \u2192 kept top-{final_top_n}")
    elif verbose and len(deduped_results) > 0:
        print(f"  [Final] {len(deduped_results)} unique citations (no final rerank needed)")

    deduped = [r.get("citation", "") for r in deduped_results]
    return deduped, logs'''

        # Also need to change how all_citations is collected — need full results, not just citation strings
        # Replace all_citations.extend(obs_citations) with all_results tracking
        old_collect = '''    all_citations = []
    logs = []
    history = []  # list of (action_str, observation_summary) tuples'''

        new_collect = '''    all_results = []   # Full result dicts (with scores) for final reranking
    all_citations = []  # Legacy: just citation strings
    logs = []
    history = []  # list of (action_str, observation_summary) tuples'''

        old_extend = '''        obs_citations = tool.get_last_citations()
        all_citations.extend(obs_citations)'''

        new_extend = '''        obs_citations = tool.get_last_citations()
        all_citations.extend(obs_citations)
        all_results.extend(tool._last_results)  # Keep full results for final rerank'''

        if old_dedup in src and old_collect in src and old_extend in src:
            new_src = src.replace(old_collect, new_collect)
            new_src = new_src.replace(old_extend, new_extend)
            new_src = new_src.replace(old_dedup, new_dedup)
            cells[i]["source"] = new_src.splitlines(keepends=True)
            print(f"  ✅ Cell {i}: run_agent() updated with final reranking")
        else:
            if old_dedup not in src:
                print(f"  ❌ Cell {i}: old_dedup not found")
            if old_collect not in src:
                print(f"  ❌ Cell {i}: old_collect not found")
            if old_extend not in src:
                print(f"  ❌ Cell {i}: old_extend not found")
        break
else:
    print("  ❌ Could not find run_agent cell")

# ============================================================
# 5. Save modified notebook
# ============================================================
with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ All changes saved to notebook!")
print("\nSummary of changes:")
print("  1. CONFIG: top_k 15→30, added rerank_top_n=10, final_rerank_top_n=25")
print("  2. Cell 9: CrossEncoder model loading (BAAI/bge-reranker-v2-m3)")
print("  3. faiss_search(): per-search reranking (30→10)")
print("  4. run_agent(): final reranking of all deduped results (→top 25)")
