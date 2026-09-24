"""Dashboard statistics, investigation queue and agency profiles.

Each view is narrowed to the acting user's area of responsibility. The analysis
underneath is unchanged — a work's score is the same figure whoever reads it;
role only decides which works appear in the list.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import rbac
from ..database import get_db
from ..rbac import User, current_user
from ..schemas import AgencyListResponse, DashboardStats, QueueResponse
from ..services import analysis_service as svc
from ..services import case_service as cases
from ..services import intelligence_service as intel

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    top: int = Query(5, ge=1, le=20),
    user: User = Depends(current_user),
):
    """Portfolio-level figures, all derived from live analysis of every work."""
    context = rbac.scoped_context(svc.build_context(db), user)
    stats = svc.dashboard_stats(context, top_n=top)
    stats["generated_at"] = datetime.now()
    stats["scope"] = rbac.scope_label(user)
    return stats


@router.get("/investigation-queue", response_model=QueueResponse)
def investigation_queue(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Works with at least one risk signal, ordered highest risk first.

    Each row carries the state of its investigation case, if one has been
    opened, so the queue shows what has already been picked up rather than
    listing the same works to every officer every day.
    """
    context = rbac.scoped_context(svc.build_context(db), user)
    items = svc.investigation_queue(context)

    index = cases.case_index(db) if user.can("view.cases") else {}
    for item in items:
        state = index.get(item["project_id"])
        item["case_id"] = state["case_id"] if state else None
        item["case_status"] = state["status"] if state else None
        item["case_assigned_to"] = state["assigned_to"] if state else None
        item["case_outcome"] = state["outcome"] if state else None

    return {
        "total": len(items),
        "data_notice": svc.DATA_NOTICE,
        "items": items,
        "scope": rbac.scope_label(user),
        "open_cases": sum(1 for i in items if i["case_id"]),
        "permissions": {cap: user.can(cap) for cap in rbac.CAPABILITIES},
    }


@router.get("/agencies", response_model=AgencyListResponse)
def agencies(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Risk aggregated by implementing agency."""
    context = rbac.scoped_context(svc.build_context(db), user)
    profiles = svc.agency_profiles(context)
    return {
        "total": len(profiles),
        "data_notice": svc.DATA_NOTICE,
        "agencies": profiles,
        "scope": rbac.scope_label(user),
        "notice": intel.AGENCY_NOTICE,
    }
