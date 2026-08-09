"""Audit notebook for all recent changes."""
import json

nb = json.load(open("notebooks/03_hyde_kaggle.ipynb", "r", encoding="utf-8"))
src = "".join(line for cell in nb["cells"] for line in cell.get("source", []))

print("=== TRUNCATION VALUES ===")
print(f"  [:400] present: {'[:400]' in src}")
print(f"  [:512] present: {'[:512]' in src}")
print(f"  [:1500] present: {'[:1500]' in src}")
print(f"  [:2048] present: {'[:2048]' in src}")
print(f"  [:800] present: {'[:800]' in src}")

print()
print("=== CONFIG VALUES ===")
if '"embed_max_length": 1024' in src:
    print("  embed_max_length: 1024 OK")
elif '"embed_max_length": 512' in src:
    print("  embed_max_length: 512 BAD (should be 1024)")
else:
    print("  embed_max_length: NOT FOUND")

if "max_length=1024" in src:
    print("  CrossEncoder max_length: 1024 OK")
elif "max_length=512" in src:
    print("  CrossEncoder max_length: 512 BAD (should be 1024)")

print()
print("=== KEY LINES ===")
for cell in nb["cells"]:
    for line in cell.get("source", []):
        if "[:1500]" in line and "texts =" in line:
            print(f"  Embed text: {line.strip()[:100]}")
        if "CrossEncoder" in line and "max_length" in line:
            print(f"  Reranker init: {line.strip()[:100]}")
        if 'r.get("text", "")[:2048]' in line:
            print(f"  Reranker doc: {line.strip()[:100]}")
        if "hyde_doc[:2048]" in line or "first_hyde_doc[:2048]" in line:
            print(f"  Reranker query: {line.strip()[:100]}")
        if "[:800]" in line and "r.get" in line:
            print(f"  PRF snippet: {line.strip()[:100]}")

print()
print("=== BM25 HYBRID ===")
print(f"  BM25Okapi: {'BM25Okapi' in src}")
print(f"  reciprocal_rank_fusion: {'reciprocal_rank_fusion' in src}")
print(f"  def hybrid_search: {'def hybrid_search' in src}")
print(f"  def _tokenize_german: {'def _tokenize_german' in src}")

print()
print("=== CO-CITATION + E-SECTION ===")
print(f"  def expand_cocitations: {'def expand_cocitations' in src}")
print(f"  def expand_esections: {'def expand_esections' in src}")
print(f"  expand_citations called: {'expand_citations(deduped' in src}")
