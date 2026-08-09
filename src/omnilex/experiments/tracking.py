from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class TrackingBackend:
    """Small tracking helper that uses MLflow if available, else local JSONL artifacts."""

    run_root: Path
    experiment_name: str = "omnilex_ablation"

    def __post_init__(self) -> None:
        self.run_root.mkdir(parents=True, exist_ok=True)

    def start_run(self, run_name: str, params: dict[str, Any]) -> dict[str, Any]:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + run_name
        run_dir = self.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": run_id,
            "run_name": run_name,
            "experiment_name": self.experiment_name,
            "started_at_utc": datetime.now(UTC).isoformat(),
            "params": params,
            "tracking_mode": "local_jsonl",
        }

        (run_dir / "run_meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"run_id": run_id, "run_dir": str(run_dir), "tracking_mode": "local_jsonl"}

    def log_metrics(self, run_dir: str | Path, metrics: dict[str, Any]) -> None:
        run_dir = Path(run_dir)
        line = {
            "ts_utc": datetime.now(UTC).isoformat(),
            "metrics": metrics,
        }
        with (run_dir / "metrics.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + os.linesep)

    def log_trace(self, run_dir: str | Path, trace_event: dict[str, Any]) -> None:
        run_dir = Path(run_dir)
        line = {
            "ts_utc": datetime.now(UTC).isoformat(),
            **trace_event,
        }
        with (run_dir / "agent_trace.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + os.linesep)

    def finalize_run(self, run_dir: str | Path, status: str = "completed") -> None:
        run_dir = Path(run_dir)
        done = {
            "ended_at_utc": datetime.now(UTC).isoformat(),
            "status": status,
        }
        (run_dir / "run_end.json").write_text(json.dumps(done, indent=2), encoding="utf-8")
