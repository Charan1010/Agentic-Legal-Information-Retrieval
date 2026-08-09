"""Download Mistral-7B-Instruct GGUF model from HuggingFace."""
import os
import sys
import urllib.request

URL = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
DEST = os.path.join(os.path.dirname(__file__), "models", "mistral-7b-instruct-v0.2.Q4_K_M.gguf")

os.makedirs(os.path.dirname(DEST), exist_ok=True)

def report(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  {pct:5.1f}%  {mb:,.0f} / {total_mb:,.0f} MB")
        sys.stdout.flush()

print(f"Downloading to: {DEST}")
print(f"URL: {URL}")
print()

try:
    urllib.request.urlretrieve(URL, DEST, reporthook=report)
    print(f"\n\nDone! File size: {os.path.getsize(DEST) / (1024**3):.2f} GB")
except KeyboardInterrupt:
    print("\n\nDownload cancelled.")
    if os.path.exists(DEST):
        os.remove(DEST)
