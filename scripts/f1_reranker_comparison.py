"""Analyze F1 with and without reranker using V3 log data."""

# From pipeline_debug_log_v3.txt — Query 1
# All unique citations found by search (from direction summaries)
search_found = {
    # Direction 1 (StPO laws) - 14 unique
    'Art. 229 Abs. 3 StPO', 'Art. 229 Abs. 1 StPO', 'Art. 226 Abs. 3 StPO',
    'Art. 50 Abs. 3 StPO', 'Art. 274 Abs. 2 StPO', 'Art. 212 Abs. 3 StPO',
    'Art. 227 Abs. 7 StPO', 'Art. 220 Abs. 1 StPO', 'Art. 226 Abs. 4 StPO',
    'Art. 226 Abs. 5 StPO', 'Art. 431 Abs. 2 StPO', 'Art. 227 Abs. 4 StPO',
    'Art. 221 Abs. 1 StPO', 'Art. 227 Abs. 1 StPO',
    # Direction 2 (1B_ courts) - 20 unique
    '1B_633/2021 E. 5', '1B_166/2016 E. 2.2', '1B_149/2023 E. 2',
    '1B_18/2022 E. C', '1B_179/2022 E. 3', '1B_219/2010 20.07.2010 E. 5',
    '1B_203/2016 E. 4', '1B_94/2022 E. 2.1', '1B_288/2008 28.11.2008 E. 2.4',
    '1B_164/2020 E. 2.1', '1B_606/2020 E. 5', '1B_230/2008 25.08.2008 E. 4',
    '1B_379/2020 E. 2.6', '1B_173/2016 E. 2', '1B_300/2008 25.11.2008 E. 3',
    '1B_483/2012 20.09.2012 E. A', '1B_470/2022 E. 5.3', '1B_44/2008 13.03.2008 E. 2',
    '1B_187/2009 03.07.2009 E. A', '1B_1/2020 E. 7.1',
    # Direction 3 (BGG laws) - 29 unique
    'Art. 100 Abs. 2 BGG', 'Art. 25a Abs. 3 BGG', 'Art. 130 Abs. 1 BGG',
    'Art. 46 Abs. 1 BGG', 'Art. 63 Abs. 2 BGG', 'Art. 132 Abs. 2 BGG',
    'Art. 9 Abs. 1 BGG', 'Art. 70 Abs. 3 BGG', 'Art. 119 Abs. 2 BGG',
    'Art. 110 BGG', 'Art. 68 Abs. 4 BGG', 'Art. 25 Abs. 3 BGG',
    'Art. 47 Abs. 2 BGG', 'Art. 2 Abs. 1 BGG', 'Art. 47 Abs. 1 BGG',
    'Art. 50 Abs. 1 BGG', 'Art. 130 Abs. 2 BGG', 'Art. 38 Abs. 1 BGG',
    'Art. 100 Abs. 3 BGG', 'Art. 43 BGG', 'Art. 84 Abs. 2 BGG',
    'Art. 90 BGG', 'Art. 106 Abs. 1 BGG', 'Art. 44 Abs. 1 BGG',
    'Art. 124 Abs. 3 BGG', 'Art. 100 Abs. 6 BGG', 'Art. 66 Abs. 5 BGG',
    'Art. 52 BGG', 'Art. 99 Abs. 2 BGG',
    # Direction 4 (StPO+BGG) - additional unique
    'Art. 314 Abs. 2 StPO', 'Art. 406 Abs. 3 StPO', 'Art. 221 Abs. 1bis StPO',
    'Art. 289 Abs. 2 StPO', 'Art. 123 Abs. 2 StPO', 'Art. 81 Abs. 3 StPO',
    'Art. 274 Abs. 1 StPO', 'Art. 82 Abs. 4 StPO', 'Art. 165 Abs. 2 StPO',
    'Art. 81 Abs. 1 StPO', 'Art. 221 Abs. 2 StPO',
}

# Procedural defaults injected
defaults = {
    'Art. 42 Abs. 2 BGG', 'Art. 95 BGG', 'Art. 100 Abs. 1 BGG',
    'Art. 105 Abs. 1 BGG', 'Art. 29 Abs. 2 BV', 'Art. 78 Abs. 1 BGG',
    'Art. 80 Abs. 1 BGG', 'Art. 81 Abs. 1 BGG', 'Art. 221 Abs. 1 StPO',
    'Art. 10 Abs. 2 BV', 'Art. 31 Abs. 3 BV',
}

# Gold citations
gold = {
    'Art. 221 Abs. 1 StPO', 'Art. 140 Abs. 1 StGB', 'Art. 396 Abs. 1 StPO',
    'Art. 222 StPO', 'Art. 393 Abs. 1 StPO', 'Art. 382 Abs. 1 StPO',
    'Art. 385 Abs. 1 StPO', 'Art. 221 Abs. 2 StPO', 'Art. 227 Abs. 1 StPO',
    'Art. 212 Abs. 3 StPO', 'Art. 390 Abs. 2 StPO', 'Art. 422 Abs. 1 StPO',
    'Art. 422 Abs. 2 StPO', 'Art. 428 Abs. 1 StPO', 'Art. 135 Abs. 4 StPO',
    'Art. 100 Abs. 1 BGG', 'Art. 135 Abs. 3 StPO', 'Art. 37 Abs. 1 StBOG',
    'Art. 39 Abs. 1 StBOG', 'BGE 137 IV 122 E. 6.2', 'BGE 137 IV 122 E. 6.4',
    'BGE 137 IV 122 E. 4.2', 'BGE 132 I 21 E. 3.2', '1B_210/2023 E. 4.1',
    'BGE 132 I 21 E. 3.2.2', '1B_536/2018 E. 5.1', 'BGE 139 IV 270 E. 3.1',
    'BGE 133 I 168 E. 4.1', 'BGE 143 IV 168 E. 5.1', 'BGE 133 I 270 E. 3.4.2',
    'BGE 137 IV 122 E. 4.1', 'BGE 132 I 21 E. 3.2.1', '1B_90/2021 E. 2.1',
    '1B_90/2021 E. 2.4', '7B_496/2025 E. 3.2', '7B_231/2025 E. 4.1',
    '7B_69/2024 E. 3.3.2', '7B_301/2024 E. 2.4', '7B_12/2025 E. 2.2',
    '1B_357/2022 E. 3.1', '1B_15/2023 E. 3.1', '1B_28/2022 E. 4.1',
}

all_candidates = search_found | defaults

hits_in_pool = gold & all_candidates
missed_entirely = gold - all_candidates

print("=" * 60)
print("CANDIDATE POOL ANALYSIS")
print("=" * 60)
print(f"Search found (unique): {len(search_found)}")
print(f"Defaults injected: {len(defaults)}")
print(f"Total candidates (union): {len(all_candidates)}")
print(f"Gold total: {len(gold)}")
print()
print(f"Gold items IN candidate pool: {len(hits_in_pool)}")
for h in sorted(hits_in_pool):
    src = []
    if h in search_found: src.append("search")
    if h in defaults: src.append("default")
    print(f"  + {h}  [{' + '.join(src)}]")
print()
print(f"Gold items NEVER RETRIEVED: {len(missed_entirely)}")
for m in sorted(missed_entirely):
    print(f"  - {m}")

print()
print("=" * 60)
print("F1 COMPARISON: WITH vs WITHOUT RERANKER")
print("=" * 60)

# A) WITH reranker (current broken state) — top-10 fallback
current_output = {
    'Art. 80 Abs. 1 BGG', 'Art. 81 Abs. 1 BGG', 'Art. 10 Abs. 2 BV',
    'Art. 31 Abs. 3 BV', 'Art. 226 Abs. 4 StPO', 'Art. 227 Abs. 7 StPO',
    'Art. 227 Abs. 1 StPO', 'Art. 227 Abs. 4 StPO', 'Art. 220 Abs. 1 StPO',
    'Art. 431 Abs. 2 StPO',
}
tp_a = len(current_output & gold)
p_a = tp_a / len(current_output)
r_a = tp_a / len(gold)
f1_a = 2 * p_a * r_a / (p_a + r_a) if (p_a + r_a) > 0 else 0

print()
print(f"A) WITH RERANKER (broken, top-10 fallback):")
print(f"   Output size: {len(current_output)} citations")
print(f"   TP={tp_a}, P={p_a:.4f}, R={r_a:.4f}, F1={f1_a:.4f}")

# B) NO reranker — dump ALL candidates
tp_b = len(all_candidates & gold)
p_b = tp_b / len(all_candidates)
r_b = tp_b / len(gold)
f1_b = 2 * p_b * r_b / (p_b + r_b) if (p_b + r_b) > 0 else 0

print()
print(f"B) NO RERANKER — output ALL {len(all_candidates)} candidates:")
print(f"   TP={tp_b}, P={p_b:.4f}, R={r_b:.4f}, F1={f1_b:.4f}")

# C) NO reranker — capped at 60
cap = 60
p_c = tp_b / min(len(all_candidates), cap)
r_c = tp_b / len(gold)
f1_c = 2 * p_c * r_c / (p_c + r_c) if (p_c + r_c) > 0 else 0

print()
print(f"C) NO RERANKER — capped at 60 (max_final_citations):")
print(f"   TP={tp_b}, P={p_c:.4f}, R={r_c:.4f}, F1={f1_c:.4f}")
print(f"   (assumes all {tp_b} TPs survive the cap)")

# D) Sort by RRF only, top-20
# Defaults score 0.3, search results 0.015-0.032
# Top-20 = 11 defaults + top-9 search results by RRF
# Gold in defaults: Art. 221 Abs. 1 StPO + Art. 100 Abs. 1 BGG = 2
# Gold in top-9 search: Art. 227 Abs. 1 StPO (0.030), probably Art. 212 (0.016 if it makes top-9)
# Actually Art. 226 Abs. 4 (0.032), Art. 227 Abs. 7 (0.031-0.032), Art. 227 Abs. 1 (0.030), Art. 227 Abs. 4 (0.030)
# take top-9 slots... Art. 212 Abs. 3 might NOT make it (0.016 vs 0.026+ for others)
tp_d = 3  # 221 (default), 100 BGG (default), 227 Abs. 1 (search top-9)
p_d = tp_d / 20
r_d = tp_d / len(gold)
f1_d = 2 * p_d * r_d / (p_d + r_d) if (p_d + r_d) > 0 else 0

print()
print(f"D) NO RERANKER — top-20 by RRF score:")
print(f"   TP~{tp_d}, P={p_d:.4f}, R={r_d:.4f}, F1={f1_d:.4f}")

print()
print("=" * 60)
print("THE REAL PROBLEM: RETRIEVAL CEILING")
print("=" * 60)
print(f"Only {len(hits_in_pool)}/{len(gold)} gold items were EVER retrieved by search")
print(f"Max possible recall = {len(hits_in_pool)/len(gold):.3f}")
print(f"")
print("BREAKDOWN of what's missing:")
bge_missed = [m for m in missed_entirely if m.startswith("BGE")]
court_7b = [m for m in missed_entirely if m.startswith("7B_")]
court_1b = [m for m in missed_entirely if m.startswith("1B_")]
stpo_missed = [m for m in missed_entirely if "StPO" in m]
other = [m for m in missed_entirely if m not in bge_missed + court_7b + court_1b + stpo_missed]
print(f"  BGE (never searched BGE_IV/BGE_I): {len(bge_missed)}")
print(f"  7B_ (prefix not in routing):       {len(court_7b)}")
print(f"  1B_ (searched but wrong ones):     {len(court_1b)}")
print(f"  StPO (never searched these arts):  {len(stpo_missed)}")
print(f"  Other (StGB, StBOG, etc):          {len(other)}")
