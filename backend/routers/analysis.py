"""
Analysis endpoints.

``POST /api/projects/{id}/analyze`` is the endpoint the "Analyze Risk" button
calls. It runs the real pipeline every time; nothing is precomputed and nothing
is faked in the browser.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from anomaly_engine import risk_engine
from anomaly_engine.config import RISK_BANDS, WEIGHTS
from anomaly_engine.explanation_engine import DISCLAIMER

from ..database import get_db
from ..schemas import AnomalyListResponse, VerificationRequest, VerificationResponse
from ..services import analysis_service as svc

router = APIRouter(prefix="/api", tags=["analysis"])


def _analyse_or_404(db: Session, project_id: str) -> dict:
    if svc.load_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    context = svc.build_context(db)
    analysis = context["analyses"][project_id]
    analysis["nearby_projects"] = svc.nearby_projects(context, project_id)
    analysis["data_notice"] = svc.DATA_NOTICE
    return analysis


@router.post("/projects/{project_id}/analyze")
def analyze(project_id: str, db: Session = Depends(get_db)):
    """Run the full risk assessment for one work.

    Sequence: validate the record, run the four anomaly detectors, look for
    overlapping works across the corpus, fuse the signals into a score, then
    generate explanations and recommended verification steps.
    """
    return _analyse_or_404(db, project_id)


@router.get("/projects/{project_id}/analyze")
def analyze_get(project_id: str, db: Session = Depends(get_db)):
    """GET form of the same analysis, so the result is linkable and testable."""
    return _analyse_or_404(db, project_id)


@router.get("/projects/{project_id}/anomalies", response_model=AnomalyListResponse)
def anomalies(project_id: str, db: Session = Depends(get_db)):
    """Just the detected signals, without the surrounding narrative."""
    analysis = _analyse_or_404(db, project_id)
    return {
        "project_id": project_id,
        "risk_score": analysis["risk_score"],
        "risk_level": analysis["risk_level"],
        "anomaly_count": analysis["anomaly_count"],
        "anomalies": analysis["anomalies"],
        "disclaimer": DISCLAIMER,
    }


@router.post("/projects/{project_id}/verify", response_model=VerificationResponse)
def verify(project_id: str, payload: VerificationRequest, db: Session = Depends(get_db)):
    """Recompute the score with officer-cleared signals withheld.

    The officer ticks the signals they have checked and found explained. The
    engine then re-runs its own fusion arithmetic with those families
    contributing zero, so the adjusted figure is computed by the same rule as
    the original and remains reconstructable by hand.

    Nothing is persisted. This is a provisional working view for the reviewer,
    not a determination, and the underlying findings are left on record.
    """
    analysis = _analyse_or_404(db, project_id)

    detected = {a["type"] for a in analysis["anomalies"]}
    unknown = [c for c in payload.cleared if c not in WEIGHTS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown signal type(s): {', '.join(sorted(unknown))}.",
        )

    cleared = {c for c in payload.cleared if c in detected}
    adjusted = risk_engine.fuse(analysis["anomalies"], cleared=cleared)

    return {
        "project_id": project_id,
        "original_risk_score": analysis["risk_score"],
        "original_risk_level": analysis["risk_level"],
        "adjusted_risk_score": adjusted["risk_score"],
        "adjusted_risk_level": adjusted["risk_level"],
        "adjusted_raw_total": adjusted["raw_total"],
        "was_clamped": adjusted["was_clamped"],
        "points_withheld": adjusted["points_withheld"],
        "cleared_types": adjusted["cleared_types"],
        "ignored_types": sorted(set(payload.cleared) - detected),
        "breakdown": adjusted["breakdown"],
        "band_changed": adjusted["risk_level"] != analysis["risk_level"],
        "note": (
            "Provisional view only. Verification marks are not saved and no "
            "finding has been removed from the record. The determination rests "
            "with the authorised officer."
        ),
        "disclaimer": DISCLAIMER,
    }


@router.get("/methodology")
def methodology():
    """The scoring rules, published so the output can be checked by hand.

    A decision-support tool that an officer cannot audit is not much use, so
    every weight, band and threshold the engine applies is readable here.
    """
    from anomaly_engine import config as C

    return {
        "weights": WEIGHTS,
        "max_score": C.MAX_RISK_SCORE,
        "bands": [{"level": label, "min": low, "max": high} for low, high, label in RISK_BANDS],
        "thresholds": {
            "cost_tolerance_pct": C.COST_TOLERANCE_PCT,
            "cost_full_severity_pct": C.COST_FULL_SEVERITY_PCT,
            "mismatch_tolerance_pp": C.MISMATCH_TOLERANCE_PP,
            "mismatch_full_pp": C.MISMATCH_FULL_PP,
            "delay_deficit_tolerance_pp": C.DELAY_DEFICIT_TOLERANCE_PP,
            "delay_deficit_full_pp": C.DELAY_DEFICIT_FULL_PP,
            "overdue_full_severity_days": C.OVERDUE_FULL_SEVERITY_DAYS,
            "duplicate_similarity_threshold": C.DUPLICATE_SIMILARITY_THRESHOLD,
            "duplicate_similarity_full": C.DUPLICATE_SIMILARITY_FULL,
            "duplicate_distance_km": C.DUPLICATE_DISTANCE_KM,
            "data_quality_full_penalty": C.DATA_QUALITY_FULL_PENALTY,
        },
        "formula": "risk_score = clamp(sum(weight_i x severity_factor_i), 0, 100)",
        "note": (
            "Severity factors scale linearly between the tolerance threshold and "
            "the full-severity threshold for each detector, so a marginal breach "
            "scores far lower than a severe one."
        ),
        "disclaimer": DISCLAIMER,
        "data_notice": svc.DATA_NOTICE,
    }
