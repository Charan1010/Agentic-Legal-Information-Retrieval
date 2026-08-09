"""Analyze law/court type extraction from actual data."""
import re, pandas as pd
from collections import Counter

def get_law_type(citation):
    match = re.search(r'\b([A-Z]{2,}[a-z]?)\s*$', citation.strip())
    if match:
        return match.group(1)
    matches = re.findall(r'\b([A-Z]{2,})\b', citation)
    return matches[-1] if matches else 'OTHER'

def get_court_type(citation):
    m = re.match(r'^(\d[A-Z]_)', citation)
    if m:
        return m.group(1)
    m = re.match(r'BGE\s+\d+\s+(I{1,3}V?|V)\s', citation)
    if m:
        return f'BGE_{m.group(1)}'
    return 'OTHER'

# Laws
print('=== LAWS ===')
laws = pd.read_csv('data/laws_de.csv', usecols=['citation'], dtype={'citation': str}, na_filter=False)
law_types = [get_law_type(c) for c in laws['citation']]
law_counts = Counter(law_types)
print(f'Total docs: {len(laws):,}')
print(f'Unique types: {len(law_counts)}')
print(f'Types with >=10 docs: {sum(1 for c in law_counts.values() if c >= 10)}')
print(f'Types with >=50 docs: {sum(1 for c in law_counts.values() if c >= 50)}')
print()

# Check critical codes from routing guide
critical = ['StGB', 'StPO', 'BGG', 'ATSG', 'SchKG', 'UVG', 'RPG', 'USG', 'StBOG', 'BVG', 'IVG', 'KVG', 'AVIG', 'AIG']
print('Critical codes from routing guide:')
for c in critical:
    count = law_counts.get(c, 0)
    print(f'  {c:10s} {count:>6,} docs', end='')
    if count == 0:
        # Check if it appears as substring in citations
        matches = [cit for cit in laws['citation'] if c in cit][:3]
        print(f'  ← NOT FOUND! Samples with "{c}" substring: {matches}')
    else:
        print()

print()
print('Top 80 law types (by frequency):')
for t, c in law_counts.most_common(80):
    print(f'  {t:12s} {c:>6,} docs')

print()
print('=== OTHER CATEGORY ANALYSIS ===')
others = [c for c, t in zip(laws['citation'], law_types) if t == 'OTHER']
print(f'Total OTHER: {len(others):,}')
print(f'Sample: {others[:15]}')
sr_pattern = re.compile(r'\d+\.?\d*$')
sr_count = sum(1 for c in others if sr_pattern.search(c.strip()))
print(f'With numeric SR ending: {sr_count:,} ({sr_count/len(others)*100:.1f}%)')

# What SR numbers are most common?
sr_nums = []
for c in others:
    m = re.search(r'(\d{3}(?:\.\d+)?)\s*$', c.strip())
    if m:
        sr_nums.append(m.group(1))
sr_counter = Counter(sr_nums)
print(f'\nTop 20 SR numbers (these are the "OTHER" docs):')
for sr, cnt in sr_counter.most_common(20):
    sample = next((c for c in others if sr in c), '')
    print(f'  SR {sr:10s} {cnt:>5,} docs  (e.g. "{sample}")')

print()
print('=== COURTS ===')
courts = pd.read_csv('data/court_considerations.csv', usecols=['citation'], dtype={'citation': str}, na_filter=False, nrows=500000)
court_types = [get_court_type(c) for c in courts['citation']]
court_counts = Counter(court_types)
print(f'Total docs (first 500K): {len(courts):,}')
print(f'Unique types: {len(court_counts)}')
print(f'Types with >=50 docs: {sum(1 for c in court_counts.values() if c >= 50)}')
print()
print('All court types (by frequency):')
for t, c in court_counts.most_common():
    print(f'  {t:12s} {c:>6,} docs')

# Check what's in train.csv gold citations
print('\n\n=== TRAIN.CSV GOLD CITATIONS ANALYSIS ===')
train = pd.read_csv('data/train.csv')
if 'gold_citations' in train.columns:
    all_gold = []
    for gc in train['gold_citations'].dropna():
        all_gold.extend(gc.split(';'))
    gold_law_types = [get_law_type(c.strip()) for c in all_gold if 'Art.' in c]
    gold_court_types = [get_court_type(c.strip()) for c in all_gold if not c.strip().startswith('Art.')]
    
    gold_law_counts = Counter(gold_law_types)
    gold_court_counts = Counter(gold_court_types)
    
    print(f'Total gold citations: {len(all_gold):,}')
    print(f'Law citations: {len(gold_law_types):,}')
    print(f'Court citations: {len(gold_court_types):,}')
    print()
    print('Gold law types (top 30):')
    for t, c in gold_law_counts.most_common(30):
        corpus_count = law_counts.get(t, 0)
        flag = ' ← IN CORPUS' if corpus_count > 0 else ' ← MISSING FROM CORPUS!'
        print(f'  {t:12s} {c:>5} gold refs, {corpus_count:>6,} in corpus{flag}')
    print()
    print('Gold court types (top 20):')
    for t, c in gold_court_counts.most_common(20):
        corpus_count = court_counts.get(t, 0)
        flag = ' ← IN CORPUS' if corpus_count > 0 else ' ← MISSING!'
        print(f'  {t:12s} {c:>5} gold refs, {corpus_count:>6,} in corpus{flag}')
