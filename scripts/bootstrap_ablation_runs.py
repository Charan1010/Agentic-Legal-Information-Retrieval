from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from omnilex.experiments.ablation_plan import build_run_matrix
from omnilex.experiments.tracking import TrackingBackend


OUTPUT_ROOT = Path("output") / "experiments"


def main() -> None:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = OUTPUT_ROOT / f"ablation_batch_{stamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    base_config = {
        "max_iterations": 4,
        "temperature": 0.0,
        "top_k_laws": 30,
        "top_k_courts": 30,
    }
    records = build_run_matrix(dataset_modes=["val", "test"], base_config=base_config)

    csv_path = batch_dir / "run_matrix.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    (batch_dir / "run_matrix.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    tracker = TrackingBackend(run_root=batch_dir / "runs")
    bootstrap = tracker.start_run(
        run_name="bootstrap",
        params={
            "record_count": len(records),
            "dataset_modes": ["val", "test"],
            "base_config": base_config,
        },
    )
    tracker.log_metrics(
        bootstrap["run_dir"],
        {
            "mode_count": len({r["mode_id"] for r in records}),
            "run_count": len(records),
        },
    )
    tracker.finalize_run(bootstrap["run_dir"])

    print(f"Created ablation batch: {batch_dir}")
    print(f"Run matrix: {csv_path}")


if __name__ == "__main__":
    main()
