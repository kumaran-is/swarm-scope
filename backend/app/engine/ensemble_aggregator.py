"""
Ensemble aggregator: compute statistics across multiple simulation runs using numpy.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def aggregate_kpi_trajectories(
    runs_kpi_data: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    Given KPI data from multiple runs (each run = list of {tick, kpi_name: value} dicts),
    compute mean, std, confidence bands, and robustness scores.

    Args:
        runs_kpi_data: list of runs, where each run is a list of tick records

    Returns:
        {kpi_name: {mean: [...], std: [...], lower_95: [...], upper_95: [...], robustness: float}}
    """
    if not runs_kpi_data:
        return {}

    # Collect all KPI names
    kpi_names: set[str] = set()
    for run in runs_kpi_data:
        for tick_data in run:
            kpi_names.update(k for k in tick_data if k != "tick")

    max_ticks = max((len(run) for run in runs_kpi_data), default=0)
    result: dict[str, Any] = {}

    for kpi_name in kpi_names:
        # Build matrix: runs x ticks
        matrix = []
        for run in runs_kpi_data:
            values = [tick_data.get(kpi_name, 0.0) for tick_data in run]
            # Pad to max_ticks if needed
            if len(values) < max_ticks:
                values.extend([values[-1] if values else 0.0] * (max_ticks - len(values)))
            matrix.append(values[:max_ticks])

        arr = np.array(matrix, dtype=np.float64)
        mean = arr.mean(axis=0).tolist()
        std = arr.std(axis=0).tolist()
        lower_95 = (arr.mean(axis=0) - 1.96 * arr.std(axis=0)).tolist()
        upper_95 = (arr.mean(axis=0) + 1.96 * arr.std(axis=0)).tolist()

        # Robustness: 1 - (coefficient of variation at final tick)
        final_values = arr[:, -1] if arr.shape[1] > 0 else np.array([0.0])
        final_mean = float(final_values.mean())
        final_std = float(final_values.std())
        robustness = 1.0 - (final_std / (abs(final_mean) + 1e-8))
        robustness = round(max(0.0, min(1.0, robustness)), 3)

        result[kpi_name] = {
            "mean": mean,
            "std": std,
            "lower_95": lower_95,
            "upper_95": upper_95,
            "robustness": robustness,
            "num_runs": len(runs_kpi_data),
        }
        logger.debug(
            "KPI %s aggregated: robustness=%.3f, final_mean=%.2f±%.2f",
            kpi_name, robustness, final_mean, final_std,
        )

    return result


def compute_robustness_score(kpi_statistics: dict[str, Any]) -> float:
    """
    Aggregate robustness score across all KPIs (simple mean of per-KPI robustness).
    Returns float 0.0-1.0.
    """
    if not kpi_statistics:
        return 0.0
    scores = [v.get("robustness", 0.0) for v in kpi_statistics.values()]
    return round(float(np.mean(scores)), 3)
