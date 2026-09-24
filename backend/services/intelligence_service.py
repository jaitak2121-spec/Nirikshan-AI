"""
Derived intelligence views.

Four aggregations over the same analysis context the rest of the API uses:
compliance, trend, early warning, and the relationship network. None of them
introduces a second model — every figure here is arithmetic over scores and
recorded fields that the existing engine already produced.

What this module deliberately does **not** do is as important as what it does:

* There is no time series of past risk scores, because the register holds one
  snapshot per work and no history. The trend view therefore groups works by
  **when they were sanctioned** and is labelled as such. It is not a claim that
  risk rose or fell over time.
* The early-warning view projects from recorded dates and progress figures by
  straight-line arithmetic. It is not a forecast, it has no accuracy figure, and
  nothing here has been validated against outcomes.
* The network shows recorded relationships — shared text, proximity, the same
  agency, the same district. It is not a learned graph model and a connection is
  not evidence of anything by itself.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from anomaly_engine import config as C
from anomaly_engine.risk_engine import ANOMALY_TITLES
from anomaly_engine.text_similarity import haversine_km

from .analysis_service import project_summaries

# --------------------------------------------------------------------------
# Compliance monitor
# --------------------------------------------------------------------------

#: A sanction taking longer than this after the recommendation is worth a look.
#: Chosen as roughly two months, which is above every gap in the current
#: register, so the check does not fire spuriously on the demonstration data.
SANCTION_LAG_WATCH_DAYS = 75
SANCTION_LAG_REVIEW_DAYS = 120

#: Completeness below these levels moves a record down a compliance grade.
COMPLETENESS_WATCH_PCT = 95.0
COMPLETENESS_REVIEW_PCT = 85.0

COMPLIANCE_NOTICE = (
    "These checks compare a record against the timelines and completeness the "
    "register itself implies. A 'requires review' grade means the record cannot "
    "be reconciled as it stands — it is a statement about the record, not a "
    "finding against any person or agency."
)


def _grade(results: list[dict[str, Any]]) -> str:
    if any(r["status"] == "REQUIRES REVIEW" for r in results):
        return "REQUIRES REVIEW"
    if any(r["status"] == "WATCH" for r in results):
        return "WATCH"
    return "COMPLIANT"


def _check(name: str, status: str, detail: str, basis: str) -> dict[str, Any]:
    return {"check": name, "status": status, "detail": detail, "basis": basis}


def compliance_for(record: dict[str, Any], analysis: dict[str, Any],
                   as_of: date | None = None) -> dict[str, Any]:
    """Run every compliance check against one work."""
    as_of = as_of or date.today()
    validation = analysis.get("validation", {})
    checks: list[dict[str, Any]] = []

    # 1. Sanction timeline ------------------------------------------------
    rec, sanc = record.get("recommendation_date"), record.get("sanction_date")
    if rec and sanc:
        lag = (sanc - rec).days
        if lag < 0:
            checks.append(_check(
                "Sanction timeline", "REQUIRES REVIEW",
                f"Sanctioned {abs(lag)} days before it was recommended.",
                "recommendation_date vs sanction_date",
            ))
        elif lag >= SANCTION_LAG_REVIEW_DAYS:
            checks.append(_check(
                "Sanction timeline", "REQUIRES REVIEW",
                f"{lag} days from recommendation to sanction.",
                f"threshold {SANCTION_LAG_REVIEW_DAYS} days",
            ))
        elif lag >= SANCTION_LAG_WATCH_DAYS:
            checks.append(_check(
                "Sanction timeline", "WATCH", f"{lag} days from recommendation to sanction.",
                f"threshold {SANCTION_LAG_WATCH_DAYS} days",
            ))
        else:
            checks.append(_check(
                "Sanction timeline", "COMPLIANT", f"Sanctioned {lag} days after recommendation.",
                "recommendation_date vs sanction_date",
            ))
    else:
        checks.append(_check(
            "Sanction timeline", "REQUIRES REVIEW",
            "Recommendation or sanction date is not recorded.",
            "recommendation_date, sanction_date",
        ))

    # 2. Completion timeline ----------------------------------------------
    expected = record.get("expected_completion_date")
    actual = record.get("actual_completion_date")
    if expected and actual:
        slip = (actual - expected).days
        if slip > 0:
            checks.append(_check(
                "Completion timeline", "WATCH",
                f"Completed {slip} days after the expected date.",
                "expected vs actual completion date",
            ))
        else:
            checks.append(_check(
                "Completion timeline", "COMPLIANT",
                f"Completed {abs(slip)} days within the expected date.",
                "expected vs actual completion date",
            ))
    elif expected:
        overdue = (as_of - expected).days
        if overdue > 0:
            status = "REQUIRES REVIEW" if overdue >= C.OVERDUE_FULL_SEVERITY_DAYS else "WATCH"
            checks.append(_check(
                "Completion timeline", status,
                f"{overdue} days past the expected completion date and not recorded as complete.",
                f"expected_completion_date vs {as_of.isoformat()}",
            ))
        else:
            checks.append(_check(
                "Completion timeline", "COMPLIANT",
                f"{abs(overdue)} days remaining to the expected completion date.",
                f"expected_completion_date vs {as_of.isoformat()}",
            ))
    else:
        checks.append(_check(
            "Completion timeline", "REQUIRES REVIEW",
            "No expected completion date is recorded, so the work cannot be tracked against a schedule.",
            "expected_completion_date",
        ))

    # 3. Required information ---------------------------------------------
    missing = validation.get("missing_required", [])
    checks.append(_check(
        "Required information", "REQUIRES REVIEW" if missing else "COMPLIANT",
        f"Missing: {', '.join(missing)}." if missing else "All required fields are present.",
        "validation engine, required fields",
    ))

    # 4. Internal consistency of dates and values --------------------------
    inconsistent = [
        i for i in validation.get("issues", [])
        if i.get("severity") in ("HIGH", "CRITICAL") and i.get("code") not in ("MISSING_REQUIRED",)
    ]
    checks.append(_check(
        "Internal consistency", "REQUIRES REVIEW" if inconsistent else "COMPLIANT",
        (f"{len(inconsistent)} value(s) cannot be reconciled: "
         + "; ".join(i["reason"] for i in inconsistent[:2]))
        if inconsistent else "Dates and values are internally consistent.",
        "validation engine, consistency rules",
    ))

    # 5. Data completeness -------------------------------------------------
    completeness = validation.get("completeness_pct", 0.0)
    if completeness < COMPLETENESS_REVIEW_PCT:
        status = "REQUIRES REVIEW"
    elif completeness < COMPLETENESS_WATCH_PCT:
        status = "WATCH"
    else:
        status = "COMPLIANT"
    checks.append(_check(
        "Data completeness", status, f"{completeness}% of tracked fields are populated.",
        f"watch below {COMPLETENESS_WATCH_PCT}%, review below {COMPLETENESS_REVIEW_PCT}%",
    ))

    # 6. Expenditure against progress --------------------------------------
    phys, fin = record.get("physical_progress"), record.get("financial_progress")
    if phys is not None and fin is not None:
        gap = fin - phys
        if gap >= C.MISMATCH_FULL_PP:
            status, detail = "REQUIRES REVIEW", f"{gap:.0f}pp of funds drawn ahead of physical work."
        elif gap > C.MISMATCH_TOLERANCE_PP:
            status, detail = "WATCH", f"{gap:.0f}pp of funds drawn ahead of physical work."
        else:
            status, detail = "COMPLIANT", f"Financial and physical progress are within {abs(gap):.0f}pp."
        checks.append(_check(
            "Expenditure against progress", status, detail,
            f"tolerance {C.MISMATCH_TOLERANCE_PP}pp, full {C.MISMATCH_FULL_PP}pp",
        ))
    else:
        checks.append(_check(
            "Expenditure against progress", "REQUIRES REVIEW",
            "Physical or financial progress is not recorded.",
            "physical_progress, financial_progress",
        ))

    # 7. Supporting evidence available -------------------------------------
    payments = record.get("payment_count", 0)
    has_geo = record.get("latitude") is not None and record.get("longitude") is not None
    if payments and has_geo:
        status, detail = "COMPLIANT", f"{payments} payment record(s) and site coordinates on file."
    elif payments or has_geo:
        status = "WATCH"
        detail = (
            f"{payments} payment record(s) on file but no site coordinates."
            if payments else "Site coordinates on file but no payment records."
        )
    else:
        status, detail = "REQUIRES REVIEW", "Neither payment records nor site coordinates are on file."
    checks.append(_check(
        "Supporting evidence", status, detail, "payment records, site coordinates",
    ))

    return {
        "project_id": record["project_id"],
        "project_name": record.get("project_name"),
        "district": record.get("district"),
        "state": record.get("state"),
        "implementing_agency": record.get("implementing_agency"),
        "risk_score": analysis["risk_score"],
        "risk_level": analysis["risk_level"],
        "compliance_status": _grade(checks),
        "checks": checks,
        "review_count": sum(1 for c in checks if c["status"] == "REQUIRES REVIEW"),
        "watch_count": sum(1 for c in checks if c["status"] == "WATCH"),
    }


def compliance_report(context: dict, as_of: date | None = None) -> dict[str, Any]:
    """Compliance grades for every work in the context."""
    payment_counts = {r["project_id"]: 0 for r in context["records"]}
    for row in context["rows"]:
        payment_counts[row.project_id] = len(row.payments)

    reports = []
    for record in context["records"]:
        enriched = dict(record, payment_count=payment_counts.get(record["project_id"], 0))
        reports.append(compliance_for(enriched, context["analyses"][record["project_id"]], as_of))

    order = {"REQUIRES REVIEW": 0, "WATCH": 1, "COMPLIANT": 2}
    reports.sort(key=lambda r: (order[r["compliance_status"]], -r["risk_score"]))

    counts = {"COMPLIANT": 0, "WATCH": 0, "REQUIRES REVIEW": 0}
    for report in reports:
        counts[report["compliance_status"]] += 1

    # Which checks fail most often across the register — the systemic view.
    by_check: dict[str, dict[str, Any]] = {}
    for report in reports:
        for check in report["checks"]:
            bucket = by_check.setdefault(
                check["check"], {"check": check["check"], "compliant": 0, "watch": 0, "review": 0}
            )
            key = {"COMPLIANT": "compliant", "WATCH": "watch", "REQUIRES REVIEW": "review"}[check["status"]]
            bucket[key] += 1

    return {
        "total": len(reports),
        "counts": [{"status": s, "count": c} for s, c in counts.items()],
        "by_check": sorted(by_check.values(), key=lambda b: (-b["review"], -b["watch"])),
        "projects": reports,
        "notice": COMPLIANCE_NOTICE,
    }


# --------------------------------------------------------------------------
# Trend analysis
# --------------------------------------------------------------------------

TREND_NOTICE = (
    "The register holds one current snapshot per work and no history of past "
    "scores, so this is not a time series of risk rising or falling. Works are "
    "grouped by the quarter they were sanctioned in, and each group is scored "
    "as it stands today. Read it as: how do works sanctioned in each period "
    "look now. The counts are small and drawn from synthetic demonstration data."
)


def _quarter(value: date) -> str:
    return f"{value.year}-Q{(value.month - 1) // 3 + 1}"


def trend_analysis(context: dict) -> dict[str, Any]:
    """Risk composition of works grouped by sanction quarter."""
    buckets: dict[str, dict[str, Any]] = {}
    undated = 0

    for record in context["records"]:
        sanctioned = record.get("sanction_date")
        if not sanctioned:
            undated += 1
            continue
        analysis = context["analyses"][record["project_id"]]
        key = _quarter(sanctioned)
        bucket = buckets.setdefault(
            key,
            {
                "period": key,
                "projects": 0,
                "scores": [],
                "high_risk": 0,
                "critical": 0,
                "sanctioned_cost": 0.0,
                **{code: 0 for code in C.WEIGHTS},
            },
        )
        bucket["projects"] += 1
        bucket["scores"].append(analysis["risk_score"])
        if analysis["risk_level"] in ("HIGH", "CRITICAL"):
            bucket["high_risk"] += 1
        if analysis["risk_level"] == "CRITICAL":
            bucket["critical"] += 1
        bucket["sanctioned_cost"] += record.get("sanctioned_cost") or 0
        for anomaly in analysis["anomalies"]:
            bucket[anomaly["type"]] += 1

    series = []
    for key in sorted(buckets):
        bucket = buckets[key]
        scores = bucket.pop("scores")
        bucket["average_risk_score"] = round(sum(scores) / len(scores), 1)
        bucket["max_risk_score"] = max(scores)
        bucket["sanctioned_cost"] = round(bucket["sanctioned_cost"], 2)
        series.append(bucket)

    signal_totals = [
        {
            "type": code,
            "title": ANOMALY_TITLES.get(code, code),
            "count": sum(b[code] for b in series),
        }
        for code in C.WEIGHTS
    ]

    return {
        "series": series,
        "periods": len(series),
        "signal_series": [
            {"type": code, "title": ANOMALY_TITLES.get(code, code),
             "points": [{"period": b["period"], "count": b[code]} for b in series]}
            for code in C.WEIGHTS
        ],
        "signal_totals": sorted(signal_totals, key=lambda s: -s["count"]),
        "projects_without_sanction_date": undated,
        "notice": TREND_NOTICE,
        "basis": "sanction_date grouped by calendar quarter; scores recomputed at request time",
    }


# --------------------------------------------------------------------------
# Early warning / watchlist
# --------------------------------------------------------------------------

WATCHLIST_NOTICE = (
    "An early-warning entry is a work whose indicators are moving the wrong way "
    "but have not reached the level that raises a risk signal. Each indicator is "
    "straight-line arithmetic over the dates and progress figures on the record. "
    "It is not a forecast, it carries no accuracy figure, and no historical "
    "series of these works exists to validate it against."
)


def _schedule_position(record: dict[str, Any], as_of: date) -> float | None:
    """How far through its sanctioned schedule a work is, 0–1."""
    start = record.get("start_date") or record.get("sanction_date")
    end = record.get("expected_completion_date")
    if not start or not end or end <= start:
        return None
    return max(0.0, min(1.5, (as_of - start).days / (end - start).days))


def watchlist(context: dict, as_of: date | None = None) -> dict[str, Any]:
    """Works deteriorating but not yet flagged at full severity."""
    as_of = as_of or date.today()
    entries = []

    for record in context["records"]:
        analysis = context["analyses"][record["project_id"]]
        if record.get("status") == "Completed":
            continue

        indicators = []
        phys = record.get("physical_progress")
        fin = record.get("financial_progress")

        # 1. Progress gap opening up, below the level that raises a signal.
        if phys is not None and fin is not None:
            gap = fin - phys
            if 0 < gap <= C.MISMATCH_FULL_PP:
                severity = min(1.0, gap / C.MISMATCH_FULL_PP)
                indicators.append({
                    "indicator": "Progress gap",
                    "reading": f"{fin:.0f}% financial against {phys:.0f}% physical ({gap:.0f}pp apart)",
                    "threshold": f"a signal is raised above {C.MISMATCH_TOLERANCE_PP}pp",
                    "direction": "widening" if gap > C.MISMATCH_TOLERANCE_PP / 2 else "opening",
                    "severity": round(severity, 2),
                })

        # 2. Physical progress behind where the schedule says it should be.
        position = _schedule_position(record, as_of)
        if position is not None and phys is not None:
            expected_pct = position * 100
            deficit = expected_pct - phys
            if deficit > 0:
                severity = min(1.0, deficit / C.DELAY_DEFICIT_FULL_PP)
                indicators.append({
                    "indicator": "Schedule position",
                    "reading": (
                        f"{position * 100:.0f}% through the sanctioned schedule with "
                        f"{phys:.0f}% physical progress ({deficit:.0f}pp behind)"
                    ),
                    "threshold": f"a signal is raised above {C.DELAY_DEFICIT_TOLERANCE_PP}pp behind",
                    "direction": "falling behind",
                    "severity": round(severity, 2),
                })

        # 3. Expenditure approaching the sanctioned amount before the work is.
        sanctioned = record.get("sanctioned_cost")
        spent = record.get("actual_expenditure")
        if sanctioned and spent is not None and sanctioned > 0:
            burn = 100.0 * spent / sanctioned
            if phys is not None and burn > phys and burn <= 100 + C.COST_TOLERANCE_PCT:
                severity = min(1.0, (burn - phys) / 100.0)
                indicators.append({
                    "indicator": "Expenditure against completion",
                    "reading": (
                        f"{burn:.0f}% of the sanctioned amount drawn at "
                        f"{phys:.0f}% physical completion"
                    ),
                    "threshold": f"a cost signal is raised above {100 + C.COST_TOLERANCE_PCT:.0f}% of sanction",
                    "direction": "approaching the sanctioned limit",
                    "severity": round(severity, 2),
                })

        if not indicators:
            continue

        # A work already assessed CRITICAL is past early warning — it is on the
        # investigation queue, and repeating it here would be noise.
        if analysis["risk_level"] == "CRITICAL":
            continue

        pressure = round(sum(i["severity"] for i in indicators) / len(indicators), 2)
        entries.append({
            "project_id": record["project_id"],
            "project_name": record.get("project_name"),
            "district": record.get("district"),
            "state": record.get("state"),
            "implementing_agency": record.get("implementing_agency"),
            "status": record.get("status"),
            "risk_score": analysis["risk_score"],
            "risk_level": analysis["risk_level"],
            "indicators": indicators,
            "indicator_count": len(indicators),
            "pressure": pressure,
            "watch_level": "WATCH" if pressure >= 0.5 or len(indicators) >= 2 else "MONITOR",
        })

    entries.sort(key=lambda e: (-e["indicator_count"], -e["pressure"], -e["risk_score"]))
    return {
        "total": len(entries),
        "watch_count": sum(1 for e in entries if e["watch_level"] == "WATCH"),
        "monitor_count": sum(1 for e in entries if e["watch_level"] == "MONITOR"),
        "entries": entries,
        "as_of": as_of.isoformat(),
        "notice": WATCHLIST_NOTICE,
    }


# --------------------------------------------------------------------------
# Investigation network
# --------------------------------------------------------------------------

NETWORK_NOTICE = (
    "These are recorded relationships between works: shared description text, "
    "geographic proximity, the same implementing agency, the same district. "
    "Each edge states the measurement behind it. A connection between two works "
    "is a reason to compare them — it is not evidence of collusion, a network of "
    "wrongdoing, or any coordinated conduct, and nothing here is inferred by a "
    "learned graph model."
)

#: Edge types, with how strongly each is worth following. Ordered so the
#: strongest evidence of overlap sorts first.
EDGE_TYPES = {
    "TEXT_SIMILARITY": "Similar description",
    "GEOGRAPHIC_PROXIMITY": "Close together",
    "SAME_AGENCY": "Same implementing agency",
    "SAME_DISTRICT": "Same district",
}


def network_for(context: dict, project_id: str, *, radius_km: float = 25.0,
                max_neighbours: int = 12) -> dict[str, Any]:
    """The works related to one work, with the basis for each relationship."""
    records = {r["project_id"]: r for r in context["records"]}
    origin = records.get(project_id)
    if origin is None:
        return {"nodes": [], "edges": [], "notice": NETWORK_NOTICE}

    similarity = {
        m["project_id"]: m
        for m in context["index"]["matches"].get(project_id, [])
    } if "matches" in context["index"] else {}

    # The similarity index is consulted through the same helper the rest of the
    # API uses, so the figures match what the project page shows.
    from anomaly_engine.duplicate_detection import find_similar_projects

    for match in find_similar_projects(context["index"], project_id, limit=max_neighbours):
        similarity[match["project_id"]] = match

    edges: list[dict[str, Any]] = []
    neighbours: set[str] = set()

    def add_edge(other: str, edge_type: str, strength: float, basis: str) -> None:
        if other == project_id or other not in records:
            return
        edges.append({
            "source": project_id,
            "target": other,
            "type": edge_type,
            "label": EDGE_TYPES[edge_type],
            "strength": round(max(0.0, min(1.0, strength)), 3),
            "basis": basis,
        })
        neighbours.add(other)

    for other_id, match in similarity.items():
        add_edge(
            other_id, "TEXT_SIMILARITY", match["similarity"],
            f"{match['similarity_pct']:.0f}% term overlap in the recorded descriptions"
            + (f"; shared terms: {', '.join(match['shared_terms'][:4])}" if match.get("shared_terms") else ""),
        )

    if origin.get("latitude") is not None and origin.get("longitude") is not None:
        for other_id, other in records.items():
            if other_id == project_id:
                continue
            if other.get("latitude") is None or other.get("longitude") is None:
                continue
            distance = haversine_km(
                origin["latitude"], origin["longitude"], other["latitude"], other["longitude"]
            )
            if distance is None or distance > radius_km:
                continue
            add_edge(
                other_id, "GEOGRAPHIC_PROXIMITY", 1.0 - (distance / radius_km),
                f"{distance:.2f} km apart by straight-line distance",
            )

    agency = origin.get("implementing_agency")
    if agency:
        for other_id, other in records.items():
            if other_id != project_id and other.get("implementing_agency") == agency:
                add_edge(other_id, "SAME_AGENCY", 0.5, f"Both implemented by {agency}")

    district = origin.get("district")
    if district:
        for other_id, other in records.items():
            if other_id != project_id and other.get("district") == district:
                add_edge(other_id, "SAME_DISTRICT", 0.25, f"Both sanctioned in {district}")

    def node_for(pid: str, is_origin: bool) -> dict[str, Any]:
        record, analysis = records[pid], context["analyses"][pid]
        return {
            "project_id": pid,
            "project_name": record.get("project_name"),
            "district": record.get("district"),
            "state": record.get("state"),
            "village": record.get("village"),
            "implementing_agency": record.get("implementing_agency"),
            "work_type": record.get("work_type"),
            "sanctioned_cost": record.get("sanctioned_cost"),
            "risk_score": analysis["risk_score"],
            "risk_level": analysis["risk_level"],
            "anomaly_count": analysis["anomaly_count"],
            "is_origin": is_origin,
            "edge_count": sum(1 for e in edges if e["target"] == pid),
        }

    nodes = [node_for(project_id, True)] + [
        node_for(pid, False)
        for pid in sorted(
            neighbours,
            key=lambda p: -max(e["strength"] for e in edges if e["target"] == p),
        )
    ]

    order = list(EDGE_TYPES)
    edges.sort(key=lambda e: (order.index(e["type"]), -e["strength"]))

    return {
        "project_id": project_id,
        "nodes": nodes,
        "edges": edges,
        "edge_types": [
            {"type": t, "label": label,
             "count": sum(1 for e in edges if e["type"] == t)}
            for t, label in EDGE_TYPES.items()
        ],
        "neighbour_count": len(neighbours),
        "radius_km": radius_km,
        "notice": NETWORK_NOTICE,
    }


# --------------------------------------------------------------------------
# Agency drill-down
# --------------------------------------------------------------------------

AGENCY_NOTICE = (
    "These are descriptive summaries of a small number of records, not an "
    "assessment of any agency. A high mean risk score reflects the works "
    "currently on the register under this name and does not establish "
    "wrongdoing by the agency or by anyone in it."
)


def agency_detail(context: dict, agency: str, cases: list[dict] | None = None) -> dict[str, Any]:
    """One agency's works, signal mix, highest-risk items and open cases."""
    summaries = [
        s for s in project_summaries(context)
        if (s.get("implementing_agency") or "Not recorded") == agency
    ]
    if not summaries:
        return {}

    scores = [s["risk_score"] for s in summaries]
    signal_counts: dict[str, int] = {code: 0 for code in C.WEIGHTS}
    for summary in summaries:
        analysis = context["analyses"][summary["project_id"]]
        for anomaly in analysis["anomalies"]:
            signal_counts[anomaly["type"]] += 1

    ranked = sorted(summaries, key=lambda s: -s["risk_score"])
    project_ids = {s["project_id"] for s in summaries}
    related_case_list = [c for c in (cases or []) if c["project_id"] in project_ids]

    # Other agencies working the same districts — the comparison that stops a
    # single agency's average being read in isolation.
    districts = {s["district"] for s in summaries if s.get("district")}
    peers: dict[str, list[float]] = {}
    for summary in project_summaries(context):
        name = summary.get("implementing_agency") or "Not recorded"
        if name == agency or summary.get("district") not in districts:
            continue
        peers.setdefault(name, []).append(summary["risk_score"])

    return {
        "implementing_agency": agency,
        "project_count": len(summaries),
        "average_risk_score": round(sum(scores) / len(scores), 1),
        "max_risk_score": max(scores),
        "high_risk_count": sum(1 for s in summaries if s["risk_level"] in ("HIGH", "CRITICAL")),
        "critical_count": sum(1 for s in summaries if s["risk_level"] == "CRITICAL"),
        "total_anomalies": sum(s["anomaly_count"] for s in summaries),
        "total_sanctioned_cost": sum(s.get("sanctioned_cost") or 0 for s in summaries),
        "total_expenditure": sum(s.get("actual_expenditure") or 0 for s in summaries),
        "district_list": sorted(districts),
        "state_list": sorted({s["state"] for s in summaries if s.get("state")}),
        "signal_distribution": sorted(
            [
                {"type": code, "title": ANOMALY_TITLES.get(code, code), "count": count,
                 "share_pct": round(100.0 * count / len(summaries), 1)}
                for code, count in signal_counts.items()
            ],
            key=lambda s: -s["count"],
        ),
        "highest_risk_works": ranked[:8],
        "projects": ranked,
        "active_cases": [c for c in related_case_list if c["status"] != "CLOSED"],
        "all_cases": related_case_list,
        "peer_agencies": sorted(
            [
                {"implementing_agency": name, "project_count": len(vals),
                 "average_risk_score": round(sum(vals) / len(vals), 1)}
                for name, vals in peers.items()
            ],
            key=lambda p: -p["average_risk_score"],
        )[:6],
        "notice": AGENCY_NOTICE,
    }
