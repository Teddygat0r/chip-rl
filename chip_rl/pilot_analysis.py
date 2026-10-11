"""Descriptive analysis of an explicitly joined physical pilot table.

This module deliberately has no dependency on the pilot runner or worker output.
The caller supplies every attempted physical row, including failed attempts.
Nothing here establishes physical signoff, proxy calibration, Fmax, or policy
learning.  The statistics are descriptive and do not produce p-values or
confidence intervals.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any, Sequence


SCHEMA = "chip-rl-physical-pilot-analysis-v1"
REQUIRED_FIELDS = (
    "family", "config", "reference_name", "source_sha256", "generic_cells",
    "physical_stdcell_area_um2", "physical_stage", "finite_pre_route_checked",
    "route_completed",
)


def average_ranks(values: Sequence[float]) -> list[float]:
    """Return one-based ranks, averaging the occupied positions for ties."""
    ranks = [0.0] * len(values)
    positions = sorted(range(len(values)), key=lambda index: values[index])
    offset = 0
    while offset < len(values):
        end = offset + 1
        while end < len(values) and values[positions[end]] == values[positions[offset]]:
            end += 1
        average = (offset + 1 + end) / 2
        for position in positions[offset:end]:
            ranks[position] = average
        offset = end
    return ranks


def spearman_rank_correlation(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Pearson correlation of average ranks; undefined cases return None."""
    if len(x) != len(y):
        raise ValueError("rank vectors have different lengths")
    if len(x) < 2:
        return None
    for value in (*x, *y):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("rank vectors must contain only finite numbers")
    rx, ry = average_ranks(x), average_ranks(y)
    mean_x, mean_y = sum(rx) / len(rx), sum(ry) / len(ry)
    cross = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    xx = sum((a - mean_x) ** 2 for a in rx)
    yy = sum((b - mean_y) ** 2 for b in ry)
    if xx == 0 or yy == 0:
        return None
    return max(-1.0, min(1.0, cross / math.sqrt(xx * yy)))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _positive_number(value: Any) -> bool:
    return _finite_number(value) and value > 0


def _nonnegative_number(value: Any) -> bool:
    return _finite_number(value) and value >= 0


def _json_scalar(value: Any) -> bool:
    """Do not carry invalid non-finite input values into the output JSON."""
    return value is None or type(value) in (bool, int, str) or (
        type(value) is float and math.isfinite(value))


def _row_reasons(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row_not_object"]
    reasons = [f"missing_{field}" for field in REQUIRED_FIELDS if field not in row]
    if "family" in row and not _text(row["family"]):
        reasons.append("invalid_family")
    if "config" in row and not (
        (type(row["config"]) is int and row["config"] > 0) or _text(row["config"])
    ):
        reasons.append("invalid_config")
    if "reference_name" in row and not _text(row["reference_name"]):
        reasons.append("invalid_reference_name")
    if "source_sha256" in row:
        sha = row["source_sha256"]
        if not (isinstance(sha, str) and len(sha) == 64
                and all(char in "0123456789abcdefABCDEF" for char in sha)):
            reasons.append("invalid_source_sha256")
    if "generic_cells" in row and not (
        type(row["generic_cells"]) is int and _positive_number(row["generic_cells"])
    ):
        reasons.append("invalid_generic_cells")
    if "physical_stdcell_area_um2" in row and not _positive_number(row["physical_stdcell_area_um2"]):
        reasons.append("invalid_physical_stdcell_area_um2")
    if "physical_stage" in row and not _text(row["physical_stage"]):
        reasons.append("invalid_physical_stage")
    for key in ("finite_pre_route_checked", "route_completed"):
        if key in row and type(row[key]) is not bool:
            reasons.append(f"invalid_{key}")
    if row.get("finite_pre_route_checked") is False:
        reasons.append("finite_pre_route_not_checked")
    if row.get("route_completed") is False:
        reasons.append("route_not_completed")
    if "is_baseline" in row and type(row["is_baseline"]) is not bool:
        reasons.append("invalid_is_baseline")
    if row.get("setup_slack_ns") is not None and not (
        _finite_number(row["setup_slack_ns"])
    ):
        reasons.append("invalid_setup_slack_ns")
    if row.get("route_violation_count") is not None and not (
        type(row["route_violation_count"]) is int and row["route_violation_count"] >= 0
    ):
        reasons.append("invalid_route_violation_count")
    if row.get("elapsed_s") is not None and not _nonnegative_number(row["elapsed_s"]):
        reasons.append("invalid_elapsed_s")
    return reasons


def _direction(candidate: float, baseline: float) -> str:
    if candidate == baseline:
        return "tie"
    return "increase" if candidate > baseline else "decrease"


def analyze_pilot(rows: Sequence[Any]) -> dict[str, Any]:
    """Analyze all submitted attempts, retaining exclusions and raw paired points.

    A completed route with violations remains a routed observation.  Its
    violation count is disclosed; it is never labelled violation-free.
    ``is_baseline: true`` is required on the unique baseline in each stratum.
    """
    if not isinstance(rows, (list, tuple)):
        raise ValueError("input rows must be an array")
    attempts: list[dict[str, Any]] = []
    included: list[tuple[int, dict[str, Any]]] = []
    reason_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        reasons = _row_reasons(row)
        reason_counts.update(reasons)
        record: dict[str, Any] = {
            "row_index": index, "included": not reasons, "exclusion_reasons": reasons,
        }
        if isinstance(row, dict):
            for key in ("family", "config", "reference_name", "source_sha256",
                        "generic_cells", "physical_stdcell_area_um2", "physical_stage",
                        "finite_pre_route_checked", "route_completed", "is_baseline",
                        "setup_slack_ns", "route_violation_count", "elapsed_s"):
                if key in row and _json_scalar(row[key]):
                    record[key] = row[key]
        attempts.append(record)
        if not reasons:
            included.append((index, row))

    group_rows: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, row in included:
        group_rows[(row["family"], str(row["config"]))].append((index, row))

    pairs: list[dict[str, Any]] = []
    pair_diagnostics: list[dict[str, Any]] = []
    for (family, config), group in sorted(group_rows.items()):
        baselines = [(i, row) for i, row in group if row.get("is_baseline") is True]
        alternatives = [(i, row) for i, row in group if row.get("is_baseline") is not True]
        if len(baselines) != 1:
            pair_diagnostics.append({
                "family": family, "config": config,
                "reason": "missing_baseline" if not baselines else "duplicate_baseline",
                "baseline_row_indices": [i for i, _ in baselines],
                "unpaired_row_indices": [i for i, _ in group],
            })
            continue
        baseline_index, baseline = baselines[0]
        if not alternatives:
            pair_diagnostics.append({
                "family": family, "config": config, "reason": "missing_alternative_source",
                "baseline_row_indices": [baseline_index],
                "unpaired_row_indices": [baseline_index],
            })
            continue
        for candidate_index, candidate in alternatives:
            if candidate["physical_stage"] != baseline["physical_stage"]:
                pair_diagnostics.append({
                    "family": family, "config": config, "reason": "physical_stage_mismatch",
                    "baseline_row_indices": [baseline_index],
                    "unpaired_row_indices": [candidate_index],
                    "baseline_physical_stage": baseline["physical_stage"],
                    "candidate_physical_stage": candidate["physical_stage"],
                })
                continue
            if candidate["source_sha256"].lower() == baseline["source_sha256"].lower():
                pair_diagnostics.append({
                    "family": family, "config": config, "reason": "same_source_as_baseline",
                    "baseline_row_indices": [baseline_index],
                    "unpaired_row_indices": [candidate_index],
                })
                continue
            cell_direction = _direction(candidate["generic_cells"], baseline["generic_cells"])
            area_direction = _direction(candidate["physical_stdcell_area_um2"],
                                        baseline["physical_stdcell_area_um2"])
            tie = "tie" in (cell_direction, area_direction)
            pairs.append({
                "family": family, "config": config,
                "baseline_row_index": baseline_index, "candidate_row_index": candidate_index,
                "baseline_reference_name": baseline["reference_name"],
                "candidate_reference_name": candidate["reference_name"],
                "baseline_source_sha256": baseline["source_sha256"],
                "candidate_source_sha256": candidate["source_sha256"],
                "baseline_generic_cells": baseline["generic_cells"],
                "candidate_generic_cells": candidate["generic_cells"],
                "baseline_physical_stdcell_area_um2": baseline["physical_stdcell_area_um2"],
                "candidate_physical_stdcell_area_um2": candidate["physical_stdcell_area_um2"],
                "cell_ratio": candidate["generic_cells"] / baseline["generic_cells"],
                "area_ratio": (candidate["physical_stdcell_area_um2"]
                               / baseline["physical_stdcell_area_um2"]),
                "cell_direction": cell_direction, "area_direction": area_direction,
                "direction_agrees": None if tie else cell_direction == area_direction,
                "direction_status": "tie" if tie else (
                    "agree" if cell_direction == area_direction else "disagree"),
                "baseline_route_violation_count": baseline.get("route_violation_count"),
                "candidate_route_violation_count": candidate.get("route_violation_count"),
            })

    x = [row["generic_cells"] for _, row in included]
    y = [row["physical_stdcell_area_um2"] for _, row in included]
    stages = sorted(set(row["physical_stage"] for _, row in included))
    family_counts = dict(sorted(Counter(row["family"] for _, row in included).items()))
    route_completed_count = sum(
        isinstance(row, dict) and row.get("route_completed") is True for row in rows)
    known_violation_counts = [
        row["route_violation_count"] for row in rows
        if isinstance(row, dict) and row.get("route_completed") is True
        and type(row.get("route_violation_count")) is int and row["route_violation_count"] >= 0
    ]
    return {
        "schema": SCHEMA,
        "scope": "descriptive_exploratory_physical_pilot",
        "denominators": {
            "attempts": len(rows), "routed_included": len(included),
            "excluded": len(rows) - len(included),
            "route_completed_attempts": route_completed_count,
            "route_violation_count_known_completed_attempts": len(known_violation_counts),
            "violation_free_completed_attempts": sum(v == 0 for v in known_violation_counts),
            "completed_attempts_with_violations": sum(v > 0 for v in known_violation_counts),
        },
        "exclusion_reason_counts": dict(sorted(reason_counts.items())),
        "attempts": attempts,
        "pooled_association": {
            "n": len(included), "family_counts": family_counts,
            "physical_stages": stages,
            "distinct_generic_cell_values": len(set(x)),
            "distinct_physical_area_values": len(set(y)),
            "spearman_rho": spearman_rank_correlation(x, y) if len(stages) <= 1 else None,
            "undefined_reason": "mixed_physical_stages" if len(stages) > 1 else (
                "insufficient_or_constant_ranks" if spearman_rank_correlation(x, y) is None else None),
            "warning": "Pooled cross-family association is confounded by circuit size and is not calibration evidence. Mixed physical stages are not pooled.",
        },
        "pairs": pairs,
        "pair_diagnostics": pair_diagnostics,
        "notes": [
            "Five paired cases, if present, are exploratory and do not establish general proxy calibration.",
            "Comparisons sharing one baseline are not independent samples.",
            "A completed route is distinct from a violation-free route; unknown violation counts remain unknown.",
            "Generic-cell count alone does not predict cycles times clock period.",
            "Setup slack is distinct from critical-path delay and cannot by itself establish Fmax.",
            "No inferential p-values, confidence intervals, or signoff claims are produced.",
        ],
    }
