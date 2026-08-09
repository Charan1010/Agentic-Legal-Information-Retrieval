import pandas as pd, re
from collections import Counter

chunks = pd.read_csv('data/court_considerations.csv', usecols=['citation'], chunksize=200000)
tc = Counter()

for ch in chunks:
    for c in ch['citation'].astype(str):
        if c.startswith('BGE'):
            m = re.match(r'BGE\s+\d+\s+([IVX]+)', c)
            div = m.group(1) if m else 'OTHER'
            tc[f'BGE_{div}'] += 1
        else:
            m = re.match(r'(\d+[A-Z]+)', c)
            prefix = m.group(1) if m else 'OTHER'
            tc[f'CASE_{prefix}'] += 1

total = sum(tc.values())
bge = sum(v for k,v in tc.items() if k.startswith('BGE'))
case_n = sum(v for k,v in tc.items() if k.startswith('CASE'))

print(f'=== COURTS: {total} total docs ===')
print(f'  Leading (BGE): {bge} ({bge*100/total:.1f}%)')
print(f'  Non-leading (case): {case_n} ({case_n*100/total:.1f}%)')
print(f'  Unique types: {len(tc)}')
print()
for k, v in tc.most_common():
    print(f'  {k:20s} {v:>8d}  ({v*100/total:5.2f}%)')
