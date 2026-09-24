"""
Analysis service — the bridge between storage and the anomaly engine.

The routers stay thin: they parse query parameters and hand off to the
functions here. Everything that decides *what a number means* lives either in
this module or, for the analytical work itself, in ``anomaly_engine``.

Why the whole corpus is re-analysed on every request
----------------------------------------------------
Duplicate detection is inherently a corpus-level operation — a work can only be
"potentially overlapping" relative to the other works — so a single-project
analysis still needs the full TF-IDF index. Analysing all ~26 records takes
about 3 ms, so there is no cache here on purpose. Nothing can go stale, and the
claim that risk scores are computed rather than stored stays literally true.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from anomaly_engine import analyze_project, build_similarity_index, find_similar_projects
from anomaly_engine.config import WEIGHTS
from anomaly_engine.risk_engine import ANOMALY_TITLES

from ..models import Project

DATA_NOTICE = (
    "Prototype / Synthetic Demonstration Data. This system does not use or "
    "represent official government records."
)

# Colour is bound to meaning, not to fashion: one colour per risk band, used
# identically everywhere in the interface.
BAND_COLORS = {
    "LOW": "#15803d",       # green
    "MEDIUM": "#b45309",    # amber
    "HIGH": "#c2410c",      # orange
    "CRITICAL": "#b91c1c",  # red
}


def load_projects(db: Session) -> list[Project]:
    stmt = select(Project).order_by(Project.project_id)
    return list(db.scalars(stmt).all())


def load_project(db: Session, project_id: str) -> Project | None:
    stmt = (
        select(Project)
        .options(selectinload(Project.payments))
        .where(Project.project_id == project_id)
    )
    return db.scalars(stmt).first()


def build_context(db: Session, as_of: date | None = None) -> dict:
    """Analyse every stored work once.

    Returns the raw records, the TF-IDF index and the per-project analyses, so a
    caller can serve a list, a chart or a single detail view from one pass.
    """
    rows = load_projects(db)
    records = [row.as_dict() for row in rows]
    index = build_similarity_index(records)
    analyses = {
        record["project_id"]: analyze_project(record, index, as_of=as_of)
        for record in records
    }
    return {"rows": rows, "records": records, "index": index, "analyses": analyses}


def summarise(row: Project, analysis: dict) -> dict:
    """Flatten one work plus its analysis into the shape the tables consume."""
    data = row.as_dict()
    data.update(
        {
            "risk_score": analysis["risk_score"],
            "risk_level": analysis["risk_level"],
            "anomaly_count": analysis["anomaly_count"],
            "primary_risk": analysis["primary_risk"],
            "anomaly_types": [a["type"] for a in analysis["anomalies"]],
        }
    )
    return data


def project_summaries(context: dict) -> list[dict]:
    return [summarise(row, context["analyses"][row.project_id]) for row in context["rows"]]


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard_stats(context: dict, top_n: int = 5) -> dict:
    summaries = project_summaries(context)
    analyses = context["analyses"].values()

    total_anomalies = sum(a["anomaly_count"] for a in analyses)
    scores = [s["risk_score"] for s in summaries]

    distribution = []
    for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        distribution.append(
            {
                "level": level,
                "count": sum(1 for s in summaries if s["risk_level"] == level),
                "color": BAND_COLORS[level],
            }
        )

    counts: dict[str, int] = {code: 0 for code in WEIGHTS}
    for analysis in analyses:
        for anomaly in analysis["anomalies"]:
            counts[anomaly["type"]] = counts.get(anomaly["type"], 0) + 1

    breakdown = [
        {"type": code, "title": ANOMALY_TITLES.get(code, code), "count": count}
        for code, count in counts.items()
    ]

    ranked = sorted(summaries, key=lambda s: (-s["risk_score"], s["project_id"]))

    return {
        "total_projects": len(summaries),
        "high_risk_projects": sum(1 for s in summaries if s["risk_level"] in ("HIGH", "CRITICAL")),
        "critical_projects": sum(1 for s in summaries if s["risk_level"] == "CRITICAL"),
        "total_anomalies": total_anomalies,
        "total_sanctioned_cost": sum(s.get("sanctioned_cost") or 0 for s in summaries),
        "total_expenditure": sum(s.get("actual_expenditure") or 0 for s in summaries),
        "average_risk_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "projects_analyzed": len(summaries),
        "risk_distribution": distribution,
        "anomaly_breakdown": breakdown,
        "top_risk_projects": ranked[:top_n],
        "data_notice": DATA_NOTICE,
    }


# --------------------------------------------------------------------------- #
# Investigation queue
# --------------------------------------------------------------------------- #
def investigation_queue(context: dict, min_score: float = 1.0) -> list[dict]:
    """Works ordered by risk, highest first — the officer's worklist.

    Works with no signal at all are excluded: an empty verification task is not
    worth an officer's time.
    """
    summaries = [s for s in project_summaries(context) if s["risk_score"] >= min_score]
    summaries.sort(key=lambda s: (-s["risk_score"], s["project_id"]))

    return [
        {
            "priority": i + 1,
            "project_id": s["project_id"],
            "project_name": s["project_name"],
            "risk_score": s["risk_score"],
            "risk_level": s["risk_level"],
            "primary_risk": s["primary_risk"],
            "anomaly_count": s["anomaly_count"],
            "district": s["district"],
            "implementing_agency": s["implementing_agency"],
            "sanctioned_cost": s["sanctioned_cost"],
            "status": s["status"],
        }
        for i, s in enumerate(summaries)
    ]


# --------------------------------------------------------------------------- #
# Agency profiles
# --------------------------------------------------------------------------- #
def agency_profiles(context: dict) -> list[dict]:
    """Aggregate risk by implementing agency.

    This is arithmetic over the per-project scores, not a separate model. An
    agency's average is a description of its recorded works, and with a handful
    of works each it should be read as a prompt to look, not as a judgement
    about the agency.
    """
    buckets: dict[str, list[dict]] = {}
    for summary in project_summaries(context):
        agency = summary.get("implementing_agency") or "Not recorded"
        buckets.setdefault(agency, []).append(summary)

    profiles = []
    for agency, items in buckets.items():
        top = max(items, key=lambda s: s["risk_score"])
        scores = [s["risk_score"] for s in items]
        profiles.append(
            {
                "implementing_agency": agency,
                "district_list": sorted({s["district"] for s in items if s.get("district")}),
                "project_count": len(items),
                "high_risk_count": sum(1 for s in items if s["risk_level"] in ("HIGH", "CRITICAL")),
                "critical_count": sum(1 for s in items if s["risk_level"] == "CRITICAL"),
                "average_risk_score": round(sum(scores) / len(scores), 1),
                "total_anomalies": sum(s["anomaly_count"] for s in items),
                "total_sanctioned_cost": sum(s.get("sanctioned_cost") or 0 for s in items),
                "total_expenditure": sum(s.get("actual_expenditure") or 0 for s in items),
                "highest_risk_project": top["project_id"],
                "highest_risk_score": top["risk_score"],
            }
        )

    profiles.sort(key=lambda p: (-p["average_risk_score"], p["implementing_agency"]))
    return profiles


# --------------------------------------------------------------------------- #
# Similar works
# --------------------------------------------------------------------------- #
def similar_projects(context: dict, project_id: str, limit: int = 5) -> list[dict]:
    return find_similar_projects(context["index"], project_id, limit=limit)


def nearby_projects(context: dict, project_id: str, radius_km: float = 25.0, limit: int = 6) -> list[dict]:
    """Other works within a radius — the lightweight geographic view.

    Deliberately a distance calculation rather than a mapping stack: it answers
    "what else was sanctioned around here?" without a tile server.
    """
    from anomaly_engine.text_similarity import haversine_km

    origin = next((r for r in context["records"] if r["project_id"] == project_id), None)
    if not origin or origin.get("latitude") is None or origin.get("longitude") is None:
        return []

    out = []
    for record in context["records"]:
        if record["project_id"] == project_id:
            continue
        if record.get("latitude") is None or record.get("longitude") is None:
            continue
        distance = haversine_km(
            origin["latitude"], origin["longitude"], record["latitude"], record["longitude"]
        )
        if distance is None or distance > radius_km:
            continue
        analysis = context["analyses"][record["project_id"]]
        out.append(
            {
                "project_id": record["project_id"],
                "project_name": record["project_name"],
                "village": record.get("village"),
                "district": record.get("district"),
                "work_type": record.get("work_type"),
                "sanctioned_cost": record.get("sanctioned_cost"),
                "latitude": record["latitude"],
                "longitude": record["longitude"],
                "distance_km": round(distance, 2),
                "risk_score": analysis["risk_score"],
                "risk_level": analysis["risk_level"],
            }
        )

    out.sort(key=lambda p: p["distance_km"])
    return out[:limit]
