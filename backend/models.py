"""SQLAlchemy models for the MPLADS-style synthetic dataset."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Project(Base):
    """One sanctioned MPLADS-style work.

    Nullable columns are nullable on purpose: the validation engine needs to be
    able to encounter genuinely missing fields, which is one of the risk signals
    the prototype demonstrates.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # Identity ------------------------------------------------------------
    project_name: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    work_type: Mapped[str | None] = mapped_column(String(120), index=True)
    sector: Mapped[str | None] = mapped_column(String(120), index=True)

    # Location ------------------------------------------------------------
    location: Mapped[str | None] = mapped_column(String(200))
    village: Mapped[str | None] = mapped_column(String(120), index=True)
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(120), index=True)
    constituency: Mapped[str | None] = mapped_column(String(160))
    mp_name: Mapped[str | None] = mapped_column(String(160))
    implementing_agency: Mapped[str | None] = mapped_column(String(200), index=True)

    # Timeline ------------------------------------------------------------
    recommendation_date: Mapped[date | None] = mapped_column(Date)
    sanction_date: Mapped[date | None] = mapped_column(Date)
    start_date: Mapped[date | None] = mapped_column(Date)
    expected_completion_date: Mapped[date | None] = mapped_column(Date)
    actual_completion_date: Mapped[date | None] = mapped_column(Date)

    # Finance -------------------------------------------------------------
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    sanctioned_cost: Mapped[float | None] = mapped_column(Float)
    actual_expenditure: Mapped[float | None] = mapped_column(Float)

    # Progress ------------------------------------------------------------
    physical_progress: Mapped[float | None] = mapped_column(Float)
    financial_progress: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str | None] = mapped_column(String(60), index=True)

    # Geography -----------------------------------------------------------
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Lineage -------------------------------------------------------------
    data_source: Mapped[str] = mapped_column(
        String(120), default="Synthetic Demonstration Record"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Payment.transaction_sequence"
    )

    def as_dict(self) -> dict:
        """Plain-dict view handed to the anomaly engine.

        The engine never sees an ORM object — that is what keeps it independent
        of the storage layer and directly unit-testable.
        """
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "description": self.description,
            "work_type": self.work_type,
            "sector": self.sector,
            "location": self.location,
            "village": self.village,
            "district": self.district,
            "state": self.state,
            "constituency": self.constituency,
            "mp_name": self.mp_name,
            "implementing_agency": self.implementing_agency,
            "recommendation_date": self.recommendation_date,
            "sanction_date": self.sanction_date,
            "start_date": self.start_date,
            "expected_completion_date": self.expected_completion_date,
            "actual_completion_date": self.actual_completion_date,
            "estimated_cost": self.estimated_cost,
            "sanctioned_cost": self.sanctioned_cost,
            "actual_expenditure": self.actual_expenditure,
            "physical_progress": self.physical_progress,
            "financial_progress": self.financial_progress,
            "status": self.status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "data_source": self.data_source,
        }


class Payment(Base):
    """A release against a work. Kept deliberately simple for the prototype."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.project_id", ondelete="CASCADE"), index=True
    )
    payment_amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[date | None] = mapped_column(Date)
    vendor: Mapped[str | None] = mapped_column(String(200))
    transaction_sequence: Mapped[int] = mapped_column(Integer, default=1)

    project: Mapped[Project] = relationship(back_populates="payments")

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "payment_amount": self.payment_amount,
            "payment_date": self.payment_date,
            "vendor": self.vendor,
            "transaction_sequence": self.transaction_sequence,
        }


# --------------------------------------------------------------------------
# Investigation case workflow
#
# Everything above this line is the synthetic register — the data being
# analysed. Everything below is the record of what officers did about it.
#
# The separation matters: risk scores are never written to the register, and
# case activity never edits a project record. A case is an overlay on a work,
# so the assessment and the investigation of it can always be told apart.
# --------------------------------------------------------------------------


#: The workflow a case moves through. Held here rather than as a database
#: enum so the allowed transitions can be read in one place.
CASE_STATUSES = (
    "OPEN",
    "ASSIGNED",
    "UNDER VERIFICATION",
    "CLARIFICATION REQUESTED",
    "ESCALATED",
    "CLOSED",
)

#: What an officer concluded. Recorded at closure; never inferred by the system.
CASE_OUTCOMES = (
    "Valid Risk",
    "False Positive",
    "Requires Clarification",
    "Escalated",
    "No Issue Found",
)


class InvestigationCase(Base):
    """An officer's working file against one work.

    The risk figures stored here are a snapshot of what the engine assessed at
    the moment the case was opened. They are kept so that a closed case still
    shows the assessment it was opened on, even after the register changes and
    the live score moves. The live score is always recomputed; this is history.
    """

    __tablename__ = "investigation_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.project_id", ondelete="CASCADE"), index=True
    )

    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    outcome: Mapped[str | None] = mapped_column(String(48))
    outcome_remark: Mapped[str | None] = mapped_column(Text)

    assigned_to: Mapped[str | None] = mapped_column(String(120))
    assigned_role: Mapped[str | None] = mapped_column(String(32))
    opened_by: Mapped[str | None] = mapped_column(String(120))
    opened_role: Mapped[str | None] = mapped_column(String(32))

    # Snapshot of the assessment the case was opened on.
    risk_score_at_open: Mapped[float | None] = mapped_column(Float)
    risk_level_at_open: Mapped[str | None] = mapped_column(String(16))
    primary_risk_at_open: Mapped[str | None] = mapped_column(String(160))

    # Scope, copied from the work so a case can be filtered by role without
    # joining back to the register on every query.
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(120), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    items: Mapped[list[VerificationItem]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="VerificationItem.id"
    )

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "project_id": self.project_id,
            "status": self.status,
            "outcome": self.outcome,
            "outcome_remark": self.outcome_remark,
            "assigned_to": self.assigned_to,
            "assigned_role": self.assigned_role,
            "opened_by": self.opened_by,
            "opened_role": self.opened_role,
            "risk_score_at_open": self.risk_score_at_open,
            "risk_level_at_open": self.risk_level_at_open,
            "primary_risk_at_open": self.primary_risk_at_open,
            "district": self.district,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
        }


class VerificationItem(Base):
    """One check on a case's checklist.

    Items are generated from the signals actually detected on the work (see
    ``anomaly_engine.verification_checklist``), so the list is specific to the
    record rather than a standard form.
    """

    __tablename__ = "verification_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("investigation_cases.case_id", ondelete="CASCADE"), index=True
    )

    item_key: Mapped[str] = mapped_column(String(64), index=True)
    signal_type: Mapped[str] = mapped_column(String(48), index=True)
    signal_title: Mapped[str | None] = mapped_column(String(120))
    label: Mapped[str] = mapped_column(String(200))
    hint: Mapped[str | None] = mapped_column(Text)
    recorded: Mapped[str | None] = mapped_column(Text)

    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(Text)
    evidence_ref: Mapped[str | None] = mapped_column(String(300))
    completed_by: Mapped[str | None] = mapped_column(String(120))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    case: Mapped[InvestigationCase] = relationship(back_populates="items")

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "key": self.item_key,
            "signal_type": self.signal_type,
            "signal_title": self.signal_title,
            "label": self.label,
            "hint": self.hint,
            "recorded": self.recorded,
            "completed": self.completed,
            "remark": self.remark,
            "evidence_ref": self.evidence_ref,
            "completed_by": self.completed_by,
            "completed_at": self.completed_at,
        }


class CaseEvent(Base):
    """One line of the audit trail.

    Append-only by convention: nothing in the application updates or deletes a
    row here. An audit trail that can be edited is not an audit trail.

    Deliberately unrelated to :class:`InvestigationCase` by ORM relationship and
    unconstrained by a foreign key — the trail stands on its own and outlives
    whatever it describes. ``case_id`` is also left empty for events that
    precede a case, such as a risk alert being raised on a work.
    """

    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str | None] = mapped_column(String(32), index=True)
    project_id: Mapped[str | None] = mapped_column(String(32), index=True)

    event_type: Mapped[str] = mapped_column(String(48), index=True)
    summary: Mapped[str] = mapped_column(String(400))
    remark: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(120))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    reference: Mapped[str | None] = mapped_column(String(300))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "remark": self.remark,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "reference": self.reference,
            "created_at": self.created_at,
        }
