"""Test improved regex that catches mixed-case Swiss abbreviations."""
import re, pandas as pd
from collections import Counter

# Improved: catches StGB, StPO, SchKG, etc.
# Pattern: word boundary + starts with uppercase + has at least one more uppercase
# somewhere + optional trailing lowercase
_LAW_TYPE_RE = re.compile(r'\b([A-Z][A-Za-z]*[A-Z][a-z]?)\s*$')
_LAW_TYPE_FALLBACK_RE = re.compile(r'\b([A-Z]{2,}[a-z]?)\b')

def get_law_type_v2(citation: str) -> str:
    """Improved: catches mixed-case Swiss abbreviations (StGB, StPO, SchKG)."""
    c = citation.strip()
    # Primary: trailing abbreviation with >=2 uppercase letters (allows lowercase between)
    match = _LAW_TYPE_RE.search(c)
    if match:
        return match.group(1)
    # Secondary: last all-caps word (fallback for edge cases)
    matches = _LAW_TYPE_FALLBACK_RE.findall(c)
    if matches:
        return matches[-1]
    return "OTHER"

# Test on known patterns
test_cases = [
    ("Art. 1 StGB", "StGB"),
    ("Art. 60 OR", "OR"),
    ("Art. 975 ZGB", "ZGB"),
    ("Art. 212 StPO", "StPO"),
    ("Art. 1 SchKG", "SchKG"),
    ("Art. 1 Abs. 1 StBOG", "StBOG"),
    ("Art. 3 Abs. 1 131.211", "OTHER"),
    ("Art. 1 Abs. 1 ABV-FINMA", "FINMA"),  # hyphenated
    ("Art. 1 Abs. 1 PDV-ETH", "ETH"),  # hyphenated
    ("Art. 1 JStPO", "JStPO"),  # juvenile
    ("Art. 1 Abs. 2 BGG", "BGG"),
    ("Art. 29 Abs. 2 BV", "BV"),
    ("Art. 10a Abs. 1 USG", "USG"),
    ("Art. 1 FINMAG", "FINMAG"),
    ("Art. 1 GebV SchKG", "SchKG"),
]

print("=== REGEX TEST ===")
for citation, expected in test_cases:
    result = get_law_type_v2(citation)
    status = "✓" if result == expected else f"✗ (got {result})"
    print(f"  {citation:35s} → {result:10s} {status}")

# Run on full corpus
print("\n=== FULL CORPUS WITH IMPROVED REGEX ===")
laws = pd.read_csv('data/laws_de.csv', usecols=['citation'], dtype={'citation': str}, na_filter=False)
law_types = [get_law_type_v2(c) for c in laws['citation']]
law_counts = Counter(law_types)

print(f'Total docs: {len(laws):,}')
print(f'Unique types: {len(law_counts)}')
print(f'Types with >=10 docs: {sum(1 for c in law_counts.values() if c >= 10)}')

# Check critical codes now
critical = ['StGB', 'StPO', 'BGG', 'ATSG', 'SchKG', 'UVG', 'RPG', 'USG', 'StBOG', 
            'BV', 'OR', 'ZGB', 'ZPO', 'AIG', 'IVG', 'KVG', 'AVIG', 'BVG', 'FINMAG',
            'JStPO', 'JStG']
print('\nCritical codes:')
for c in critical:
    count = law_counts.get(c, 0)
    flag = "" if count > 0 else " ← STILL MISSING"
    print(f'  {c:10s} {count:>6,} docs{flag}')

print('\nTop 60 by frequency:')
for t, c in law_counts.most_common(60):
    print(f'  {t:12s} {c:>6,} docs')

# OTHER analysis
print(f'\nOTHER: {law_counts.get("OTHER", 0):,} docs')

# Show what's in gold that the regex now finds
print('\n=== GOLD CITATIONS CHECK ===')
train = pd.read_csv('data/train.csv')
all_gold = []
for gc in train['gold_citations'].dropna():
    all_gold.extend(gc.split(';'))

gold_law_types = [get_law_type_v2(c.strip()) for c in all_gold if 'Art.' in c]
gold_counts = Counter(gold_law_types)
print('Gold citation types (top 30):')
for t, c in gold_counts.most_common(30):
    corpus_count = law_counts.get(t, 0)
    flag = '✓' if corpus_count > 0 else '✗ MISSING'
    print(f'  {t:12s} {c:>5} gold,  {corpus_count:>6,} corpus  {flag}')
