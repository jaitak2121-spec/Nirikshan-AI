"""
The analysis pipeline.

One function, ``analyze_project``, runs the full journey for a single work:

    validation -> feature engineering -> anomaly detection -> duplicate
    detection -> risk fusion -> explanation -> recommended action

``analyze_corpus`` runs it across every work, reusing a single TF-IDF index so
duplicate detection stays O(n^2) on a matrix rather than re-vectorising per
project.
"""

from __future__ import annotations

from datetime import date

from .detectors import (
    detect_cost_anomaly,
    detect_data_quality,
    detect_delay_anomaly,
    detect_progress_mismatch,
)
from .duplicate_detection import (
    build_similarity_index,
    detect_duplicate_anomaly,
    find_similar_projects,
)
from .explanation_engine import (
    DISCLAIMER,
    attach_actions,
    band_summary,
    build_explanations,
    build_recommendation,
)
from .lineage import lineage_for
from .risk_engine import fuse, primary_risk_label, what_if
from .verification_checklist import CHECKLIST_NOTE, build_checklist

__all__ = ["analyze_project", "analyze_corpus", "build_similarity_index", "find_similar_projects"]


def analyze_project(
    project: dict,
    index: dict,
    as_of: date | None = None,
) -> dict:
    """Run the full analysis for one project. Deterministic."""
    as_of = as_of or date.today()

    # 1. Validation -------------------------------------------------------
    from .validation import validate_project

    validation = validate_project(project)

    # 2 & 3. Anomaly detection -------------------------------------------
    anomalies: list[dict] = []
    for detected in (
        detect_cost_anomaly(project),
        detect_progress_mismatch(project),
        detect_delay_anomaly(project, as_of=as_of),
    ):
        if detected:
            anomalies.append(detected)

    # 4. Duplicate detection ---------------------------------------------
    duplicate, similar = detect_duplicate_anomaly(index, project["project_id"])
    if duplicate:
        anomalies.append(duplicate)

    # 5. Data quality (scored from the validation result) ------------------
    quality = detect_data_quality(project, validation)
    if quality:
        anomalies.append(quality)

    # 6. Risk fusion ------------------------------------------------------
    risk = fuse(anomalies)

    # 7 & 8. Explanations and recommended actions -------------------------
    attach_actions(anomalies)
    explanations = build_explanations(anomalies)
    recommendation = build_recommendation(anomalies, risk["risk_level"])

    # 9. Verification steps and score drivers ------------------------------
    # Both are derived from the signals just detected — the checklist names
    # what an officer would check, the driver view shows what the score would
    # be if each signal turned out to be explained.
    checklist = build_checklist(anomalies)

    return {
        "project_id": project["project_id"],
        "project_name": project.get("project_name"),
        "analyzed_at": as_of.isoformat(),
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "risk": risk,
        "primary_risk": primary_risk_label(anomalies),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "explanations": explanations,
        "recommendation": recommendation,
        "validation": validation,
        "similar_projects": similar,
        "lineage": lineage_for(project, len(anomalies)),
        "risk_bands": band_summary(),
        "verification_checklist": checklist,
        "verification_note": CHECKLIST_NOTE,
        "score_drivers": what_if(anomalies),
        "disclaimer": DISCLAIMER,
    }


def analyze_corpus(projects: list[dict], as_of: date | None = None) -> dict:
    """Analyse every project. Returns {project_id: analysis}."""
    index = build_similarity_index(projects)
    return {p["project_id"]: analyze_project(p, index, as_of=as_of) for p in projects}
