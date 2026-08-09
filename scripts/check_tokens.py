"""Quick token budget check for planner with routing guides."""
import sys
sys.path.insert(0, 'src')
from pathlib import Path

CONTEXT_DIR = Path('context')
PROMPTS_DIR = Path('prompts')

def _load_text(p):
    return p.read_text(encoding='utf-8')

system_prompt = _load_text(PROMPTS_DIR / 'planner_system.txt').format(
    available_law_codes='StGB, StPO, ZGB, OR, BGG, BV, ATSG, IVG',
    available_court_codes='1B_, 4A_, 5A_, 6B_, 8C_, 9C_, BGE_I, BGE_III, BGE_IV, BGE_V',
)
swiss_legal = _load_text(CONTEXT_DIR / 'swiss_legal_system.txt')
routing_laws = _load_text(CONTEXT_DIR / 'routing_guide_laws.txt')
routing_courts = _load_text(CONTEXT_DIR / 'routing_guide_courts.txt')
terminology = _load_text(CONTEXT_DIR / 'terminology_bridge.txt')

user_msg = (
    f'KONTEXT (Schweizerisches Rechtssystem):\n{swiss_legal}\n\n'
    f'GESETZES-ROUTING (Taxonomie & Klassifikation):\n{routing_laws}\n\n'
    f'GERICHTS-ROUTING (Abteilungen & Praefixe):\n{routing_courts}\n\n'
    f'TERMINOLOGIE (Englisch -> Deutsch):\n{terminology}\n\n'
    f'FRAGE: Under what conditions can pre-trial detention be extended?'
)

system_tokens = len(system_prompt) / 4
user_tokens = len(user_msg) / 4
total = system_tokens + user_tokens

print(f'System prompt: {len(system_prompt):,} chars = ~{system_tokens:.0f} tokens')
print(f'User message:  {len(user_msg):,} chars = ~{user_tokens:.0f} tokens')
print(f'TOTAL:         ~{total:.0f} tokens')
print(f'With 800 gen:  ~{total + 800:.0f} tokens needed')
fits = "YES" if total + 800 < 16000 else "NO"
print(f'Fits in 16K?   {fits}')

# Also check executor worst case (all codes)
from omnilex.retrieval.executor import get_taxonomy_section, _build_taxonomy_cache
cache = _build_taxonomy_cache()
all_codes = list(cache.keys())
max_section = get_taxonomy_section(all_codes)
print(f'\nExecutor taxonomy (ALL {len(all_codes)} codes): {len(max_section)} chars = ~{len(max_section)/4:.0f} tokens')
# Typical direction uses 1-3 codes
for n in [1, 2, 3]:
    sample = get_taxonomy_section(all_codes[:n])
    print(f'  {n} codes: {len(sample)} chars = ~{len(sample)/4:.0f} tokens')
