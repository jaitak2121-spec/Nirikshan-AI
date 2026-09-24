"""
Data validation engine.

Runs before anomaly detection. Its job is to answer "can we trust this record?"
rather than "is this record suspicious?" — the two questions are kept separate
so that a data-entry problem is never presented to an officer as a spending
problem.

Every issue is returned as a structured dict so the API, the UI and the risk
engine all read the same shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .config import RECOMMENDED_FIELDS, REQUIRED_FIELDS, VALIDATION_PENALTY

# Human-readable labels for field names used in messages.
FIELD_LABELS = {
    "project_name": "Project name",
    "description": "Description",
    "work_type": "Work type",
    "sector": "Sector",
    "village": "Village",
    "district": "District",
    "constituency": "Constituency",
    "mp_name": "Member of Parliament",
    "implementing_agency": "Implementing agency",
    "recommendation_date": "Recommendation date",
    "sanction_date": "Sanction date",
    "start_date": "Start date",
    "expected_completion_date": "Expected completion date",
    "actual_completion_date": "Actual completion date",
    "estimated_cost": "Estimated cost",
    "sanctioned_cost": "Sanctioned cost",
    "actual_expenditure": "Actual expenditure",
    "physical_progress": "Physical progress",
    "financial_progress": "Financial progress",
    "status": "Status",
    "latitude": "Latitude",
    "longitude": "Longitude",
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").capitalize())


def _issue(
    code: str,
    severity: str,
    field: str,
    reason: str,
    actual: Any = None,
    expected: Any = None,
    *,
    counts_towards_quality: bool = True,
) -> dict:
    """Build one structured validation issue.

    ``counts_towards_quality`` is False for issues that another detector already
    scores (currently the expenditure-over-sanction inconsistency, which the
    cost detector owns). Those issues are still reported to the officer — they
    just are not charged twice against the risk score.
    """
    return {
        "type": code,
        "severity": severity,
        "field": field,
        "field_label": _label(field),
        "actual": actual,
        "expected": expected,
        "reason": reason,
        "counts_towards_quality": counts_towards_quality,
        "penalty": VALIDATION_PENALTY.get(severity, 0) if counts_towards_quality else 0,
    }


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def validate_project(project: dict) -> dict:
    """Validate a single project record.

    Returns a dict with the issue list, a 0-100 data quality score, a
    completeness percentage and the total penalty the risk engine should use.
    """
    issues: list[dict] = []

    # ---------------------------------------------------------------- #
    # 1. Completeness
    # ---------------------------------------------------------------- #
    missing_required = [f for f in REQUIRED_FIELDS if _is_blank(project.get(f))]
    missing_recommended = [f for f in RECOMMENDED_FIELDS if _is_blank(project.get(f))]

    for field in missing_required:
        issues.append(
            _issue(
                "MISSING_REQUIRED_FIELD",
                "HIGH",
                field,
                f"{_label(field)} is required for monitoring but is not present in the record.",
                actual="(empty)",
                expected="a value",
            )
        )
    for field in missing_recommended:
        issues.append(
            _issue(
                "MISSING_FIELD",
                "MEDIUM",
                field,
                f"{_label(field)} is not recorded, which limits automated verification.",
                actual="(empty)",
                expected="a value",
            )
        )

    # ---------------------------------------------------------------- #
    # 2. Financial validity
    # ---------------------------------------------------------------- #
    sanctioned = project.get("sanctioned_cost")
    expenditure = project.get("actual_expenditure")
    estimated = project.get("estimated_cost")

    for field, value in (
        ("estimated_cost", estimated),
        ("sanctioned_cost", sanctioned),
        ("actual_expenditure", expenditure),
    ):
        if value is not None and value < 0:
            issues.append(
                _issue(
                    "NEGATIVE_AMOUNT",
                    "CRITICAL",
                    field,
                    f"{_label(field)} cannot be negative.",
                    actual=value,
                    expected=">= 0",
                )
            )

    if sanctioned is not None and sanctioned == 0:
        issues.append(
            _issue(
                "ZERO_SANCTIONED_COST",
                "HIGH",
                "sanctioned_cost",
                "Sanctioned cost is zero, so cost performance cannot be assessed.",
                actual=0,
                expected="> 0",
            )
        )

    if (
        sanctioned is not None
        and expenditure is not None
        and sanctioned > 0
        and expenditure > sanctioned
    ):
        issues.append(
            _issue(
                "DATA_INCONSISTENCY",
                "HIGH",
                "actual_expenditure",
                "Expenditure exceeds the sanctioned cost.",
                actual=expenditure,
                expected=f"<= {int(sanctioned)}",
                # The cost anomaly detector already scores this overrun.
                counts_towards_quality=False,
            )
        )

    # ---------------------------------------------------------------- #
    # 3. Progress validity
    # ---------------------------------------------------------------- #
    for field in ("physical_progress", "financial_progress"):
        value = project.get(field)
        if value is None:
            continue
        if value < 0:
            issues.append(
                _issue(
                    "INVALID_PROGRESS",
                    "HIGH",
                    field,
                    f"{_label(field)} cannot be below 0%.",
                    actual=value,
                    expected="0 - 100",
                )
            )
        elif value > 100:
            issues.append(
                _issue(
                    "INVALID_PROGRESS",
                    "HIGH",
                    field,
                    f"{_label(field)} cannot exceed 100%.",
                    actual=value,
                    expected="0 - 100",
                )
            )

    # ---------------------------------------------------------------- #
    # 4. Date validity and ordering
    # ---------------------------------------------------------------- #
    date_fields = (
        "recommendation_date",
        "sanction_date",
        "start_date",
        "expected_completion_date",
        "actual_completion_date",
    )
    parsed: dict[str, date | None] = {}
    for field in date_fields:
        raw = project.get(field)
        parsed[field] = _as_date(raw)
        if not _is_blank(raw) and parsed[field] is None:
            issues.append(
                _issue(
                    "INVALID_DATE",
                    "HIGH",
                    field,
                    f"{_label(field)} is not a readable calendar date.",
                    actual=str(raw),
                    expected="YYYY-MM-DD",
                )
            )

    def order(earlier: str, later: str, severity: str, reason: str) -> None:
        a, b = parsed.get(earlier), parsed.get(later)
        if a and b and b < a:
            issues.append(
                _issue(
                    "DATE_SEQUENCE_ERROR",
                    severity,
                    later,
                    reason,
                    actual=b.isoformat(),
                    expected=f">= {_label(earlier).lower()} ({a.isoformat()})",
                )
            )

    order(
        "recommendation_date",
        "sanction_date",
        "MEDIUM",
        "Sanction date precedes the MP recommendation date.",
    )
    order(
        "sanction_date",
        "start_date",
        "HIGH",
        "Work start date precedes the sanction date, which the sanction workflow does not allow.",
    )
    order(
        "start_date",
        "expected_completion_date",
        "HIGH",
        "Expected completion date precedes the work start date.",
    )
    order(
        "sanction_date",
        "actual_completion_date",
        "HIGH",
        "Actual completion date precedes the sanction date.",
    )

    # ---------------------------------------------------------------- #
    # 5. Status consistency
    # ---------------------------------------------------------------- #
    status = (project.get("status") or "").strip().upper()
    physical = project.get("physical_progress")
    if status == "COMPLETED" and physical is not None and physical < 100:
        issues.append(
            _issue(
                "STATUS_INCONSISTENCY",
                "MEDIUM",
                "status",
                "Status is recorded as Completed while physical progress is below 100%.",
                actual=f"Completed / {physical}%",
                expected="Completed with 100% physical progress",
            )
        )
    if status == "COMPLETED" and _is_blank(project.get("actual_completion_date")):
        issues.append(
            _issue(
                "STATUS_INCONSISTENCY",
                "MEDIUM",
                "actual_completion_date",
                "Status is recorded as Completed but no actual completion date is present.",
                actual="(empty)",
                expected="a completion date",
            )
        )

    # ---------------------------------------------------------------- #
    # 6. Geo validity
    # ---------------------------------------------------------------- #
    lat, lon = project.get("latitude"), project.get("longitude")
    if lat is not None and not (-90 <= lat <= 90):
        issues.append(
            _issue("INVALID_COORDINATE", "MEDIUM", "latitude", "Latitude is out of range.", lat, "-90 to 90")
        )
    if lon is not None and not (-180 <= lon <= 180):
        issues.append(
            _issue("INVALID_COORDINATE", "MEDIUM", "longitude", "Longitude is out of range.", lon, "-180 to 180")
        )

    # ---------------------------------------------------------------- #
    # Scoring
    # ---------------------------------------------------------------- #
    total_penalty = sum(i["penalty"] for i in issues)
    quality_score = max(0.0, 100.0 - float(total_penalty))

    tracked = REQUIRED_FIELDS + RECOMMENDED_FIELDS
    present = sum(1 for f in tracked if not _is_blank(project.get(f)))
    completeness = round(present / len(tracked) * 100, 1)

    return {
        "is_valid": not any(i["severity"] in ("HIGH", "CRITICAL") for i in issues),
        "issues": issues,
        "issue_count": len(issues),
        "total_penalty": total_penalty,
        "data_quality_score": round(quality_score, 1),
        "completeness_pct": completeness,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }
