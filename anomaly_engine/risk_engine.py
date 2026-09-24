"""
Risk fusion.

The score is always computed from the anomalies that were actually detected —
there is no stored or hardcoded score anywhere in this system. Each anomaly
contributes ``weight x severity_factor`` points; the contributions are summed
and clamped to 0-100.

Keeping the fusion additive and linear is a deliberate choice for a
decision-support tool: an officer can read the breakdown and reconstruct the
total by hand, which a non-linear or learned model would not allow.
"""

from __future__ import annotations

from . import config as C


def fuse(anomalies: list[dict], cleared: set[str] | None = None) -> dict:
    """Combine detected anomalies into a single risk assessment.

    ``cleared`` names signal families an authorised officer has marked as
    checked and explained. A cleared signal keeps its detected values and its
    full weight on record, but contributes zero points, so the adjusted score
    is recomputed by this same arithmetic rather than subtracted elsewhere.
    Clearing a signal records a verification step; it does not delete the
    finding.
    """
    cleared = set(cleared or ())
    breakdown = []
    raw_total = 0.0
    withheld_total = 0.0

    for code, weight in C.WEIGHTS.items():
        match = next((a for a in anomalies if a["type"] == code), None)
        detected_points = match["contribution"] if match else 0.0
        is_cleared = code in cleared and match is not None

        points = 0.0 if is_cleared else detected_points
        raw_total += points
        if is_cleared:
            withheld_total += detected_points

        breakdown.append(
            {
                "type": code,
                "title": match["title"] if match else _default_title(code),
                "detected": match is not None,
                "max_weight": weight,
                "severity_factor": match["severity_factor"] if match else 0.0,
                "points": round(points, 2),
                "detected_points": round(detected_points, 2),
                "cleared": is_cleared,
                "severity": match["severity"] if match else None,
                # The figures the row was derived from travel with the row, so a
                # contribution table can be opened out into the evidence behind
                # each line without a second request.
                "headline": match["headline"] if match else None,
                "actual_value": match.get("actual_value") if match else None,
                "expected_value": match.get("expected_value") if match else None,
                "difference": match.get("difference") if match else None,
                "reason": match.get("reason") if match else None,
                "evidence": match.get("evidence", []) if match else [],
                "arithmetic": (
                    f"{weight} max weight x {match['severity_factor']:.2f} severity "
                    f"= {detected_points:.2f} points"
                    if match
                    else f"not detected, contributes 0 of {weight}"
                ),
            }
        )

    score = round(min(C.MAX_RISK_SCORE, max(0.0, raw_total)))
    level = C.risk_level(score)

    return {
        "risk_score": int(score),
        "risk_level": level,
        "raw_total": round(raw_total, 2),
        "was_clamped": raw_total > C.MAX_RISK_SCORE,
        "max_possible": int(C.MAX_RISK_SCORE),
        "breakdown": breakdown,
        "detected_count": sum(1 for b in breakdown if b["detected"]),
        "cleared_count": sum(1 for b in breakdown if b["cleared"]),
        "cleared_types": sorted(b["type"] for b in breakdown if b["cleared"]),
        "points_withheld": round(withheld_total, 2),
        "bands": [
            {"level": label, "min": low, "max": high}
            for low, high, label in C.RISK_BANDS
        ],
    }


def _default_title(code: str) -> str:
    return ANOMALY_TITLES.get(code, code.replace("_", " ").title())


def what_if(anomalies: list[dict]) -> dict:
    """What the score would be if each detected signal turned out to be explained.

    Every figure here is produced by re-running :func:`fuse` with one family
    withheld — the same arithmetic that produced the score in the first place.
    Nothing is estimated and nothing is stored: this answers "what is driving
    this number", which is the first question an officer asks of a score.
    """
    base = fuse(anomalies)
    scenarios = []

    for row in base["breakdown"]:
        if not row["detected"]:
            continue
        without = fuse(anomalies, cleared={row["type"]})
        scenarios.append(
            {
                "type": row["type"],
                "title": row["title"],
                "points": row["points"],
                "score_without": without["risk_score"],
                "level_without": without["risk_level"],
                "score_drop": round(base["raw_total"] - without["raw_total"], 2),
                "band_changes": without["risk_level"] != base["risk_level"],
            }
        )

    scenarios.sort(key=lambda s: s["score_drop"], reverse=True)
    return {
        "current_score": base["risk_score"],
        "current_level": base["risk_level"],
        "current_raw_total": base["raw_total"],
        "scenarios": scenarios,
        "largest_driver": scenarios[0]["title"] if scenarios else None,
        "note": (
            "Each figure is the score recomputed with that one signal withheld. "
            "It shows what the signal is contributing, not a prediction and not "
            "a revised assessment."
        ),
    }


#: Display names for the five detector families, used wherever an anomaly type
#: has to be shown without an accompanying anomaly object (charts, legends).
ANOMALY_TITLES = {
    "COST_ANOMALY": "Cost Anomaly",
    "PROGRESS_MISMATCH": "Progress Mismatch",
    "DELAY_RISK": "Delay Risk",
    "POTENTIAL_DUPLICATE": "Potential Duplicate / Overlapping Work",
    "DATA_QUALITY": "Data Quality",
}


def primary_risk_label(anomalies: list[dict]) -> str:
    """Short label for queue/table views, e.g. 'Cost + Delay + Duplicate'."""
    if not anomalies:
        return "No signal"
    short = {
        "COST_ANOMALY": "Cost",
        "PROGRESS_MISMATCH": "Mismatch",
        "DELAY_RISK": "Delay",
        "POTENTIAL_DUPLICATE": "Duplicate",
        "DATA_QUALITY": "Data quality",
    }
    ordered = sorted(anomalies, key=lambda a: a["contribution"], reverse=True)
    return " + ".join(short.get(a["type"], a["type"]) for a in ordered[:3])
