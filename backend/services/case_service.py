"""
Investigation case workflow.

A case is the officer-facing half of the system. The analysis engine produces a
signal; a case is what someone does about it. This module owns the transitions
between case states, the checklist attached to a case, and the audit trail that
records every one of those actions.

Three rules run through all of it:

* **Every state change writes an audit event.** There is no path through this
  module that changes a case without recording who changed it and when.
* **Nothing here changes a risk score.** Cases annotate an assessment; they do
  not revise it. The score on screen is always recomputed by the engine.
* **The system never concludes anything.** Outcomes are recorded because an
  officer selected them. The words "valid risk" or "false positive" appear in
  the database only because a person put them there.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from anomaly_engine.verification_checklist import (
    CHECKLIST_NOTE,
    build_checklist,
    checklist_summary,
)

from .. import rbac
from ..models import CASE_OUTCOMES, CASE_STATUSES, CaseEvent, InvestigationCase, VerificationItem
from ..rbac import User

# --------------------------------------------------------------------------
# Workflow
# --------------------------------------------------------------------------

#: Which statuses a case may move to from each status. A case that has been
#: closed can be reopened for clarification but cannot jump straight back to
#: OPEN, so the history of it having been worked is not erased.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "OPEN": ("ASSIGNED", "UNDER VERIFICATION", "CLARIFICATION REQUESTED", "ESCALATED", "CLOSED"),
    "ASSIGNED": ("UNDER VERIFICATION", "CLARIFICATION REQUESTED", "ESCALATED", "CLOSED"),
    "UNDER VERIFICATION": ("CLARIFICATION REQUESTED", "ESCALATED", "CLOSED", "ASSIGNED"),
    "CLARIFICATION REQUESTED": ("UNDER VERIFICATION", "ESCALATED", "CLOSED"),
    "ESCALATED": ("UNDER VERIFICATION", "CLARIFICATION REQUESTED", "CLOSED"),
    "CLOSED": ("UNDER VERIFICATION", "CLARIFICATION REQUESTED"),
}

#: Ordering for queue views — a case needing attention sorts above a settled one.
STATUS_ORDER = {status: i for i, status in enumerate(CASE_STATUSES)}

STATUS_MEANING = {
    "OPEN": "Raised from a risk signal. Not yet assigned to an officer.",
    "ASSIGNED": "Allocated to an officer. Verification has not started.",
    "UNDER VERIFICATION": "An officer is working through the verification steps.",
    "CLARIFICATION REQUESTED": "Waiting on information from the implementing agency.",
    "ESCALATED": "Referred upward for a decision beyond this officer's authority.",
    "CLOSED": "An officer has recorded an outcome. The findings stay on record.",
}

CASE_NOTICE = (
    "A case records what officers did about a risk signal. Opening a case is "
    "not an allegation and closing one is not an exoneration — both are records "
    "of process. Determinations rest with the authorised officer."
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------


def log_event(
    db: Session,
    *,
    event_type: str,
    summary: str,
    project_id: str | None = None,
    case_id: str | None = None,
    actor: User | None = None,
    remark: str | None = None,
    reference: str | None = None,
    commit: bool = False,
) -> CaseEvent:
    """Append one line to the audit trail.

    Called from every mutating path in this module. Nothing updates or deletes
    what this writes.
    """
    event = CaseEvent(
        case_id=case_id,
        project_id=project_id,
        event_type=event_type,
        summary=summary[:400],
        remark=remark,
        actor=actor.display_name if actor else None,
        actor_role=actor.role if actor else None,
        reference=reference,
        created_at=_now(),
    )
    db.add(event)
    if commit:
        db.commit()
    return event


def audit_trail(db: Session, *, case_id: str | None = None, project_id: str | None = None,
                limit: int = 200) -> list[dict[str, Any]]:
    """The recorded history, newest first."""
    query = db.query(CaseEvent)
    if case_id:
        query = query.filter(CaseEvent.case_id == case_id)
    if project_id:
        query = query.filter(CaseEvent.project_id == project_id)
    rows = query.order_by(CaseEvent.created_at.desc(), CaseEvent.id.desc()).limit(limit).all()
    return [r.as_dict() for r in rows]


# --------------------------------------------------------------------------
# Case lifecycle
# --------------------------------------------------------------------------


def _next_case_id(db: Session) -> str:
    count = db.query(func.count(InvestigationCase.id)).scalar() or 0
    return f"CASE-{count + 1:04d}"


def get_case(db: Session, case_id: str) -> InvestigationCase:
    case = db.query(InvestigationCase).filter(InvestigationCase.case_id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail=f"No case found with id '{case_id}'.")
    return case


def case_for_project(db: Session, project_id: str) -> InvestigationCase | None:
    """The most recent case on a work, if any."""
    return (
        db.query(InvestigationCase)
        .filter(InvestigationCase.project_id == project_id)
        .order_by(InvestigationCase.id.desc())
        .first()
    )


def case_index(db: Session) -> dict[str, dict[str, Any]]:
    """Compact case state for every work that has one, keyed by project id.

    One query for the whole worklist rather than one per row: the investigation
    queue needs to show whether a work is already being looked at, and the
    answer for twenty-six works should not cost twenty-six round trips.
    """
    index: dict[str, dict[str, Any]] = {}
    for case in db.query(InvestigationCase).order_by(InvestigationCase.id.asc()).all():
        # Ascending, so a later case on the same work overwrites the earlier one
        # and the row reflects the case currently in hand.
        index[case.project_id] = {
            "case_id": case.case_id,
            "status": case.status,
            "assigned_to": case.assigned_to,
            "assigned_role": case.assigned_role,
            "outcome": case.outcome,
        }
    return index


def open_case(
    db: Session,
    *,
    project: dict[str, Any],
    analysis: dict[str, Any],
    user: User,
    assign_to: str | None = None,
    remark: str | None = None,
) -> InvestigationCase:
    """Open a case against a work, seeding its checklist from the live signals.

    The checklist is materialised at this moment from the anomalies the engine
    detected, so the case carries the checks that the assessment actually
    justified rather than a standard form.
    """
    rbac.require(user, "case.create")
    rbac.assert_visible(
        user,
        state=project.get("state"),
        district=project.get("district"),
        what=f"Work {project['project_id']}",
    )

    existing = case_for_project(db, project["project_id"])
    if existing is not None and existing.status != "CLOSED":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Case {existing.case_id} is already open against "
                f"{project['project_id']} with status {existing.status}."
            ),
        )

    case = InvestigationCase(
        case_id=_next_case_id(db),
        project_id=project["project_id"],
        status="OPEN",
        opened_by=user.display_name,
        opened_role=user.role,
        risk_score_at_open=analysis["risk_score"],
        risk_level_at_open=analysis["risk_level"],
        primary_risk_at_open=analysis.get("primary_risk"),
        district=project.get("district"),
        state=project.get("state"),
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(case)
    db.flush()

    for entry in build_checklist(analysis.get("anomalies", [])):
        db.add(
            VerificationItem(
                case_id=case.case_id,
                item_key=entry["key"],
                signal_type=entry["signal_type"],
                signal_title=entry["signal_title"],
                label=entry["label"],
                hint=entry["hint"],
                recorded=entry["recorded"],
                completed=False,
            )
        )

    # The alert that justified the case is recorded before the case itself, so
    # the trail reads in the order things actually happened.
    log_event(
        db,
        event_type="RISK_ALERT_GENERATED",
        summary=(
            f"Risk signal raised on {project['project_id']}: "
            f"{analysis['risk_score']} {analysis['risk_level']} "
            f"({analysis.get('anomaly_count', 0)} signal(s) detected)"
        ),
        project_id=project["project_id"],
        case_id=case.case_id,
        reference=analysis.get("primary_risk"),
    )
    log_event(
        db,
        event_type="CASE_CREATED",
        summary=f"Case {case.case_id} opened against {project['project_id']}",
        project_id=project["project_id"],
        case_id=case.case_id,
        actor=user,
        remark=remark,
    )

    if assign_to:
        _apply_assignment(db, case, assign_to=assign_to, user=user)

    db.commit()
    db.refresh(case)
    return case


def _guard_not_closed(case: InvestigationCase, action: str) -> None:
    """Refuse work on a closed case.

    Reopening is a status change, and a deliberate one: it is recorded in the
    trail as such. Quietly reassigning or ticking an item on a closed case would
    change the record of a concluded verification without saying so.
    """
    if case.status == "CLOSED":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Case {case.case_id} is closed, so it cannot {action}. "
                "Move it back to Under Verification first if the case needs to be reopened."
            ),
        )


def _apply_assignment(db: Session, case: InvestigationCase, *, assign_to: str, user: User) -> None:
    assignee = rbac.DEMO_USERS.get(assign_to)
    if assignee is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown user '{assign_to}'. Available: {', '.join(sorted(rbac.DEMO_USERS))}.",
        )

    case.assigned_to = assignee.display_name
    case.assigned_role = assignee.role
    case.updated_at = _now()
    if case.status == "OPEN":
        case.status = "ASSIGNED"

    log_event(
        db,
        event_type="CASE_ASSIGNED",
        summary=(
            f"Case {case.case_id} assigned to {assignee.display_name} "
            f"({assignee.role_def.title})"
        ),
        project_id=case.project_id,
        case_id=case.case_id,
        actor=user,
    )


def assign_case(db: Session, case_id: str, *, assign_to: str, user: User) -> InvestigationCase:
    rbac.require(user, "case.assign")
    case = get_case(db, case_id)
    _guard_scope(user, case)
    _guard_not_closed(case, "be reassigned")
    _apply_assignment(db, case, assign_to=assign_to, user=user)
    db.commit()
    db.refresh(case)
    return case


def change_status(
    db: Session, case_id: str, *, status: str, user: User, remark: str | None = None
) -> InvestigationCase:
    """Move a case through the workflow, refusing transitions that are not allowed."""
    case = get_case(db, case_id)
    _guard_scope(user, case)

    status = status.upper().strip()
    if status not in CASE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown status '{status}'. Allowed: {', '.join(CASE_STATUSES)}.",
        )

    # Escalation and closure are separately held capabilities, because they are
    # the two transitions that carry consequences outside the case.
    if status == "ESCALATED":
        rbac.require(user, "case.escalate")
    elif status == "CLOSED":
        rbac.require(user, "case.close")
    else:
        rbac.require(user, "case.status")

    if status == case.status:
        raise HTTPException(status_code=409, detail=f"Case {case_id} is already {status}.")

    allowed = ALLOWED_TRANSITIONS.get(case.status, ())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A case that is {case.status} cannot move to {status}. "
                f"Allowed from here: {', '.join(allowed) or 'none'}."
            ),
        )

    if status == "CLOSED" and not case.outcome:
        raise HTTPException(
            status_code=422,
            detail=(
                "Record an outcome before closing the case. A case closed "
                "without a recorded finding leaves no account of what was decided."
            ),
        )

    previous, case.status = case.status, status
    case.updated_at = _now()
    case.closed_at = _now() if status == "CLOSED" else None

    event_type = {
        "ESCALATED": "CASE_ESCALATED",
        "CLOSED": "CASE_CLOSED",
    }.get(status, "STATUS_CHANGED")

    log_event(
        db,
        event_type=event_type,
        summary=f"Case {case.case_id} moved from {previous} to {status}",
        project_id=case.project_id,
        case_id=case.case_id,
        actor=user,
        remark=remark,
    )
    db.commit()
    db.refresh(case)
    return case


def record_outcome(
    db: Session, case_id: str, *, outcome: str, user: User, remark: str | None = None
) -> InvestigationCase:
    """Record the officer's conclusion on a case.

    The outcome is stored exactly as the officer selected it. The system does
    not derive it, weight it, or feed it back into the scoring model — there is
    no learning pipeline in this prototype, and recording an outcome does not
    change how any future work is scored.
    """
    rbac.require(user, "case.close")
    case = get_case(db, case_id)
    _guard_scope(user, case)

    if outcome not in CASE_OUTCOMES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown outcome '{outcome}'. Allowed: {', '.join(CASE_OUTCOMES)}.",
        )

    case.outcome = outcome
    case.outcome_remark = remark
    case.updated_at = _now()

    log_event(
        db,
        event_type="OUTCOME_RECORDED",
        summary=f"Outcome recorded on {case.case_id}: {outcome}",
        project_id=case.project_id,
        case_id=case.case_id,
        actor=user,
        remark=remark,
    )
    db.commit()
    db.refresh(case)
    return case


def add_remark(
    db: Session, case_id: str, *, remark: str, user: User, reference: str | None = None
) -> CaseEvent:
    """Add a free-text officer remark, optionally with a reference to evidence."""
    rbac.require(user, "case.verify")
    case = get_case(db, case_id)
    _guard_scope(user, case)

    text = (remark or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="A remark cannot be empty.")

    case.updated_at = _now()
    event = log_event(
        db,
        event_type="EVIDENCE_ADDED" if reference else "REMARK_ADDED",
        summary=(
            f"Evidence reference added to {case.case_id}"
            if reference
            else f"Remark added to {case.case_id}"
        ),
        project_id=case.project_id,
        case_id=case.case_id,
        actor=user,
        remark=text,
        reference=reference,
    )
    db.commit()
    db.refresh(event)
    return event


def update_item(
    db: Session,
    case_id: str,
    item_key: str,
    *,
    user: User,
    completed: bool | None = None,
    remark: str | None = None,
    evidence_ref: str | None = None,
) -> VerificationItem:
    """Complete or annotate one verification step."""
    rbac.require(user, "case.verify")
    case = get_case(db, case_id)
    _guard_scope(user, case)
    _guard_not_closed(case, "take further verification entries")

    item = (
        db.query(VerificationItem)
        .filter(VerificationItem.case_id == case_id, VerificationItem.item_key == item_key)
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"No verification step '{item_key}' on case {case_id}."
        )

    changes: list[str] = []
    if completed is not None and completed != item.completed:
        item.completed = completed
        item.completed_by = user.display_name if completed else None
        item.completed_at = _now() if completed else None
        changes.append("marked complete" if completed else "reopened")
    if remark is not None:
        item.remark = remark.strip() or None
        changes.append("remark recorded")
    if evidence_ref is not None:
        item.evidence_ref = evidence_ref.strip() or None
        changes.append("evidence reference recorded")

    if changes:
        case.updated_at = _now()
        # Working a step implies the case is being verified; reflect that rather
        # than making the officer set the status separately.
        if item.completed and case.status in ("OPEN", "ASSIGNED"):
            previous, case.status = case.status, "UNDER VERIFICATION"
            log_event(
                db,
                event_type="STATUS_CHANGED",
                summary=f"Case {case.case_id} moved from {previous} to UNDER VERIFICATION",
                project_id=case.project_id,
                case_id=case.case_id,
                actor=user,
                remark="Set automatically when the first verification step was completed.",
            )

        log_event(
            db,
            event_type="VERIFICATION_ITEM_UPDATED",
            summary=f"{item.label} — {', '.join(changes)}",
            project_id=case.project_id,
            case_id=case.case_id,
            actor=user,
            remark=item.remark,
            reference=item.evidence_ref,
        )

    db.commit()
    db.refresh(item)
    return item


def _guard_scope(user: User, case: InvestigationCase) -> None:
    rbac.assert_visible(user, state=case.state, district=case.district, what=f"Case {case.case_id}")


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def list_cases(db: Session, user: User, *, status: str | None = None,
               project_id: str | None = None) -> list[dict[str, Any]]:
    """Cases the acting user may see, most recently touched first."""
    rbac.require(user, "view.cases")
    query = db.query(InvestigationCase)
    if status:
        query = query.filter(InvestigationCase.status == status.upper())
    if project_id:
        query = query.filter(InvestigationCase.project_id == project_id)

    rows = [c for c in query.all()
            if rbac.in_scope(user, state=c.state, district=c.district)]
    rows.sort(key=lambda c: (STATUS_ORDER.get(c.status, 99), -(c.risk_score_at_open or 0)))
    return [_summarise(db, c) for c in rows]


def _summarise(db: Session, case: InvestigationCase) -> dict[str, Any]:
    items = db.query(VerificationItem).filter(VerificationItem.case_id == case.case_id).all()
    payload = case.as_dict()
    payload["checklist_summary"] = checklist_summary([i.as_dict() for i in items])
    payload["status_meaning"] = STATUS_MEANING.get(case.status, "")
    return payload


def case_detail(db: Session, case_id: str, user: User) -> dict[str, Any]:
    """One case with its checklist, its audit trail and the transitions available."""
    rbac.require(user, "view.cases")
    case = get_case(db, case_id)
    _guard_scope(user, case)

    items = (
        db.query(VerificationItem)
        .filter(VerificationItem.case_id == case_id)
        .order_by(VerificationItem.id)
        .all()
    )
    item_dicts = [i.as_dict() for i in items]

    payload = case.as_dict()
    payload.update(
        {
            "status_meaning": STATUS_MEANING.get(case.status, ""),
            "checklist": item_dicts,
            "checklist_summary": checklist_summary(item_dicts),
            "checklist_note": CHECKLIST_NOTE,
            "audit_trail": audit_trail(db, case_id=case_id),
            "available_statuses": list(ALLOWED_TRANSITIONS.get(case.status, ())),
            "available_outcomes": list(CASE_OUTCOMES),
            "assignable_users": [
                {"username": u.username, "display_name": u.display_name,
                 "role": u.role, "designation": u.designation}
                for u in rbac.DEMO_USERS.values()
                if u.can("case.verify") or u.can("case.status")
            ],
            "permissions": {
                cap: user.can(cap)
                for cap in ("case.assign", "case.status", "case.verify",
                            "case.escalate", "case.close")
            },
            "notice": CASE_NOTICE,
        }
    )
    return payload


def case_stats(db: Session, user: User) -> dict[str, Any]:
    """Counts by status for the queue header."""
    cases = list_cases(db, user)
    by_status = {status: 0 for status in CASE_STATUSES}
    for case in cases:
        by_status[case["status"]] = by_status.get(case["status"], 0) + 1
    return {
        "total": len(cases),
        "open": sum(v for k, v in by_status.items() if k != "CLOSED"),
        "closed": by_status.get("CLOSED", 0),
        "by_status": [
            {"status": s, "count": by_status.get(s, 0), "meaning": STATUS_MEANING.get(s, "")}
            for s in CASE_STATUSES
        ],
    }
