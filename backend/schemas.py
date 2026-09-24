"""
Pydantic response schemas.

Two styles are used deliberately:

* The list, summary and statistics endpoints are strictly typed — those shapes
  are what the frontend tables and charts bind to, so a contract is worth having.
* The analysis payload is passed through as a structured mapping. Its shape is
  owned by ``anomaly_engine`` and is already well-defined there; re-declaring
  every nested evidence row here would duplicate that definition and mean two
  places to change whenever a detector gains a field.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_amount: float
    payment_date: date | None = None
    vendor: str | None = None
    transaction_sequence: int


class ProjectBase(BaseModel):
    """Every stored field of a work."""

    model_config = ConfigDict(from_attributes=True)

    project_id: str
    project_name: str | None = None
    description: str | None = None
    work_type: str | None = None
    sector: str | None = None
    location: str | None = None
    village: str | None = None
    district: str | None = None
    state: str | None = None
    constituency: str | None = None
    mp_name: str | None = None
    implementing_agency: str | None = None
    recommendation_date: date | None = None
    sanction_date: date | None = None
    start_date: date | None = None
    expected_completion_date: date | None = None
    actual_completion_date: date | None = None
    estimated_cost: float | None = None
    sanctioned_cost: float | None = None
    actual_expenditure: float | None = None
    physical_progress: float | None = None
    financial_progress: float | None = None
    status: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    data_source: str = "Synthetic Demonstration Record"


class ProjectSummary(ProjectBase):
    """A work plus its freshly computed risk figures.

    ``risk_score`` is never read from storage. It is produced by the anomaly
    engine at request time, which is why it lives on this response model rather
    than on the database model.
    """

    risk_score: float
    risk_level: str
    anomaly_count: int
    primary_risk: str
    anomaly_types: list[str] = Field(default_factory=list)


class ProjectDetail(ProjectSummary):
    payments: list[PaymentOut] = Field(default_factory=list)
    analysis: dict[str, Any]


class ProjectListResponse(BaseModel):
    total: int  # works in the register
    matched: int  # works passing the filters
    returned: int  # works actually in this response, after `limit`
    data_notice: str
    projects: list[ProjectSummary]


class RiskDistributionItem(BaseModel):
    level: str
    count: int
    color: str


class AnomalyTypeCount(BaseModel):
    type: str
    title: str
    count: int


class DashboardStats(BaseModel):
    total_projects: int
    high_risk_projects: int
    critical_projects: int
    total_anomalies: int
    total_sanctioned_cost: float
    total_expenditure: float
    average_risk_score: float
    projects_analyzed: int
    risk_distribution: list[RiskDistributionItem]
    anomaly_breakdown: list[AnomalyTypeCount]
    top_risk_projects: list[ProjectSummary]
    generated_at: datetime
    data_notice: str
    scope: str | None = None


class QueueItem(BaseModel):
    priority: int
    project_id: str
    project_name: str | None = None
    risk_score: float
    risk_level: str
    primary_risk: str
    anomaly_count: int
    district: str | None = None
    implementing_agency: str | None = None
    sanctioned_cost: float | None = None
    status: str | None = None

    # State of the investigation case on this work, when one has been opened.
    case_id: str | None = None
    case_status: str | None = None
    case_assigned_to: str | None = None
    case_outcome: str | None = None


class QueueResponse(BaseModel):
    total: int
    data_notice: str
    items: list[QueueItem]
    scope: str | None = None
    open_cases: int = 0
    permissions: dict[str, bool] = {}


class AgencyProfile(BaseModel):
    implementing_agency: str
    district_list: list[str]
    project_count: int
    high_risk_count: int
    critical_count: int
    average_risk_score: float
    total_anomalies: int
    total_sanctioned_cost: float
    total_expenditure: float
    highest_risk_project: str | None = None
    highest_risk_score: float


class AgencyListResponse(BaseModel):
    total: int
    data_notice: str
    agencies: list[AgencyProfile]
    scope: str | None = None
    notice: str | None = None


class SimilarProject(BaseModel):
    project_id: str
    project_name: str | None = None
    similarity: float
    similarity_pct: float
    distance_km: float | None = None
    same_village: bool
    village: str | None = None
    district: str | None = None
    implementing_agency: str | None = None
    sanctioned_cost: float | None = None
    sanction_date: date | None = None
    shared_terms: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None


class SimilarResponse(BaseModel):
    project_id: str
    threshold: float
    data_notice: str
    disclaimer: str
    matches: list[SimilarProject]


class AnomalyListResponse(BaseModel):
    project_id: str
    risk_score: float
    risk_level: str
    anomaly_count: int
    anomalies: list[dict[str, Any]]
    disclaimer: str


class VerificationRequest(BaseModel):
    """Signal families the reviewing officer has checked and found explained."""

    cleared: list[str] = Field(default_factory=list)


class VerificationResponse(BaseModel):
    """Provisional recomputed score. Not persisted, not a determination."""

    project_id: str
    original_risk_score: float
    original_risk_level: str
    adjusted_risk_score: float
    adjusted_risk_level: str
    adjusted_raw_total: float
    was_clamped: bool
    points_withheld: float
    cleared_types: list[str]
    ignored_types: list[str]
    breakdown: list[dict[str, Any]]
    band_changed: bool
    note: str
    disclaimer: str


class HealthResponse(BaseModel):
    status: str
    database: str
    projects_in_database: int
    engine: str
    data_notice: str


# --------------------------------------------------------------------------
# Investigation cases
#
# Request bodies are strictly typed because they are the only place user input
# enters the system. The case responses are passed through as mappings, for the
# same reason the analysis payload is: their shape is owned by
# ``services.case_service`` and re-declaring it here would mean two definitions
# to keep in step.
# --------------------------------------------------------------------------


class CaseCreateRequest(BaseModel):
    project_id: str
    assign_to: str | None = None
    remark: str | None = None


class CaseAssignRequest(BaseModel):
    assign_to: str


class CaseStatusRequest(BaseModel):
    status: str
    remark: str | None = None


class CaseOutcomeRequest(BaseModel):
    """The officer's conclusion. Selected by a person, never derived."""

    outcome: str
    remark: str | None = None


class CaseRemarkRequest(BaseModel):
    remark: str
    reference: str | None = None


class VerificationItemRequest(BaseModel):
    completed: bool | None = None
    remark: str | None = None
    evidence_ref: str | None = None
