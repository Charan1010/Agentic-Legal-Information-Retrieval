"""
Pipeline Scenario Simulator
----------------------------
Uses logged pipeline data to calculate P/R/F1 under different configurations
WITHOUT re-running the pipeline.

Run: python scripts/scenario_simulator.py
"""

# ═══════════════════════════════════════════════════════════
# DATA FROM pipeline_debug_log_v2.txt  (Query 1)
# ═══════════════════════════════════════════════════════════

GOLD = {
    "Art. 221 Abs. 1 StPO", "Art. 140 Abs. 1 StGB", "Art. 396 Abs. 1 StPO",
    "Art. 222 StPO", "Art. 393 Abs. 1 StPO", "Art. 382 Abs. 1 StPO",
    "Art. 385 Abs. 1 StPO", "Art. 221 Abs. 2 StPO", "Art. 227 Abs. 1 StPO",
    "Art. 212 Abs. 3 StPO", "Art. 390 Abs. 2 StPO", "Art. 422 Abs. 1 StPO",
    "Art. 422 Abs. 2 StPO", "Art. 428 Abs. 1 StPO", "Art. 135 Abs. 4 StPO",
    "Art. 100 Abs. 1 BGG", "Art. 135 Abs. 3 StPO", "Art. 37 Abs. 1 StBOG",
    "Art. 39 Abs. 1 StBOG",
    "BGE 137 IV 122 E. 6.2", "BGE 137 IV 122 E. 6.4", "BGE 137 IV 122 E. 4.2",
    "BGE 132 I 21 E. 3.2", "1B_210/2023 E. 4.1", "BGE 132 I 21 E. 3.2.2",
    "1B_536/2018 E. 5.1", "BGE 139 IV 270 E. 3.1", "BGE 133 I 168 E. 4.1",
    "BGE 143 IV 168 E. 5.1", "BGE 133 I 270 E. 3.4.2", "BGE 137 IV 122 E. 4.1",
    "BGE 132 I 21 E. 3.2.1", "1B_90/2021 E. 2.1", "1B_90/2021 E. 2.4",
    "7B_496/2025 E. 3.2", "7B_231/2025 E. 4.1", "7B_69/2024 E. 3.3.2",
    "7B_301/2024 E. 2.4", "7B_12/2025 E. 2.2", "1B_357/2022 E. 3.1",
    "1B_15/2023 E. 3.1", "1B_28/2022 E. 4.1",
}

# --- Direction 1: StPO laws (13 unique) ---
DIR1_CITATIONS = {
    "Art. 226 Abs. 4 StPO": 0.032,
    "Art. 227 Abs. 7 StPO": 0.031,
    "Art. 227 Abs. 4 StPO": 0.030,
    "Art. 227 Abs. 1 StPO": 0.030,
    "Art. 431 Abs. 2 StPO": 0.016,
    "Art. 212 Abs. 3 StPO": 0.016,
    "Art. 229 Abs. 3 StPO": 0.016,
    "Art. 226 Abs. 5 StPO": 0.016,
    "Art. 222 StPO": 0.015,
    "Art. 226 Abs. 3 StPO": 0.015,
    "Art. 229 Abs. 1 StPO": 0.028,
    "Art. 431 Abs. 3 StPO": 0.016,
    "Art. 314 Abs. 1 StPO": 0.015,
}

# --- Direction 2: 6B_ courts (22 unique) ---
DIR2_CITATIONS = {
    "6B_519/2022 E. 3.1": 0.016,
    "6B_1213/2016 E. 2.3": 0.016,
    "6B_187/2015 E. 5.5": 0.016,
    "6B_427/2015 E. 2.2": 0.016,
    "6B_631/2014 E. 2.3": 0.015,
    "6B_1500/2022 E. 3.4.3": 0.015,
    "6B_652/2017 E. 1": 0.015,
    "6B_1247/2022 E. 5.3": 0.015,
    "6B_1206/2017 E. 2.3": 0.014,
    "6B_1148/2023 E. 9.1": 0.014,
    "6B_368/2017 E. 6.2": 0.016,
    "6B_637/2025 E. 4.2": 0.016,
    "6B_390/2012 18.02.2013 E. 4.2": 0.016,
    "6B_1197/2015 E. 3.4.1": 0.016,
    "6B_416/2015 E. 1.2": 0.015,
    "6B_193/2020 19.08.2020 E. 5.2": 0.015,
    "6B_1046/2023 E. 2.1.2": 0.015,
    "6B_1148/2023 E. 7.1.2": 0.014,
    "6B_192/2020 E. 2.4": 0.014,
    "6B_742/2007 10.01.2008 E. 2": 0.014,
    "6B_1204/2015 E. 1.1": 0.015,
    "6B_1168/2020 E. 2.1": 0.014,
}

# --- Direction 3: BGG laws (25 unique) ---
DIR3_CITATIONS = {
    "Art. 78 Abs. 2 BGG": 0.030,
    "Art. 107 Abs. 3 BGG": 0.030,
    "Art. 43 BGG": 0.030,
    "Art. 103 Abs. 2 BGG": 0.030,
    "Art. 81 Abs. 1 BGG": 0.016,
    "Art. 100 Abs. 3 BGG": 0.016,
    "Art. 100 Abs. 2 BGG": 0.016,
    "Art. 47 Abs. 1 BGG": 0.016,
    "Art. 84 Abs. 1 BGG": 0.016,
    "Art. 130 Abs. 1 BGG": 0.015,
    "Art. 47 Abs. 2 BGG": 0.016,
    "Art. 123 Abs. 1 BGG": 0.015,
    "Art. 130 Abs. 2 BGG": 0.016,
    "Art. 124 Abs. 2 BGG": 0.015,
    "Art. 100 Abs. 5 BGG": 0.014,
    "Art. 38 Abs. 1 BGG": 0.014,
    "Art. 68 Abs. 4 BGG": 0.029,
    "Art. 99 Abs. 2 BGG": 0.016,
    "Art. 128 Abs. 3 BGG": 0.015,
    "Art. 93 Abs. 2 BGG": 0.016,
    "Art. 46 Abs. 2 BGG": 0.015,
    "Art. 100 Abs. 6 BGG": 0.016,
    "Art. 132 Abs. 2 BGG": 0.016,
    "Art. 70 Abs. 3 BGG": 0.016,
    "Art. 12 BGG": 0.014,
}

# --- Procedural defaults injected ---
DEFAULTS = {
    "Art. 42 Abs. 2 BGG": 0.300,
    "Art. 95 BGG": 0.300,
    "Art. 100 Abs. 1 BGG": 0.300,
    "Art. 105 Abs. 1 BGG": 0.300,
    "Art. 29 Abs. 2 BV": 0.300,
    "Art. 78 Abs. 1 BGG": 0.300,
    "Art. 80 Abs. 1 BGG": 0.300,
    "Art. 81 Abs. 1 BGG": 0.300,
    "Art. 50 StGB": 0.300,
}

# --- Explicit from question text ---
EXPLICIT = {"Art. 221 Abs. 1 lit. b StPO"}  # Note: gold has "Art. 221 Abs. 1 StPO" (no "lit. b")


# ═══════════════════════════════════════════════════════════
# SCORING HELPERS
# ═══════════════════════════════════════════════════════════

def calc_metrics(predicted: set, gold: set):
    """Precision, Recall, F1"""
    tp = predicted & gold
    p = len(tp) / len(predicted) if predicted else 0
    r = len(tp) / len(gold) if gold else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    return {"P": p, "R": r, "F1": f1, "TP": tp, "predicted": len(predicted), "gold": len(gold)}


def print_scenario(name: str, desc: str, predicted: set, gold: set):
    m = calc_metrics(predicted, gold)
    print(f"\n{'─'*70}")
    print(f"  SCENARIO: {name}")
    print(f"  {desc}")
    print(f"{'─'*70}")
    print(f"  Predicted: {m['predicted']}  |  Gold: {m['gold']}")
    print(f"  Precision: {m['P']:.4f}  ({len(m['TP'])}/{m['predicted']})")
    print(f"  Recall:    {m['R']:.4f}  ({len(m['TP'])}/{m['gold']})")
    print(f"  F1:        {m['F1']:.4f}")
    if m['TP']:
        print(f"  Hits: {sorted(m['TP'])}")
    # Show which gold items were available in pool but missed
    available_pool = set(DIR1_CITATIONS) | set(DIR2_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS)
    missed_but_available = (gold - predicted) & available_pool
    if missed_but_available:
        print(f"  Gold in pool but not selected ({len(missed_but_available)}): {sorted(missed_but_available)}")
    return m


# ═══════════════════════════════════════════════════════════
# SCENARIOS
# ═══════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("  PIPELINE SCENARIO SIMULATOR (from debug log v2)")
    print("  Query 1: Haftverlängerung / Kollusionsgefahr")
    print("  Gold count: 42")
    print("="*70)

    # ─── BASELINE (actual pipeline output) ───
    actual_output = {
        "Art. 29 Abs. 2 BV", "Art. 78 Abs. 1 BGG", "Art. 80 Abs. 1 BGG",
        "Art. 50 StGB", "Art. 226 Abs. 4 StPO", "Art. 227 Abs. 7 StPO",
        "Art. 227 Abs. 4 StPO", "Art. 227 Abs. 1 StPO", "Art. 431 Abs. 2 StPO",
        "Art. 212 Abs. 3 StPO",
    }
    print_scenario("BASELINE (actual run)", 
                   "As-is: reranker broken (all scores 0.0097), fallback to top-10 by RRF",
                   actual_output, GOLD)

    # ─── SCENARIO A: No reranker, keep ALL retrieved + defaults ───
    all_retrieved = set(DIR1_CITATIONS) | set(DIR2_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS)
    print_scenario("A: No Reranker — keep all 60 unique + defaults",
                   "Just pass through everything search found (no filtering)",
                   all_retrieved, GOLD)

    # ─── SCENARIO B: No reranker, top-K by RRF score ───
    # Merge all with their best RRF score
    all_scored = {}
    for d in [DIR1_CITATIONS, DIR2_CITATIONS, DIR3_CITATIONS, DEFAULTS]:
        for cite, score in d.items():
            all_scored[cite] = max(all_scored.get(cite, 0), score)
    
    for k in [10, 20, 30, 40, 60]:
        top_k = set(sorted(all_scored, key=all_scored.get, reverse=True)[:k])
        print_scenario(f"B-{k}: No Reranker — top-{k} by RRF score",
                       f"Sort by RRF, take top {k}",
                       top_k, GOLD)

    # ─── SCENARIO C: Disable Direction 2 (6B_ which is WRONG) ───
    without_6b = set(DIR1_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS)
    print_scenario("C: Drop Direction 2 (wrong 6B_ direction)",
                   "Remove all 6B_ results — they're sentencing, not detention",
                   without_6b, GOLD)

    # ─── SCENARIO D: Only defaults (no search at all) ───
    print_scenario("D: Only procedural defaults",
                   "What if we ONLY had the hard-coded defaults + explicit?",
                   set(DEFAULTS) | EXPLICIT, GOLD)

    # ─── SCENARIO E: Only Direction 1 (StPO laws) ───
    print_scenario("E: Only Direction 1 (StPO laws)",
                   "Just the StPO direction results",
                   set(DIR1_CITATIONS), GOLD)

    # ─── SCENARIO F: Direction 1 + defaults ───
    print_scenario("F: Direction 1 + defaults",
                   "StPO search + procedural defaults",
                   set(DIR1_CITATIONS) | set(DEFAULTS), GOLD)

    # ─── SCENARIO G: HYPOTHETICAL — if Direction 2 had been 1B_/7B_ ───
    # What IF the planner chose 1B_ and we found the right court cases?
    # Gold has 7 cases from 1B_ and 5 from 7B_. Assume we'd find ~50% of them.
    hypothetical_1b = {
        "1B_210/2023 E. 4.1", "1B_536/2018 E. 5.1", "1B_90/2021 E. 2.1",
        "1B_90/2021 E. 2.4", "1B_357/2022 E. 3.1", "1B_15/2023 E. 3.1",
        "1B_28/2022 E. 4.1",
    }
    hypothetical_7b = {
        "7B_496/2025 E. 3.2", "7B_231/2025 E. 4.1", "7B_69/2024 E. 3.3.2",
        "7B_301/2024 E. 2.4", "7B_12/2025 E. 2.2",
    }
    hypothetical_bge = {
        "BGE 137 IV 122 E. 6.2", "BGE 137 IV 122 E. 4.2", "BGE 137 IV 122 E. 4.1",
        "BGE 132 I 21 E. 3.2", "BGE 139 IV 270 E. 3.1", "BGE 143 IV 168 E. 5.1",
    }
    
    # Conservative: find ~50% of 1B_ + ~40% of 7B_ (they're smaller corpus)
    hyp_found_1b = {"1B_210/2023 E. 4.1", "1B_90/2021 E. 2.1", "1B_357/2022 E. 3.1", "1B_28/2022 E. 4.1"}
    hyp_found_7b = {"7B_496/2025 E. 3.2", "7B_231/2025 E. 4.1"}
    hyp_found_bge = {"BGE 137 IV 122 E. 4.2", "BGE 139 IV 270 E. 3.1", "BGE 143 IV 168 E. 5.1"}
    
    scenario_g = set(DIR1_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS) | hyp_found_1b | hyp_found_7b | hyp_found_bge
    print_scenario("G: HYPOTHETICAL — correct planner (1B_/7B_/BGE_IV instead of 6B_)",
                   "If planner chose 1B_+7B_+BGE_IV, assume ~50% recall on those corpora",
                   scenario_g, GOLD)

    # ─── SCENARIO H: Hypothetical best case (correct planner + good recall) ───
    # Assume: 80% of 1B_/7B_ found + all BGE + more StPO articles
    extra_stpo = {
        "Art. 221 Abs. 1 StPO", "Art. 221 Abs. 2 StPO", "Art. 222 StPO",
        "Art. 382 Abs. 1 StPO", "Art. 393 Abs. 1 StPO", "Art. 396 Abs. 1 StPO",
        "Art. 135 Abs. 3 StPO", "Art. 135 Abs. 4 StPO",
    }
    scenario_h = (set(DIR1_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS) 
                  | hypothetical_1b | hypothetical_7b | hypothetical_bge
                  | extra_stpo | {"Art. 140 Abs. 1 StGB", "Art. 100 Abs. 1 BGG",
                                  "Art. 37 Abs. 1 StBOG", "Art. 39 Abs. 1 StBOG"})
    print_scenario("H: BEST CASE — correct planner + broader StPO search + all defaults",
                   "Optimistic: correct court dirs + deeper StPO recall + StBOG + StGB",
                   scenario_h, GOLD)

    # ─── SCENARIO I: Lower reranker cutoff (0.005 instead of 0.2) ───
    # All items scored 0.0096-0.0097, so ANY cutoff < 0.009 passes everything
    print_scenario("I: Reranker cutoff = 0.005 (effectively disabled)",
                   "Same as A — all 0.0097 scores pass, so everything comes through",
                   all_retrieved, GOLD)

    # ─── SUMMARY TABLE ───
    print("\n\n" + "="*70)
    print("  SUMMARY TABLE")
    print("="*70)
    print(f"  {'Scenario':<55} {'P':>6} {'R':>6} {'F1':>6} {'#pred':>5}")
    print(f"  {'─'*55} {'─'*6} {'─'*6} {'─'*6} {'─'*5}")
    
    scenarios = [
        ("BASELINE (actual)", actual_output),
        ("A: No reranker (all through)", all_retrieved),
        ("B-10: Top-10 by RRF", set(sorted(all_scored, key=all_scored.get, reverse=True)[:10])),
        ("B-20: Top-20 by RRF", set(sorted(all_scored, key=all_scored.get, reverse=True)[:20])),
        ("B-30: Top-30 by RRF", set(sorted(all_scored, key=all_scored.get, reverse=True)[:30])),
        ("B-60: Top-60 by RRF", set(sorted(all_scored, key=all_scored.get, reverse=True)[:60])),
        ("C: Drop 6B_ direction", without_6b),
        ("D: Only defaults", set(DEFAULTS) | EXPLICIT),
        ("E: Only Dir1 (StPO)", set(DIR1_CITATIONS)),
        ("F: Dir1 + defaults", set(DIR1_CITATIONS) | set(DEFAULTS)),
        ("G: HYPO correct planner (conservative)", scenario_g),
        ("H: HYPO best case", scenario_h),
        ("I: Reranker cutoff=0.005", all_retrieved),
    ]
    
    for name, pred in scenarios:
        m = calc_metrics(pred, GOLD)
        print(f"  {name:<55} {m['P']:>6.3f} {m['R']:>6.3f} {m['F1']:>6.3f} {m['predicted']:>5}")

    # ─── KEY INSIGHTS ───
    print("\n\n" + "="*70)
    print("  KEY INSIGHTS")
    print("="*70)
    
    # How many gold items were NEVER retrieved by any direction?
    all_pool = set(DIR1_CITATIONS) | set(DIR2_CITATIONS) | set(DIR3_CITATIONS) | set(DEFAULTS)
    gold_found = GOLD & all_pool
    gold_missed = GOLD - all_pool
    print(f"\n  Gold items found by search: {len(gold_found)}/42")
    print(f"  Gold items NEVER retrieved: {len(gold_missed)}/42")
    print(f"  → These can NEVER be found without fixing upstream (planner/directions):")
    for c in sorted(gold_missed):
        print(f"      ✗ {c}")
    
    print(f"\n  Gold items that WERE retrieved but got filtered out:")
    gold_retrieved_but_filtered = gold_found - actual_output
    for c in sorted(gold_retrieved_but_filtered):
        print(f"      ~ {c}  (was available, lost in reranker/selection)")

    # What's the CEILING for this pipeline without fixing planner?
    print(f"\n  ─── CEILING ANALYSIS ───")
    print(f"  Max possible recall (if we kept ALL retrieved): {len(gold_found)}/{len(GOLD)} = {len(gold_found)/len(GOLD):.3f}")
    print(f"  This means: even with PERFECT reranker, max F1 is limited by what search finds.")
    print(f"  The planner/direction choices cap us at {len(gold_found)/len(GOLD)*100:.1f}% recall ceiling.")


if __name__ == "__main__":
    main()
