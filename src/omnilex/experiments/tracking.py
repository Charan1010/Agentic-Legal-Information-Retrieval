from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import mlflow

    _HAS_MLFLOW = True
except ImportError:
    _HAS_MLFLOW = False

try:
    from langsmith import traceable
    from langsmith.run_trees import RunTree

    _HAS_LANGSMITH = bool(os.getenv("LANGSMITH_API_KEY"))
except ImportError:
    _HAS_LANGSMITH = False


@dataclass
class TrackingBackend:
    """Experiment tracker. Uses MLflow when available, always writes local JSONL as backup."""

    run_root: Path
    experiment_name: str = "omnilex_ablation"
    _mlflow_run: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.run_root.mkdir(parents=True, exist_ok=True)
        if _HAS_MLFLOW:
            mlflow.set_experiment(self.experiment_name)

    @property
    def uses_mlflow(self) -> bool:
        return _HAS_MLFLOW

    @property
    def uses_langsmith(self) -> bool:
        return _HAS_LANGSMITH

    def start_run(self, run_name: str, params: dict[str, Any]) -> dict[str, Any]:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + run_name
        run_dir = self.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        tracking_mode = "mlflow" if _HAS_MLFLOW else "local_jsonl"

        # MLflow: start run and log params
        if _HAS_MLFLOW:
            self._mlflow_run = mlflow.start_run(run_name=run_name)
            flat_params = self._flatten_params(params)
            mlflow.log_params(flat_params)

        # Local backup
        payload = {
            "run_id": run_id,
            "run_name": run_name,
            "experiment_name": self.experiment_name,
            "started_at_utc": datetime.now(UTC).isoformat(),
            "params": params,
            "tracking_mode": tracking_mode,
        }
        (run_dir / "run_meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return {"run_id": run_id, "run_dir": str(run_dir), "tracking_mode": tracking_mode}

    def log_metrics(self, run_dir: str | Path, metrics: dict[str, Any]) -> None:
        run_dir = Path(run_dir)

        # MLflow
        if _HAS_MLFLOW and self._mlflow_run:
            mlflow.log_metrics(metrics)

        # Local backup
        line = {"ts_utc": datetime.now(UTC).isoformat(), "metrics": metrics}
        with (run_dir / "metrics.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + os.linesep)

    def log_artifact(self, run_dir: str | Path, file_path: str | Path) -> None:
        """Log a file as artifact to MLflow and copy to local run dir."""
        file_path = Path(file_path)
        if _HAS_MLFLOW and self._mlflow_run:
            mlflow.log_artifact(str(file_path))

    def log_trace(self, run_dir: str | Path, trace_event: dict[str, Any]) -> None:
        """Log agent trace event. Sends to LangSmith if configured, always writes local JSONL."""
        run_dir = Path(run_dir)
        line = {"ts_utc": datetime.now(UTC).isoformat(), **trace_event}
        with (run_dir / "agent_trace.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + os.linesep)

    def finalize_run(self, run_dir: str | Path, status: str = "completed") -> None:
        run_dir = Path(run_dir)

        # MLflow: end run
        if _HAS_MLFLOW and self._mlflow_run:
            mlflow.end_run(status="FINISHED" if status == "completed" else "FAILED")
            self._mlflow_run = None

        # Local backup
        done = {"ended_at_utc": datetime.now(UTC).isoformat(), "status": status}
        (run_dir / "run_end.json").write_text(json.dumps(done, indent=2), encoding="utf-8")

    @staticmethod
    def _flatten_params(params: dict[str, Any], prefix: str = "") -> dict[str, str]:
        """Flatten nested dict for MLflow params (which only accepts flat key-value)."""
        flat: dict[str, str] = {}
        for k, v in params.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            if isinstance(v, dict):
                flat.update(TrackingBackend._flatten_params(v, key))
            else:
                flat[key] = str(v)
        return flat
