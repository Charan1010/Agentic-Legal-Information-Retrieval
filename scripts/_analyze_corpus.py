"""Analyze corpus structure for routing guide."""
import json, re
from pathlib import Path
from collections import Counter

DATA = Path('data')

# Check val.csv for query examples and gold citations
val_path = DATA / 'val.csv'
if val_path.exists():
    import pandas as pd
    df = pd.read_csv(val_path)
    print(f"Val queries: {len(df)}")
    for i, row in df.iterrows():
        q = row['query'][:120]
        gold = str(row.get('gold_citations', ''))[:200]
        print(f"\n  Q{i}: {q}")
        print(f"     Gold: {gold}")

# Check law types in gold citations
print("\n\n=== LAW TYPES IN GOLD ===")
all_golds = []
for _, row in df.iterrows():
    golds = str(row.get('gold_citations', '')).split(';')
    all_golds.extend([g.strip() for g in golds if g.strip()])

law_types = Counter()
court_types = Counter()
for cit in all_golds:
    if cit.startswith('BGE') or re.match(r'\d+[A-Z]', cit):
        # Court
        m = re.match(r'BGE\s+\d+\s+([IVX]+)', cit)
        if m:
            court_types[f"BGE_{m.group(1)}"] += 1
        else:
            court_types["OTHER"] += 1
    else:
        # Law - extract abbreviation
        m = re.search(r'\b([A-Z]{2,}[a-z]?)\s*$', cit.strip())
        if m:
            law_types[m.group(1)] += 1
        else:
            law_types["OTHER"] += 1

print("\nLaw types in gold citations:")
for t, c in law_types.most_common(30):
    print(f"  {t}: {c}")

print("\nCourt types in gold citations:")
for t, c in court_types.most_common(30):
    print(f"  {t}: {c}")

# Show unique citation patterns
print("\n=== SAMPLE CITATIONS (first 20 unique) ===")
seen = set()
for cit in all_golds[:100]:
    if cit not in seen:
        print(f"  {cit}")
        seen.add(cit)
    if len(seen) >= 30:
        break
