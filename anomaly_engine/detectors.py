"""
Deterministic anomaly detectors.

Each detector takes a project record and returns either ``None`` (no signal) or
one structured anomaly. Nothing here is random or sampled: given the same record
and the same as-of date, the output is always identical.

Every anomaly carries the five things an officer needs in order to act on it:
what happened, the actual value, the expected/threshold value, the difference,
and why it matters.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from . import config as C
from .formatting import human_date, pct, pp, rupees, rupees_words, signed_pct


def _anomaly(
    code: str,
    title: str,
    factor: float,
    headline: str,
    reason: str,
    evidence: list[dict],
    metrics: dict[str, Any],
    actual: str,
    expected: str,
    difference: str,
) -> dict:
    factor = max(0.0, min(1.0, factor))
    weight = C.WEIGHTS[code]
    return {
        "type": code,
        "title": title,
        "severity": C.severity_from_factor(factor),
        "severity_factor": round(factor, 4),
        "weight": weight,
        "contribution": round(weight * factor, 2),
        "headline": headline,
        "reason": reason,
        # The comparison triple is published as its own fields rather than left
        # implicit in the evidence rows, so that every anomaly — whatever its
        # family — can be read as "actual vs expected, difference" without the
        # reader having to know which evidence label means what.
        "actual_value": actual,
        "expected_value": expected,
        "difference": difference,
        "evidence": evidence,
        "metrics": metrics,
    }


def _ev(label: str, value: str, tone: str = "neutral", raw: Any = None) -> dict:
    """One evidence row. ``tone`` drives colour only, never meaning."""
    return {"label": label, "value": value, "tone": tone, "raw": raw}


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------------- #
# A. Cost anomaly
# ------------------------------------------------------------------------- #
def detect_cost_anomaly(project: dict) -> dict | None:
    sanctioned = project.get("sanctioned_cost")
    expenditure = project.get("actual_expenditure")

    if not sanctioned or sanctioned <= 0 or expenditure is None:
        return None

    deviation_pct = (expenditure - sanctioned) / sanctioned * 100.0
    if deviation_pct <= C.COST_TOLERANCE_PCT:
        return None

    span = C.COST_FULL_SEVERITY_PCT - C.COST_TOLERANCE_PCT
    factor = (deviation_pct - C.COST_TOLERANCE_PCT) / span

    overrun = expenditure - sanctioned
    return _anomaly(
        "COST_ANOMALY",
        "Cost Anomaly",
        factor,
        f"Expenditure exceeds the sanctioned amount by {deviation_pct:.0f}%.",
        "Spending beyond the sanctioned limit without a recorded revision is a "
        "known indicator of cost escalation, unapproved scope change or "
        "misclassified expenditure. It warrants verification of the expenditure "
        "records against the sanction order.",
        [
            _ev("Actual expenditure", rupees(expenditure), "bad", expenditure),
            _ev("Sanctioned amount", rupees(sanctioned), "neutral", sanctioned),
            _ev("Overrun", rupees(overrun), "bad", overrun),
            _ev("Deviation", signed_pct(deviation_pct), "bad", round(deviation_pct, 2)),
            _ev(
                "Tolerance threshold",
                f"{C.COST_TOLERANCE_PCT:.0f}% above sanctioned amount",
                "neutral",
                C.COST_TOLERANCE_PCT,
            ),
        ],
        {
            "sanctioned_cost": sanctioned,
            "actual_expenditure": expenditure,
            "overrun_amount": overrun,
            "deviation_pct": round(deviation_pct, 2),
            "threshold_pct": C.COST_TOLERANCE_PCT,
            "threshold_amount": round(sanctioned * (1 + C.COST_TOLERANCE_PCT / 100), 2),
        },
        actual=f"{rupees(expenditure)} spent ({signed_pct(deviation_pct)} of sanction)",
        expected=f"{rupees(sanctioned)} sanctioned, up to {C.COST_TOLERANCE_PCT:.0f}% tolerance",
        difference=f"{rupees(overrun)} above sanction ({rupees_words(overrun)})",
    )


# ------------------------------------------------------------------------- #
# B. Delay risk
# ------------------------------------------------------------------------- #
def detect_delay_anomaly(project: dict, as_of: date | None = None) -> dict | None:
    as_of = as_of or date.today()
    start = _as_date(project.get("start_date"))
    expected = _as_date(project.get("expected_completion_date"))
    actual_completion = _as_date(project.get("actual_completion_date"))
    physical = project.get("physical_progress")

    if expected is None or physical is None:
        return None

    # A finished work is not a delay risk, even if it finished late; that is a
    # performance fact rather than an open investigation signal.
    if actual_completion is not None or physical >= 100:
        return None

    overdue_days = (as_of - expected).days
    days_remaining = -overdue_days

    overdue_factor = 0.0
    if overdue_days > 0:
        overdue_factor = C.OVERDUE_BASE_FACTOR + (1 - C.OVERDUE_BASE_FACTOR) * min(
            1.0, overdue_days / C.OVERDUE_FULL_SEVERITY_DAYS
        )

    # Straight-line schedule expectation.
    expected_progress = None
    deficit = None
    deficit_factor = 0.0
    if start is not None and expected > start:
        total_days = (expected - start).days
        elapsed_days = (as_of - start).days
        expected_progress = max(0.0, min(100.0, elapsed_days / total_days * 100.0))
        deficit = expected_progress - physical
        if deficit > C.DELAY_DEFICIT_TOLERANCE_PP:
            span = C.DELAY_DEFICIT_FULL_PP - C.DELAY_DEFICIT_TOLERANCE_PP
            deficit_factor = (deficit - C.DELAY_DEFICIT_TOLERANCE_PP) / span

    factor = max(overdue_factor, deficit_factor)
    if factor <= 0:
        return None

    if overdue_days > 0:
        headline = (
            f"Project is {overdue_days} days past its expected completion date "
            f"with {physical:.0f}% physical progress."
        )
    else:
        headline = (
            f"Project is approaching its expected completion date "
            f"({days_remaining} days remaining) with only {physical:.0f}% physical progress."
        )

    evidence = [
        _ev("Expected completion", human_date(expected), "neutral", str(expected)),
        _ev("Assessment date", human_date(as_of), "neutral", str(as_of)),
        _ev("Physical progress", pct(physical), "bad", physical),
    ]
    if overdue_days > 0:
        evidence.append(_ev("Days overdue", f"{overdue_days} days", "bad", overdue_days))
    else:
        evidence.append(
            _ev("Days remaining", f"{days_remaining} days", "warn", days_remaining)
        )
    if expected_progress is not None:
        evidence.append(
            _ev(
                "Expected progress by now",
                pct(expected_progress),
                "neutral",
                round(expected_progress, 1),
            )
        )
        evidence.append(
            _ev("Schedule deficit", pp(deficit), "bad", round(deficit, 1))
        )
    evidence.append(
        _ev(
            "Tolerance threshold",
            f"{C.DELAY_DEFICIT_TOLERANCE_PP:.0f} percentage points behind schedule",
            "neutral",
            C.DELAY_DEFICIT_TOLERANCE_PP,
        )
    )

    if overdue_days > 0:
        actual_txt = f"{pct(physical)} complete, {overdue_days} days past due"
        expected_txt = f"Completion by {human_date(expected)}"
        difference_txt = f"{overdue_days} days overdue"
        if deficit is not None and deficit > 0:
            difference_txt += f", {pp(deficit)} behind the straight-line schedule"
    else:
        actual_txt = f"{pct(physical)} complete with {days_remaining} days remaining"
        expected_txt = (
            f"{pct(expected_progress)} by now on a straight-line schedule"
            if expected_progress is not None
            else f"Completion by {human_date(expected)}"
        )
        difference_txt = (
            f"{pp(deficit)} behind schedule" if deficit is not None else "Behind schedule"
        )

    return _anomaly(
        "DELAY_RISK",
        "Delay Risk",
        factor,
        headline,
        "A work that is materially behind its sanctioned timeline ties up funds "
        "that could be reallocated, and a large gap between elapsed time and "
        "physical execution often precedes a request for revised cost or "
        "timeline. The implementation status merits review.",
        evidence,
        {
            "start_date": str(start) if start else None,
            "expected_completion_date": str(expected),
            "as_of": str(as_of),
            "overdue_days": overdue_days if overdue_days > 0 else 0,
            "days_remaining": days_remaining if overdue_days <= 0 else 0,
            "physical_progress": physical,
            "expected_progress": round(expected_progress, 1) if expected_progress is not None else None,
            "schedule_deficit_pp": round(deficit, 1) if deficit is not None else None,
            "is_overdue": overdue_days > 0,
        },
        actual=actual_txt,
        expected=expected_txt,
        difference=difference_txt,
    )


# ------------------------------------------------------------------------- #
# C. Financial vs physical progress mismatch
# ------------------------------------------------------------------------- #
def detect_progress_mismatch(project: dict) -> dict | None:
    financial = project.get("financial_progress")
    physical = project.get("physical_progress")
    if financial is None or physical is None:
        return None

    gap = financial - physical
    if gap <= C.MISMATCH_TOLERANCE_PP:
        return None

    span = C.MISMATCH_FULL_PP - C.MISMATCH_TOLERANCE_PP
    factor = (gap - C.MISMATCH_TOLERANCE_PP) / span

    return _anomaly(
        "PROGRESS_MISMATCH",
        "Progress Mismatch",
        factor,
        f"Financial progress leads physical progress by {gap:.0f} percentage points.",
        "Funds released substantially ahead of work actually executed on the "
        "ground is one of the strongest early indicators that reported progress "
        "and site reality have diverged. Physical verification of the executed "
        "work against the released amount is recommended.",
        [
            _ev("Financial progress", pct(financial), "bad", financial),
            _ev("Physical progress", pct(physical), "warn", physical),
            _ev("Difference", pp(gap), "bad", round(gap, 1)),
            _ev(
                "Tolerance threshold",
                f"{C.MISMATCH_TOLERANCE_PP:.0f} percentage points",
                "neutral",
                C.MISMATCH_TOLERANCE_PP,
            ),
        ],
        {
            "financial_progress": financial,
            "physical_progress": physical,
            "gap_pp": round(gap, 1),
            "threshold_pp": C.MISMATCH_TOLERANCE_PP,
        },
        actual=f"{pct(financial)} financial against {pct(physical)} physical",
        expected=(
            f"Financial progress within {C.MISMATCH_TOLERANCE_PP:.0f} percentage "
            f"points of physical progress"
        ),
        difference=f"{pp(gap)} of funds released ahead of executed work",
    )


# ------------------------------------------------------------------------- #
# E. Data quality
# ------------------------------------------------------------------------- #
def detect_data_quality(project: dict, validation: dict) -> dict | None:
    """Turn the validation result into a scored anomaly.

    Only issues flagged ``counts_towards_quality`` are charged here, so a
    problem that another detector already scores is not counted twice.
    """
    penalty = validation["total_penalty"]
    if penalty <= 0:
        return None

    factor = penalty / C.DATA_QUALITY_FULL_PENALTY
    counted = [i for i in validation["issues"] if i["counts_towards_quality"]]

    evidence = [
        _ev("Data quality score", f"{validation['data_quality_score']:.0f}/100", "bad",
            validation["data_quality_score"]),
        _ev("Record completeness", pct(validation["completeness_pct"], 1), "warn",
            validation["completeness_pct"]),
        _ev("Validation issues", str(len(counted)), "bad", len(counted)),
    ]
    for issue in counted[:5]:
        evidence.append(
            _ev(
                issue["field_label"],
                f"{issue['actual']} (expected {issue['expected']})",
                "bad",
                issue["actual"],
            )
        )

    headline = (
        f"{len(counted)} data quality issue"
        f"{'s' if len(counted) != 1 else ''} detected in the source record."
    )
    return _anomaly(
        "DATA_QUALITY",
        "Data Quality",
        factor,
        headline,
        "Incomplete or internally inconsistent records reduce the reliability of "
        "every other check run against this work, and can themselves conceal "
        "reporting problems. The source record should be validated and corrected.",
        evidence,
        {
            "data_quality_score": validation["data_quality_score"],
            "completeness_pct": validation["completeness_pct"],
            "penalty": penalty,
            "penalty_threshold": C.DATA_QUALITY_FULL_PENALTY,
            "issues": counted,
        },
        actual=(
            f"Data quality score {validation['data_quality_score']:.0f}/100, "
            f"{len(counted)} issue{'s' if len(counted) != 1 else ''}"
        ),
        expected="A complete, internally consistent record with no validation issues",
        difference=(
            "; ".join(
                f"{i['field_label']}: {i['actual']} (expected {i['expected']})"
                for i in counted[:3]
            )
            or "No countable issues"
        ),
    )
