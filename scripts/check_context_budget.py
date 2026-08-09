"""Show the token budget breakdown for the planner prompt."""
import json, re

def parse_sections(text, marker):
    sections = {}
    lines = text.split('\n')
    current_key = None
    current_lines = []
    for line in lines:
        if marker in line and len(line.strip()) > len(marker) + 2:
            if current_key:
                sections[current_key] = '\n'.join(current_lines).strip()
            current_key = line.replace(marker, '').strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        sections[current_key] = '\n'.join(current_lines).strip()
    return sections

laws = open('context/routing_guide_laws.txt', encoding='utf-8').read()
courts = open('context/routing_guide_courts.txt', encoding='utf-8').read()
terms = open('context/terminology_bridge.txt', encoding='utf-8').read()
system = open('prompts/planner_system.txt', encoding='utf-8').read()

law_sections = parse_sections(laws, '===')
court_sections = parse_sections(courts, '===')
term_sections = parse_sections(terms, '---')

print('=== SOURCE FILE SIZES ===')
print(f'  planner_system.txt:       {len(system):>6,} chars')
print(f'  routing_guide_laws.txt:   {len(laws):>6,} chars  ({len(law_sections)} sections)')
print(f'  routing_guide_courts.txt: {len(courts):>6,} chars  ({len(court_sections)} sections)')
print(f'  terminology_bridge.txt:   {len(terms):>6,} chars  ({len(term_sections)} sections)')
print()

print('=== LAW SECTIONS (injected per-domain) ===')
for k, v in law_sections.items():
    print(f'  {k[:50]:50s} {len(v):>5,} chars')
print()

print('=== COURT SECTIONS ===')
for k, v in court_sections.items():
    print(f'  {k[:50]:50s} {len(v):>5,} chars')
print()

print('=== TERMINOLOGY SECTIONS ===')
for k, v in term_sections.items():
    print(f'  {k[:50]:50s} {len(v):>5,} chars')
print()

# Estimate typical context assembly
print('=== TYPICAL CONTEXT ASSEMBLY (3 law domains + 2 courts + 2 terminology) ===')
law_vals = list(law_sections.values())
court_vals = list(court_sections.values())
term_vals = list(term_sections.values())

header_law = len(law_vals[0]) if law_vals else 0
avg_domain = sum(len(v) for v in law_vals) // max(len(law_vals), 1)
header_court = len(court_vals[0]) if court_vals else 0
avg_court = sum(len(v) for v in court_vals) // max(len(court_vals), 1)
avg_term = sum(len(v) for v in term_vals) // max(len(term_vals), 1)

print(f'  1. Laws header (always):            {header_law:>5,} chars')
print(f'  2. Laws routing (3 sections, avg):  {avg_domain*3:>5,} chars  (avg {avg_domain} each)')
print(f'  3. Court header (always):           {header_court:>5,} chars')
print(f'  4. Court routing (2 sections, avg): {avg_court*2:>5,} chars  (avg {avg_court} each)')
print(f'  5. Terminology (2 sections, avg):   {avg_term*2:>5,} chars  (avg {avg_term} each)')
print(f'  6. Application rules:                 300 chars')
print()

total = header_law + avg_domain*3 + header_court + avg_court*2 + avg_term*2 + 300
print(f'  TOTAL TYPICAL CONTEXT:              {total:>6,} chars')
if total > 12000:
    print(f'  vs max_chars=12000:                 TRUNCATED (loses {total-12000} chars)')
else:
    print(f'  vs max_chars=12000:                 FITS ({12000-total} chars spare)')
if total > 8000:
    print(f'  vs max_chars=8000:                  TRUNCATED (loses {total-8000} chars)')
else:
    print(f'  vs max_chars=8000:                  FITS ({8000-total} chars spare)')

print()
print('=== FULL PROMPT TOKEN BUDGET ===')
system_with_codes = len(system) + 800  # {available_law_codes} + {available_court_codes}

print(f'  System prompt (with codes):   {system_with_codes:>6,} chars')
print(f'  + [INST] wrappers:                  ~30 chars')
print(f'  + "FRAGE: " + question:            ~300 chars')
print()

for label, ctx_chars in [("max_chars=12000", 12000), ("typical", min(total, 12000)), ("max_chars=8000", 8000)]:
    full = system_with_codes + 30 + ctx_chars + 300
    tok_optimistic = full // 4  # if tokenizer is kind
    tok_realistic = full // 3   # German compound words
    tok_pessimistic = int(full / 2.5)  # worst case
    print(f'  [{label:^16s}]')
    print(f'    Total prompt chars: {full:>6,}')
    print(f'    Tokens @4ch/tok:   {tok_optimistic:>6,}  -> output room: {16384-tok_optimistic:>6,}')
    print(f'    Tokens @3ch/tok:   {tok_realistic:>6,}  -> output room: {16384-tok_realistic:>6,}')
    print(f'    Tokens @2.5ch/tok: {tok_pessimistic:>6,}  -> output room: {16384-tok_pessimistic:>6,}')
    print(f'    max_tokens_planner=3000 fits?  {"YES" if 16384-tok_pessimistic >= 3000 else "NO (CRASH)"}')
    print()

print('=== THE CRASH SCENARIO (RETRY) ===')
print('  First call produces truncated JSON (~2000 chars of raw output)')
print('  Retry prompt = original_prompt + raw_output + retry instruction')
retry_extra = 2000 + 50  # raw output + "[INST] Output NUR valides JSON. [/INST]"
for label, ctx_chars in [("max_chars=12000", 12000), ("max_chars=8000", 8000)]:
    first_prompt = system_with_codes + 30 + ctx_chars + 300
    retry_prompt = first_prompt + retry_extra
    tok = retry_prompt // 3
    print(f'  [{label}] retry prompt: {retry_prompt:,} chars / ~{tok:,} tokens')
    print(f'    + max_tokens=3000 = {tok+3000} total needed vs 16384 ctx')
    print(f'    {"FITS" if tok+3000 <= 16384 else "OVERFLOW by " + str(tok+3000-16384)}')
    print()
