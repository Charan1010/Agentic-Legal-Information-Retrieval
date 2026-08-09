# What We Are Doing

We built an AI agent that finds legal citations.
Now we want to scientifically test which features help and which hurt.
We track everything properly so results are trustworthy and reproducible.

## The Tools We Use

| Tool | What it does |
|------|-------------|
| Git + GitHub | Tracks code changes, enables collaboration and rollback |
| MLflow | Logs experiment configs, scores, and output files in one dashboard |
| LangSmith | Shows what the AI agent did step-by-step inside each query |
| GitHub Actions | Automatically checks code quality on every pull request |

## The Order We Follow

### Done: Setup
- [x] Created git repo and pushed to GitHub
- [x] Generated experiment plan table (run_matrix.csv)
- [x] Reviewed tracking file structure (run_meta, metrics, run_end)

### Done: Tracking tools
- [x] Installed MLflow (working, logs to local mlruns/)
- [x] Installed LangSmith SDK (blocked by corporate SSL — will use local traces)
- [x] Created .env file with credentials (git-ignored)
- [x] Updated tracking.py to log to MLflow + local JSONL
- [x] Verified: test run appears in MLflow with params and metrics

### NOW: Run M0 baseline experiment
- [ ] Run notebook 03 with all features OFF on validation data
- [ ] Verify MLflow logs macro_f1, micro_f1, precision, recall
- [ ] Verify local agent_trace.jsonl captures agent steps
- [ ] Commit tracking code changes and push to GitHub

### Next: Single-feature ablation (M1–M5)
- [ ] Run M1 (HyDE only) on validation
- [ ] Run M2 (Few-shot only) on validation
- [ ] Run M3 (Type boost only) on validation
- [ ] Run M4 (Prompt injection only) on validation
- [ ] Run M5 (CCH only) on validation
- [ ] Compare all scores against M0 baseline

### After that: CI/CD and version control practice
- [ ] Add GitHub Actions workflow for lint + tests
- [ ] Create a feature branch, open PR, pass CI, merge

### Finally: Full ablation
- [ ] Run combination modes (M6–M15) on validation
- [ ] Pick best configs → run on test data
- [ ] Generate final submission

## Key Concepts (short definitions)

**run_matrix.csv** — A table listing all experiments to run. Each row = one experiment with specific settings.

**run_meta.json** — Saved at start of each run. Records what settings were used and when.

**metrics.jsonl** — Scores get appended here during/after each run. One line per log event.

**run_end.json** — Saved when a run finishes. Records success/failure and end time.

**MLflow** — Dashboard where you compare runs side by side (scores, settings, files).

**LangSmith** — Dashboard where you see the AI agent's thinking steps for each query.

**CI/CD** — Automated checks that run on every code change to catch mistakes early.

**Feature ablation** — Turn features on/off one at a time to measure each one's impact.

## When to push to GitHub

Push after each milestone:
1. After tracking tools are installed and working
2. After first real experiment completes successfully
3. After CI workflow is added and passing
