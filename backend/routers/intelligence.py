"""
Derived intelligence endpoints.

Compliance, trend, early warning and the relationship network. Each is an
aggregation over the same analysis context the rest of the API uses, narrowed to
the acting user's area of responsibility.
"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import rbac
from ..database import get_db
from ..rbac import User, current_user
from ..services import analysis_service as svc
from ..services import case_service as cases
from ..services import intelligence_service as intel

router = APIRouter(prefix="/api", tags=["intelligence"])


def _scoped_context(db: Session, user: User) -> dict:
    """Build the analysis context and narrow it to the acting user's area."""
    return rbac.scoped_context(svc.build_context(db), user)


@router.get("/compliance")
def compliance(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Compliance grade for every work in scope."""
    report = intel.compliance_report(_scoped_context(db, user))
    report["scope"] = rbac.scope_label(user)
    report["data_notice"] = svc.DATA_NOTICE
    return report


@router.get("/trends")
def trends(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Risk composition of works grouped by the quarter they were sanctioned in."""
    report = intel.trend_analysis(_scoped_context(db, user))
    report["scope"] = rbac.scope_label(user)
    report["data_notice"] = svc.DATA_NOTICE
    return report


@router.get("/watchlist")
def watchlist(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Works whose indicators are deteriorating but have not yet raised a signal."""
    report = intel.watchlist(_scoped_context(db, user))
    report["scope"] = rbac.scope_label(user)
    report["data_notice"] = svc.DATA_NOTICE
    return report


@router.get("/projects/{project_id}/network")
def project_network(
    project_id: str,
    radius_km: float = Query(default=25.0, gt=0, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Recorded relationships between one work and others.

    The network is drawn over the whole corpus, because a duplicate signal is
    only meaningful against every other work. Works outside the user's scope are
    named but their figures are withheld.
    """
    row = svc.load_project(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    rbac.assert_visible(
        user, state=row.state, district=row.district, what=f"Work {project_id}"
    )

    context = svc.build_context(db)
    network = intel.network_for(context, project_id, radius_km=radius_km)

    withheld = 0
    for node in network["nodes"]:
        if rbac.in_scope(user, state=node.get("state"), district=node.get("district")):
            continue
        # The work is named and its relationship to the origin is still shown —
        # that relationship is what makes the origin worth looking at — but its
        # own figures belong to another officer's area.
        node.update({"risk_score": None, "risk_level": None, "anomaly_count": None,
                     "sanctioned_cost": None, "out_of_scope": True})
        withheld += 1

    network["withheld_nodes"] = withheld
    network["scope"] = rbac.scope_label(user)
    network["data_notice"] = svc.DATA_NOTICE
    return network


@router.get("/agencies/{agency:path}")
def agency_detail(
    agency: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """One agency's works, signal mix, highest-risk items and open cases."""
    # The :path converter hands over the raw segment, so an agency name with a
    # space or comma arrives percent-encoded and has to be decoded here.
    agency = unquote(agency)
    context = _scoped_context(db, user)
    case_list = cases.list_cases(db, user) if user.can("view.cases") else []
    detail = intel.agency_detail(context, agency, cases=case_list)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"No works recorded for '{agency}' within {rbac.scope_label(user)}.",
        )
    detail["scope"] = rbac.scope_label(user)
    detail["data_notice"] = svc.DATA_NOTICE
    return detail


@router.get("/projects/{project_id}/what-if")
def what_if(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """What the score would be with each detected signal withheld in turn.

    Every figure is the engine re-running its own fusion arithmetic, not an
    estimate. It answers "what is driving this number".
    """
    row = svc.load_project(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No project found with id '{project_id}'.")
    rbac.assert_visible(user, state=row.state, district=row.district, what=f"Work {project_id}")

    analysis = svc.build_context(db)["analyses"][project_id]
    return {
        "project_id": project_id,
        "project_name": analysis["project_name"],
        **analysis["score_drivers"],
        "breakdown": analysis["risk"]["breakdown"],
        "data_notice": svc.DATA_NOTICE,
    }
