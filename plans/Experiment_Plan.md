# Experiment Plan

## What this project does

Your AI agent receives a legal question and returns relevant legal citations.
This plan tests which features make the agent better or worse at finding correct citations.

## How we test

Turn features on/off one at a time. Measure scores. Compare against baseline (everything off).

## Features being tested

| ID | What's on | What it means |
|----|-----------|---------------|
| M0 | Nothing | Baseline — everything off |
| M1 | HyDE | Agent writes a fake answer first, uses it to search better |
| M2 | Few-shot | Give agent example queries to learn from |
| M3 | Type boost | Prioritize results matching the expected document type |
| M4 | Prompt injection | Add extra instructions into the agent prompt |
| M5 | CCH | Citation co-occurrence heuristic |
| M6-M15 | Combinations | Pairs and groups of the above |

## Fixed settings (do not change between runs)

- top_k_laws: 30
- top_k_courts: 30
- max_iterations: 4
- temperature: 0.0

These stay constant so score differences come only from feature changes.

## Scores we track

| Metric | What it tells you |
|--------|-------------------|
| Macro F1 | Average quality across all queries (treats each query equally) |
| Micro F1 | Overall quality (treats each citation equally) |
| Precision | Of what you returned, how much was correct |
| Recall | Of what was needed, how much you found |

## Run order

1. Run M0 on validation data → establishes baseline scores
2. Run M1–M5 on validation → measures each feature alone
3. Run M0 again → confirms baseline is stable
4. Run combinations (M6–M15) on validation
5. Pick best configs → run those on test data
6. Generate final submission

## Saving time (no recomputation)

Heavy work happens once and gets cached:
- Corpus loading → saved as .pkl file
- Embeddings → saved as .pkl file
- Model download → saved in models/ folder

After that, each experiment only runs the fast part: agent inference + scoring.

## Tracking tools

**MLflow** — logs every run's settings, scores, and output files.
- Installed and working locally (mlruns/ folder).
- You can compare runs side-by-side with `mlflow ui`.

**LangSmith** — records the agent's step-by-step reasoning per query.
- SDK installed, credentials in .env file.
- Blocked by corporate SSL proxy on FedEx network.
- Fallback: local agent_trace.jsonl captures same data.
- Will work from home or non-corporate network.

## How M0 baseline run works (step by step)

1. Load validation queries from CSV
2. Load corpus (cached .pkl files — no recomputation)
3. Set all feature toggles to OFF
4. For each query:
   - Agent receives the question
   - Agent searches laws and courts using BM25
   - Agent returns citation list
   - Log agent steps to agent_trace.jsonl
5. Compare predicted citations against gold labels
6. Compute macro/micro precision, recall, F1
7. Log all metrics to MLflow + local metrics.jsonl
8. Save predictions CSV as artifact

## Version control rules

- Check `git status` before every experiment (know what code version produced what score)
- One commit per logical change
- Push to GitHub after each working milestone
- Use feature branches + pull requests for bigger changes

## CI/CD

GitHub Actions automatically runs lint + tests when you open a pull request.
If checks fail, you fix before merging. This prevents broken code from entering main.

## Decision rule

A feature is considered helpful only if:
- It improves Macro F1 by at least +0.001 over baseline
- It does not collapse precision
- The improvement is consistent on re-run

## Final outputs

- `ablation_summary.csv` — one row per mode with all scores
- Best config identified and promoted to test
- Submission file generated from best config
