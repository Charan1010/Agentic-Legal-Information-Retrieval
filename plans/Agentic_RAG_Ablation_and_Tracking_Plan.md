# Agentic RAG Ablation + Tracking Plan (Validation + Test)

## 1) Objective
Run feature-isolated experiments to identify exactly which features produce gains or losses, across both validation and test data, while minimizing recomputation and maximizing traceability.

Primary outcomes:
- Reliable feature attribution (main effects and interactions).
- Repeatable runs with stable configs and immutable run metadata.
- Full audit trail for agent behavior, retrieval behavior, and final metrics.

## 2) What We Reuse From Existing Notebooks

### 2.1 Patterns already present in `03_hyde_kaggle.ipynb`
- Persistent checkpoint dataset push with hard-fail semantics (`_save_checkpoint`, `_push_to_dataset`).
- Corpus-level cache (`corpus_documents.pkl`) to avoid CSV reload/reparse.
- Embedding caches (`faiss_laws_qwen3_embeddings.pkl`, `faiss_courts_qwen3_embeddings.pkl`).
- Disk-backed HyDE cache (`hyde_cache.pkl`) with periodic autosave.
- Prediction checkpointing for test and validation loops.
- Fresh-run guard comments when logic changes.

### 2.2 Patterns already present in `04_planner_director.ipynb`
- Same durable checkpointing discipline into `rag-checkpoints-v2`.
- Cache-first corpus loading and sampled-courts strategy.
- Deferred model loading to reduce VRAM pressure.
- Incremental progress save for submission and debug logs.
- Taxonomy cache for prompt/routing context assembly.

### 2.3 Gap to close
- There is no dedicated experiment tracking framework yet (no MLflow/W&B/LangSmith wiring in current runs).

## 3) Recommended Tracking Stack (Best Available for LLM + Agents)

Use a two-layer tracking design:

### Layer A: Metrics + Config + Artifacts
- **MLflow** as the canonical experiment registry.
- Track per run:
	- Full feature flags and non-feature hyperparameters.
	- Validation and test outputs.
	- Runtime stats (duration, cache hit rates, token counts if available).
- Artifacts:
	- Predictions CSV.
	- Per-query diagnostics CSV.
	- Run summary JSON.
	- Agent logs JSONL.

### Layer B: Agent/LLM Traces
- **LangSmith** (preferred if API key available) for step-level traces.
- If SaaS is unavailable, fallback to local structured traces:
	- JSONL trace per query (thought/action/observation/tool/results/final citations).
	- Attach JSONL to MLflow artifact store.

Why this combo:
- MLflow is strongest for experiment comparability and artifact lineage.
- LangSmith (or structured JSONL fallback) is strongest for agent-path debugging and prompt/tool analysis.

## 4) Data Regimes and Run Policy

We need both regimes:

- **Validation regime (`val`)**:
	- Used for all feature-attribution decisions.
	- Produces Macro/Micro P/R/F1 and per-query TP/FP/FN deltas.

- **Test regime (`test`)**:
	- Used to generate submission artifacts for selected candidates only.
	- No gold labels, so compare operational metrics and stability, not F1.

Policy:
- Do not tune on test outputs.
- Select top candidate configs from validation first, then run those on test.

## 5) Experiment Matrix

### 5.1 Single-feature attribution (must run first)
- M0: all OFF (baseline parity)
- M1: HyDE ON only
- M2: Few-shot ON only
- M3: Type boost ON only
- M4: Prompt injection ON only
- M5: CCH ON only

### 5.2 Pair interactions
- M6: HyDE + Few-shot
- M7: HyDE + Type boost
- M8: HyDE + Prompt injection
- M9: HyDE + CCH
- M10: Type boost + Prompt injection
- M11: Type boost + CCH
- M12: Prompt injection + CCH

### 5.3 Higher-order interactions
- M13: HyDE + Few-shot + Type boost
- M14: HyDE + Few-shot + Type boost + Prompt injection
- M15: all ON

## 6) Recomputation Avoidance Strategy (Critical)

Use strict phase boundaries so heavy artifacts are built once and reused.

### Phase A: Build and freeze heavy assets (once)
- Corpus cache creation/loading.
- FAISS embedding creation/loading.
- Model downloads and tokenizer/model init checks.
- Persist checkpoints immediately after completion.

### Phase B: Fast ablations (repeat many times)
- Reuse all Phase A outputs.
- Change only feature toggles and run inference/evaluation loops.
- Keep `FORCE_REBUILD_INDICES = False`.
- Never clear caches unless pipeline logic changes.

### Phase C: Finalists on test
- Run only selected top configs from validation.
- Save submission and run metadata as immutable artifacts.

### Stop/restart boundaries
- Safe restart points are after each saved checkpoint batch.
- If interrupted, resume from latest predictions checkpoint for the same mode.
- If code logic changed, force a fresh run for that mode and bump run version.

## 7) “No Confounders” Controls

Pin the following across all modes unless explicitly studying them:
- `top_k_laws`, `top_k_courts`
- `max_iterations`, `max_tokens`
- `max_observation_chars`, `max_conversation_chars`
- Corpus sample size / subset policy
- Temperature policy (prefer `0.0` for deterministic ablations)

Also lock:
- Prompt templates (except when prompt injection is the variable under test).
- Tool routing logic version.

## 8) Run Metadata Schema (Per Run)

Required fields:
- `run_name`, `run_id`, `timestamp_utc`
- `git_or_notebook_version` (manual string if no git hash available)
- `dataset_mode` (`val` or `test`)
- Full `CONFIG` snapshot
- `cache_manifest`:
	- corpus cache file + checksum/size
	- embeddings cache files + checksum/size
	- hyde cache file + checksum/size
- Timing:
	- setup_duration
	- inference_duration
	- evaluation_duration (val only)

Validation metrics:
- Macro precision/recall/F1
- Micro precision/recall/F1
- Per-query TP/FP/FN and per-query F1

Operational metrics:
- number_of_queries
- citations_per_query stats
- hyde_cache_hit_rate (if HyDE enabled)

## 9) Analysis Method

### Main effects
- Compare each single-feature mode against M0.
- Report absolute delta and relative delta for Macro F1.

### Interaction effects
- For X and Y:
	- `synergy = F1(XY) - F1(M0) - (F1(X)-F1(M0)) - (F1(Y)-F1(M0))`

### Loss diagnosis
- For any negative delta:
	- inspect query-level delta table
	- classify as precision-driven (FP up), recall-driven (FN up), or both

## 10) Validation-to-Test Promotion Rules

Promote config to test only if:
- Macro F1 improvement is consistent and above threshold.
- No severe precision collapse.
- Behavior is stable across reruns (if non-deterministic).

Suggested threshold:
- meaningful gain: `+0.001` Macro F1 or more over M0.

## 11) Execution Order

1. Run M0 on validation.
2. Run M1-M5 on validation.
3. Re-run M0 (stability check).
4. Run M6-M12 on validation.
5. Run M13-M15 on validation.
6. Rank and select finalists.
7. Run finalists on test.
8. Export final comparison report.

## 12) Deliverables

- `ablation_summary.csv`: one row per mode.
- `ablation_query_deltas.csv`: query-level diagnostics vs baseline.
- `ablation_report.md`: conclusions, gains/losses, and chosen production config.
- Test submission files for promoted modes.
- Full trace artifacts (LangSmith links or JSONL logs).

## 13) Immediate Next Implementation Tasks

1. Add MLflow run wrapper around evaluation in `03_hyde_retrieval.ipynb`.
2. Add a mode registry list and loop runner (validation and test passes).
3. Add structured trace writer (JSONL) if LangSmith is not configured.
4. Add cache manifest logger and run fingerprint.
5. Add final ranking table + promotion filter to test.

