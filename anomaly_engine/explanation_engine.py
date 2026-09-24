"""
Explanation and recommended-action generation.

Two hard rules govern every string produced here:

  1. The system never asserts fraud, misappropriation or wrongdoing. It reports
     risk signals and asks for verification. The determination belongs to the
     authorised officer.
  2. Every claim is accompanied by the number it came from, the threshold it
     was compared against, and the difference between them.
"""

from __future__ import annotations

from . import config as C

# ------------------------------------------------------------------------- #
# Recommended actions per anomaly family.
# ------------------------------------------------------------------------- #
ACTIONS = {
    "COST_ANOMALY": [
        "Verify expenditure records against the sanction order",
        "Review sanctioned versus actual cost and any revised estimate",
        "Confirm whether a cost revision was approved by the competent authority",
    ],
    "PROGRESS_MISMATCH": [
        "Conduct physical verification of the work executed on site",
        "Verify completion evidence against the amount released",
        "Reconcile utilisation certificates with the measurement book",
    ],
    "DELAY_RISK": [
        "Review the project timeline and revised completion schedule",
        "Check current implementation status with the implementing agency",
        "Assess whether unspent funds should be reallocated",
    ],
    "POTENTIAL_DUPLICATE": [
        "Compare the scope and site of both works before further release",
        "Verify whether the two sanctions cover the same physical asset",
        "Obtain site photographs or geo-tagged evidence for both works",
    ],
    "DATA_QUALITY": [
        "Validate the source record against the implementing agency's file",
        "Request corrected data for the fields flagged above",
        "Re-run this assessment once the record is corrected",
    ],
}

PRIORITY_NOTE = {
    "CRITICAL": "Priority verification recommended.",
    "HIGH": "Verification recommended.",
    "MEDIUM": "Review recommended during routine monitoring.",
    "LOW": "No specific action required at present.",
}


def build_explanations(anomalies: list[dict]) -> list[dict]:
    """Normalise detected anomalies into the 'Why flagged?' payload.

    Each entry answers the same five questions in the same order: what
    happened, the actual value, the expected or threshold value, the difference
    between them, and why it matters. The recommended action for that signal is
    attached here too, so a single anomaly can be acted on without reading the
    whole-project checklist.
    """
    explanations = []
    for anomaly in sorted(anomalies, key=lambda a: a["contribution"], reverse=True):
        explanations.append(
            {
                "type": anomaly["type"],
                "title": anomaly["title"],
                "severity": anomaly["severity"],
                "severity_factor": anomaly["severity_factor"],
                "what_happened": anomaly["headline"],
                "actual_value": anomaly["actual_value"],
                "expected_value": anomaly["expected_value"],
                "difference": anomaly["difference"],
                "why_it_matters": anomaly["reason"],
                "recommended_actions": list(ACTIONS.get(anomaly["type"], [])),
                "evidence": anomaly["evidence"],
                "metrics": anomaly["metrics"],
                "points_contributed": anomaly["contribution"],
                "max_points": anomaly["weight"],
                "scoring_note": (
                    f"Contributed {anomaly['contribution']:.1f} of a possible "
                    f"{anomaly['weight']:.0f} risk points "
                    f"(severity factor {anomaly['severity_factor']:.2f})."
                ),
            }
        )
    return explanations


def attach_actions(anomalies: list[dict]) -> None:
    """Add the per-family recommended actions to each anomaly, in place.

    The anomaly list is served on its own endpoint as well as inside the full
    analysis, so the actions belong on the anomaly rather than only on the
    explanation derived from it.
    """
    for anomaly in anomalies:
        anomaly["recommended_actions"] = list(ACTIONS.get(anomaly["type"], []))
        anomaly["recommended_action"] = anomaly["recommended_actions"][0] if anomaly["recommended_actions"] else ""


def build_recommendation(anomalies: list[dict], risk_level: str) -> dict:
    """Recommended action block: a headline plus a concrete checklist."""
    if not anomalies:
        return {
            "priority": "ROUTINE",
            "headline": "No risk signal detected.",
            "summary": (
                "This work did not trigger any of the configured risk checks. "
                "It remains subject to normal monitoring."
            ),
            "checklist": [],
            "disclaimer": DISCLAIMER,
        }

    checklist: list[dict] = []
    seen: set[str] = set()
    for anomaly in sorted(anomalies, key=lambda a: a["contribution"], reverse=True):
        for item in ACTIONS.get(anomaly["type"], []):
            if item in seen:
                continue
            seen.add(item)
            checklist.append(
                {
                    "action": item,
                    "driver": anomaly["title"],
                    "driver_type": anomaly["type"],
                    "severity": anomaly["severity"],
                }
            )

    multiple = len(anomalies) > 1
    if multiple and risk_level in ("HIGH", "CRITICAL"):
        headline = "Priority verification recommended."
        summary = (
            f"{len(anomalies)} independent risk signals were detected on this "
            "work. Concurrent signals of this kind are the pattern this system "
            "is designed to surface for early human review."
        )
        priority = "PRIORITY"
    elif risk_level in ("HIGH", "CRITICAL"):
        headline = "Verification recommended."
        summary = (
            "A significant risk signal was detected. Verification against source "
            "records is recommended before further release of funds."
        )
        priority = "HIGH"
    else:
        headline = PRIORITY_NOTE.get(risk_level, "Review recommended.")
        summary = (
            "A risk signal was detected at a level that merits review during "
            "routine monitoring rather than immediate action."
        )
        priority = "ROUTINE"

    return {
        "priority": priority,
        "headline": headline,
        "summary": summary,
        "checklist": checklist,
        "disclaimer": DISCLAIMER,
    }


DISCLAIMER = (
    "NIRIKSHAN AI is a decision-support system. It reports statistical and "
    "rule-based risk signals for prioritisation only. It does not establish "
    "irregularity, misappropriation or wrongdoing of any kind. All findings "
    "require verification against source records, and the determination rests "
    "with the authorised officer."
)


def band_summary() -> list[dict]:
    """The risk bands, for display alongside a score."""
    return [
        {"level": label, "min": low, "max": high}
        for low, high, label in C.RISK_BANDS
    ]
