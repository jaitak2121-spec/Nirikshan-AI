"""Project listing, detail, similarity and geographic-proximity endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import rbac
from ..database import get_db
from ..rbac import User, current_user
from ..schemas import (
    ProjectDetail,
    ProjectListResponse,
    SimilarResponse,
)
from ..services import analysis_service as svc

router = APIRouter(prefix="/api/projects", tags=["projects"])

#: Accepted values are constrained rather than parsed loosely. A misspelt filter
#: would otherwise fall through and return the whole register, which looks like
#: a working filter that quietly does nothing — worse than a 422.
RiskLevel = Literal["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
SortOrder = Literal["risk_desc", "risk_asc", "cost_desc", "name_asc"]


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="Match on id, name, district, village or agency"),
    risk_level: RiskLevel | None = Query(None, description="Filter by computed risk band"),
    district: str | None = None,
    agency: str | None = None,
    sort: SortOrder = Query("risk_desc", description="Ordering of the returned rows"),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(current_user),
):
    """Every work in the acting user's area, each with a freshly computed score.

    Filtering happens after analysis rather than in SQL, because risk level is
    not a stored column — it only exists once the engine has run. Role scope is
    applied the same way, and before every other filter: a district officer's
    "all works" is their district's works.

    The analysis itself still runs over the whole register. Duplicate detection
    compares a work against every other work, so narrowing the corpus would
    change the scores — a district officer must see the same score for a work as
    the ministry does.
    """
    context = svc.build_context(db)
    items = rbac.filter_rows(user, svc.project_summaries(context))

    if search:
        needle = search.strip().lower()
        fields = ("project_id", "project_name", "district", "village", "implementing_agency", "work_type")
        items = [i for i in items if any(needle in str(i.get(f) or "").lower() for f in fields)]

    if risk_level and risk_level != "ALL":
        items = [i for i in items if i["risk_level"] == risk_level]

    if district:
        items = [i for i in items if (i.get("district") or "").lower() == district.lower()]

    if agency:
        items = [i for i in items if (i.get("implementing_agency") or "").lower() == agency.lower()]

    sorters = {
        "risk_desc": lambda i: (-i["risk_score"], i["project_id"]),
        "risk_asc": lambda i: (i["risk_score"], i["project_id"]),
        "cost_desc": lambda i: (-(i.get("sanctioned_cost") or 0), i["project_id"]),
        "name_asc": lambda i: (i.get("project_name") or "").lower(),
    }
    items.sort(key=sorters[sort])

    # ``total`` is the size of what this user may see, so the count under a
    # filtered table never exceeds the count above it.
    visible = len(rbac.filter_rows(user, svc.project_summaries(context)))
    return {
        "total": visible,
        "returned": len(items[:limit]),
        "matched": len(items),
        "data_notice": svc.DATA_NOTICE,
        "projects": items[:limit],
    }


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """One work with its stored fields, payment releases and full analysis."""
    row = svc.load_project(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    rbac.assert_visible(user, state=row.state, district=row.district, what=f"Work {project_id}")

    context = svc.build_context(db)
    analysis = context["analyses"][project_id]

    payload = svc.summarise(row, analysis)
    payload["payments"] = [p.as_dict() for p in row.payments]
    payload["analysis"] = analysis
    payload["analysis"]["nearby_projects"] = svc.nearby_projects(context, project_id)
    return payload


@router.get("/{project_id}/similar", response_model=SimilarResponse)
def get_similar(
    project_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(5, ge=1, le=20),
    user: User = Depends(current_user),
):
    """Textually and geographically comparable works.

    A match here is a prompt to verify, never a conclusion. Two works can look
    alike because they genuinely duplicate each other, or because a district
    simply builds a lot of similar assets.
    """
    row = svc.load_project(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    rbac.assert_visible(user, state=row.state, district=row.district, what=f"Work {project_id}")

    from anomaly_engine.config import DUPLICATE_SIMILARITY_THRESHOLD
    from anomaly_engine.explanation_engine import DISCLAIMER

    context = svc.build_context(db)
    return {
        "project_id": project_id,
        "threshold": DUPLICATE_SIMILARITY_THRESHOLD,
        "data_notice": svc.DATA_NOTICE,
        "disclaimer": DISCLAIMER,
        "matches": svc.similar_projects(context, project_id, limit=limit),
    }


@router.get("/{project_id}/nearby")
def get_nearby(
    project_id: str,
    db: Session = Depends(get_db),
    radius_km: float = Query(25.0, gt=0, le=500),
    user: User = Depends(current_user),
):
    """Other works within a radius, by great-circle distance."""
    row = svc.load_project(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    rbac.assert_visible(user, state=row.state, district=row.district, what=f"Work {project_id}")

    context = svc.build_context(db)
    return {
        "project_id": project_id,
        "radius_km": radius_km,
        "has_coordinates": row.latitude is not None and row.longitude is not None,
        "origin": {"latitude": row.latitude, "longitude": row.longitude},
        "data_notice": svc.DATA_NOTICE,
        "nearby": svc.nearby_projects(context, project_id, radius_km=radius_km),
    }
