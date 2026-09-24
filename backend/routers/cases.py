"""
Investigation case endpoints.

The half of the API that records what officers did, as opposed to what the
engine found. Every mutating endpoint here checks a capability before acting and
writes an audit event after acting — both in ``services.case_service``, so there
is one place to read the rules rather than one per route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import rbac
from ..database import get_db
from ..rbac import User, current_user
from ..schemas import (
    CaseAssignRequest,
    CaseCreateRequest,
    CaseOutcomeRequest,
    CaseRemarkRequest,
    CaseStatusRequest,
    VerificationItemRequest,
)
from ..services import analysis_service as svc
from ..services import case_service as cases

router = APIRouter(prefix="/api", tags=["cases"])


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


@router.get("/roles")
def roles():
    """The four roles, what each may see and what each may do.

    Published rather than kept internal: a reviewer should be able to read the
    permission model without reading the source.
    """
    return {
        "roles": [
            {
                "name": role.name,
                "title": role.title,
                "summary": role.summary,
                "scope": role.scope,
                "capabilities": sorted(role.capabilities),
                "responsibilities": list(role.responsibilities),
            }
            for role in rbac.ROLES.values()
        ],
        "capabilities": list(rbac.CAPABILITIES),
        "users": [u.as_dict() for u in rbac.DEMO_USERS.values()],
        "notice": rbac.AUTH_NOTICE,
    }


@router.get("/me")
def me(user: User = Depends(current_user)):
    """Who the API believes is acting, and what that identity may do."""
    return {"user": user.as_dict(), "notice": rbac.AUTH_NOTICE}


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


@router.get("/cases")
def list_cases(
    status: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Cases within the acting user's area of responsibility."""
    items = cases.list_cases(db, user, status=status, project_id=project_id)
    return {
        "total": len(items),
        "cases": items,
        "stats": cases.case_stats(db, user),
        "scope": rbac.scope_label(user),
        "permissions": {cap: user.can(cap) for cap in rbac.CAPABILITIES},
        "notice": cases.CASE_NOTICE,
        "data_notice": svc.DATA_NOTICE,
    }


@router.post("/cases", status_code=201)
def create_case(
    payload: CaseCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Open a case against a work, seeding its checklist from the live signals."""
    row = svc.load_project(db, payload.project_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"No project found with id '{payload.project_id}'."
        )

    context = svc.build_context(db)
    analysis = context["analyses"][payload.project_id]
    case = cases.open_case(
        db,
        project=row.as_dict(),
        analysis=analysis,
        user=user,
        assign_to=payload.assign_to,
        remark=payload.remark,
    )
    return cases.case_detail(db, case.case_id, user)


@router.get("/cases/{case_id}")
def case_detail(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """One case with its checklist, its audit trail and the moves available."""
    detail = cases.case_detail(db, case_id, user)

    # The live assessment travels with the case so the page can show the score
    # as it stands now next to the score the case was opened on.
    context = svc.build_context(db)
    analysis = context["analyses"].get(detail["project_id"])
    if analysis:
        row = svc.load_project(db, detail["project_id"])
        detail["project"] = row.as_dict() if row else None
        detail["analysis"] = analysis
    detail["data_notice"] = svc.DATA_NOTICE
    return detail


@router.post("/cases/{case_id}/assign")
def assign(
    case_id: str,
    payload: CaseAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cases.assign_case(db, case_id, assign_to=payload.assign_to, user=user)
    return cases.case_detail(db, case_id, user)


@router.post("/cases/{case_id}/status")
def set_status(
    case_id: str,
    payload: CaseStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cases.change_status(db, case_id, status=payload.status, user=user, remark=payload.remark)
    return cases.case_detail(db, case_id, user)


@router.post("/cases/{case_id}/outcome")
def set_outcome(
    case_id: str,
    payload: CaseOutcomeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Record the officer's conclusion.

    Stored exactly as selected. The prototype has no learning pipeline: an
    outcome recorded here does not adjust any weight, threshold or future score.
    """
    cases.record_outcome(db, case_id, outcome=payload.outcome, user=user, remark=payload.remark)
    return cases.case_detail(db, case_id, user)


@router.post("/cases/{case_id}/remarks")
def add_remark(
    case_id: str,
    payload: CaseRemarkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cases.add_remark(db, case_id, remark=payload.remark, user=user, reference=payload.reference)
    return cases.case_detail(db, case_id, user)


@router.patch("/cases/{case_id}/checklist/{item_key:path}")
def update_item(
    case_id: str,
    item_key: str,
    payload: VerificationItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Complete or annotate one verification step."""
    cases.update_item(
        db,
        case_id,
        item_key,
        user=user,
        completed=payload.completed,
        remark=payload.remark,
        evidence_ref=payload.evidence_ref,
    )
    return cases.case_detail(db, case_id, user)


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------


@router.get("/audit")
def audit(
    case_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """The recorded history of actions, newest first.

    Reading the whole trail across every case is an administrative capability;
    reading one case's trail follows that case's own scope.
    """
    if case_id:
        cases.get_case(db, case_id)  # 404 before any scope check leaks existence
        cases.case_detail(db, case_id, user)  # enforces scope and view.cases
    elif not user.can("admin.audit"):
        raise HTTPException(
            status_code=403,
            detail=(
                f"The {user.role_def.title} role cannot read the full audit trail. "
                "Open a case to see its own history."
            ),
        )

    events = cases.audit_trail(db, case_id=case_id, project_id=project_id, limit=limit)
    return {
        "total": len(events),
        "events": events,
        "scope": rbac.scope_label(user),
        "note": (
            "Append-only record of actions taken in this system. Nothing here is "
            "edited or removed once written."
        ),
    }
