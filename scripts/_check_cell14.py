import json
import os

NB = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\03_hyde_kaggle.ipynb'
with open(NB, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][14]
lines = cell['source']
print(f"Cell 14 has {len(lines)} lines")
print("---FIRST 20---")
for i, l in enumerate(lines[:20]):
    print(f"  {i}: {l.rstrip()[:100]}")
print("---KEYWORDS---")
for i, l in enumerate(lines):
    stripped = l.strip()
    if any(kw in l for kw in ['ROUTING_GUIDE', 'AGENT_SYSTEM_PROMPT', 'routing_guide', 'taxonomy']):
        print(f"  {i}: {l.rstrip()[:100]}")
