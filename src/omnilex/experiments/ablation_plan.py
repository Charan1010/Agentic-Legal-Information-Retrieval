from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExperimentMode:
    name: str
    description: str
    toggles: dict[str, bool]


def build_default_modes() -> list[ExperimentMode]:
    """Build the baseline -> all-on mode matrix from the project ablation plan."""
    return [
        ExperimentMode("M0", "all_off_baseline", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M1", "hyde_only", {
            "use_hyde": True,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M2", "few_shot_only", {
            "use_hyde": False,
            "use_few_shot": True,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M3", "type_boost_only", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": True,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M4", "prompt_injection_only", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": True,
            "use_cch": False,
        }),
        ExperimentMode("M5", "cch_only", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": True,
        }),
        ExperimentMode("M6", "hyde_plus_few_shot", {
            "use_hyde": True,
            "use_few_shot": True,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M7", "hyde_plus_type_boost", {
            "use_hyde": True,
            "use_few_shot": False,
            "use_type_boost": True,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M8", "hyde_plus_prompt_injection", {
            "use_hyde": True,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": True,
            "use_cch": False,
        }),
        ExperimentMode("M9", "hyde_plus_cch", {
            "use_hyde": True,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": False,
            "use_cch": True,
        }),
        ExperimentMode("M10", "type_boost_plus_prompt_injection", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": True,
            "use_prompt_injection": True,
            "use_cch": False,
        }),
        ExperimentMode("M11", "type_boost_plus_cch", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": True,
            "use_prompt_injection": False,
            "use_cch": True,
        }),
        ExperimentMode("M12", "prompt_injection_plus_cch", {
            "use_hyde": False,
            "use_few_shot": False,
            "use_type_boost": False,
            "use_prompt_injection": True,
            "use_cch": True,
        }),
        ExperimentMode("M13", "hyde_few_shot_type_boost", {
            "use_hyde": True,
            "use_few_shot": True,
            "use_type_boost": True,
            "use_prompt_injection": False,
            "use_cch": False,
        }),
        ExperimentMode("M14", "hyde_few_shot_type_boost_prompt_injection", {
            "use_hyde": True,
            "use_few_shot": True,
            "use_type_boost": True,
            "use_prompt_injection": True,
            "use_cch": False,
        }),
        ExperimentMode("M15", "all_on", {
            "use_hyde": True,
            "use_few_shot": True,
            "use_type_boost": True,
            "use_prompt_injection": True,
            "use_cch": True,
        }),
    ]


def build_run_matrix(
    dataset_modes: list[str] | None = None,
    base_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Create run records combining mode toggles with val/test dataset regimes."""
    if dataset_modes is None:
        dataset_modes = ["val", "test"]
    if base_config is None:
        base_config = {}

    records: list[dict[str, Any]] = []
    for ds_mode in dataset_modes:
        for mode in build_default_modes():
            record = {
                "dataset_mode": ds_mode,
                "mode_id": mode.name,
                "mode_name": mode.description,
                **base_config,
                **mode.toggles,
            }
            records.append(record)
    return records


def mode_to_dict(mode: ExperimentMode) -> dict[str, Any]:
    return asdict(mode)
