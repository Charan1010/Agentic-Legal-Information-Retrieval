# Notebook Features, Toggles, Evolution, and Scores

Purpose: one place to compare Notebook 01, Notebook 02, and Notebook 03 evolution, plus validation and leaderboard scores.

Last updated: 2026-08-05

---

## 1) Notebook 01 - Direct Generation Baseline

Notebook: notebooks/01_direct_generation_baseline.ipynb

Core features:
- Direct LLM citation generation from model memory
- No retrieval layer
- No search tools
- No corpus grounding
- No planner/agent loop over tool calls

What this means:
- Very low recall on exact Swiss legal citations
- Some hallucinated citations
- Useful as a minimal baseline

---

## 2) Notebook 02 - Agentic BM25 Baseline

Notebook: notebooks/02_agentic_retrieval_baseline.ipynb

Core features:
- ReAct-style agent loop
- Two BM25 tools:
  - search_laws
  - search_courts
- German-oriented search behavior
- Multi-iteration tool calling and citation accumulation
- Observation truncation for context-budget control

What this changed vs Notebook 01:
- Added retrieval and tool usage
- Increased recall (more true positives found)
- But also increased false positives due to large raw result dumps

Note on toggles:
- Notebook 02 did not originally use the feature-toggle framework.
- The toggle framework was introduced in Notebook 03 to reproduce Notebook 02 baseline and then add features one by one.

---

## 3) Toggle Framework Introduced for Notebook 03

Notebook: notebooks/03_hyde_retrieval.ipynb

Current feature toggles available:
- hyde_enabled
- few_shot_enabled
- type_boost_enabled
- prompt_injection_enabled
- cch_enabled

Also implemented for clean ablation:
- Baseline parity mode:
  - If hyde_enabled=False, few_shot_enabled=False, type_boost_enabled=False,
    then Notebook 03 uses Notebook-02 style baseline tools.

Practical interpretation:
- You can start from Notebook 02-equivalent behavior in Notebook 03,
  then enable one feature at a time and measure delta.

---

## 4) Further Evolution in Notebook 03

Notebook: notebooks/03_hyde_retrieval.ipynb

Feature evolution direction:
1. Notebook 02 retrieval baseline behavior (via baseline parity mode)
2. Optional prompt injection (type registry guidance)
3. HyDE document generation
4. Few-shot domain-matched support for HyDE
5. Type-boosted hierarchical retrieval
6. Optional CCH-style output formatting

Important separation for analysis:
- Retrieval behavior toggles:
  - hyde_enabled
  - few_shot_enabled
  - type_boost_enabled
- Prompt behavior toggle:
  - prompt_injection_enabled
- Output formatting toggle:
  - cch_enabled

This separation enables controlled experiments:
- Retrieval quality changes can be measured independently from prompt-context changes and output-format changes.

---

## 5) Scoreboard (Val + Public + Private)

Source files:
- Evaluation Results/01_direct_generation_val_results.md
- Evaluation Results/02_agentic_retrieval_val_results.md
- Evaluation Results/03_hyde_retrieval_ablation_results.md

### Primary metric: Macro F1

| Notebook / Mode | Val Macro F1 | Public LB | Private LB |
|---|---:|---:|---:|
| Notebook 01 (Direct generation) | 0.0200 | 0.02435 | 0.02842 |
| Notebook 02 (Agentic BM25 baseline) | 0.0152 | 0.00439 | 0.00731 |
| Notebook 03 Test 1 (All OFF, historical ablation record) | 0.0017 | TBD | TBD |

### Additional validation metrics (where recorded)

Notebook 01:
- Macro precision/recall: not reported in that file

Notebook 02:
- Macro precision: 0.0091
- Macro recall: 0.0571
- Micro F1: 0.0138
- Micro precision: 0.0083
- Micro recall: 0.0398

Notebook 03 Test 1 (historical ablation record):
- Macro precision: 0.0010
- Macro recall: 0.0091
- Micro F1: 0.0012
- Micro precision: 0.0007
- Micro recall: 0.0040

---

## 6) Recommended Ablation Run Order (Clean Story)

Use this exact order in Notebook 03:
1. Baseline parity (all retrieval features OFF, prompt OFF, CCH OFF)
2. Prompt injection only
3. CCH only
4. HyDE only
5. HyDE + few-shot
6. Type boost only
7. All ON

Suggested naming for logged results:
- test_1_baseline_parity
- test_2_prompt_only
- test_3_cch_only
- test_4_hyde_only
- test_5_hyde_fewshot
- test_6_type_boost_only
- test_7_all_on

---

## 7) Notes on Comparability

To make scores comparable across runs:
- Keep the same split and query order
- Restart kernel before each test set of runs
- Keep model/config constants fixed except the target toggle(s)
- Record exact toggle values in the results table for every run

If leaderboard values are missing for Notebook 03 tests, mark them explicitly as TBD until submitted.
