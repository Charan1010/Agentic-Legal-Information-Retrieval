"""Fix text truncation limits in the notebook to fully utilize model capacity."""
import json

NB_PATH = "notebooks/03_hyde_kaggle.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

changes = 0

for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    new_source = []
    for line in cell["source"]:
        # 1. CONFIG embed_max_length: 512 -> 1024 tokens
        if '"embed_max_length": 512' in line:
            line = line.replace('"embed_max_length": 512', '"embed_max_length": 1024')
            changes += 1

        # 2. Embedding corpus text[:400] -> text[:1500] chars
        #    Target line contains: d.get('text','')[:400]
        if "[:400]" in line and "texts = " in line and "d.get" in line:
            line = line.replace("[:400]", "[:1500]")
            changes += 1

        # 3. PRF snippet text[:400] -> text[:800]
        #    Target line: text = r.get("text", "")[:400]
        elif '= r.get("text", "")[:400]' in line:
            line = line.replace("[:400]", "[:800]")
            changes += 1

        # 4. Reranker doc text[:512] -> text[:2048] (hybrid_search + final rerank)
        #    Target lines: r.get("text", "")[:512]
        if 'r.get("text", "")[:512]' in line:
            line = line.replace('")[:512]', '")[:2048]')
            changes += 1

        # 5. Reranker query hyde_doc[:512] -> hyde_doc[:2048]
        if "hyde_doc[:512]" in line and "first_hyde_doc" not in line:
            line = line.replace("hyde_doc[:512]", "hyde_doc[:2048]")
            changes += 1

        # 6. Final reranker first_hyde_doc[:512] -> first_hyde_doc[:2048]
        if "first_hyde_doc[:512]" in line:
            line = line.replace("first_hyde_doc[:512]", "first_hyde_doc[:2048]")
            changes += 1

        # 7. CrossEncoder max_length=512 -> max_length=1024
        if "max_length=512" in line and "CrossEncoder" in line:
            line = line.replace("max_length=512", "max_length=1024")
            changes += 1

        new_source.append(line)
    cell["source"] = new_source

print(f"Total changes applied: {changes}")

# Also add a comment in CONFIG for clarity
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    for i, line in enumerate(cell["source"]):
        if '"embed_max_length": 1024' in line:
            if "# tokens" not in line:
                cell["source"][i] = line.rstrip("\n") .rstrip(",") + ",  # tokens (Qwen3 supports 8192; 1024 covers ~2800 chars of German)\n"
            break

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Notebook saved successfully.")
print("\nSummary of changes:")
print("  embed_max_length: 512 -> 1024 tokens")
print("  Embedding text:   [:400] -> [:1500] chars (covers courts P75=1346)")
print("  PRF snippets:     [:400] -> [:800] chars")
print("  Reranker docs:    [:512] -> [:2048] chars (uses ~731 tokens of 1024 capacity)")
print("  Reranker query:   [:512] -> [:2048] chars")
print("  CrossEncoder:     max_length=512 -> 1024 tokens")
print("  Batch size:       8 (unchanged — T4 has headroom)")
print("\n⚠️  IMPORTANT: Cached .pkl embeddings are now INVALID!")
print("  Delete faiss_laws_qwen3_embeddings.pkl and faiss_courts_qwen3_embeddings.pkl")
print("  They will be rebuilt with the new text lengths on next run.")
