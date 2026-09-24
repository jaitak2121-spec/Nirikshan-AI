"""End-to-end acceptance check against the specification's test checklist.

Drives the FastAPI application through ``tools.asgi_client`` rather than over a
socket, so the whole surface can be exercised without a listening port. Every
assertion here corresponds to a line in the specification's testing checklist or
to the legal-language rule, and each one prints a PASS/FAIL line so a failure is
attributable rather than just a stack trace.

Run:  .venv/bin/python -m tools.acceptance_test
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app  # noqa: E402
from tools.asgi_client import Client  # noqa: E402

HERO = "MPLAD-2026-024"
ROOT = Path(__file__).resolve().parents[1]

_checks = 0
_failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    global _checks
    _checks += 1
    if condition:
        print(f"  PASS  {label}" + (f"  ({detail})" if detail else ""))
        return True
    _failures.append(label + (f" — {detail}" if detail else ""))
    print(f"  FAIL  {label}" + (f"  ({detail})" if detail else ""))
    return False


def section(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


# --------------------------------------------------------------------------
# Language rule: the system must never assert fraud as a fact.
# --------------------------------------------------------------------------
# Words that would state wrongdoing as established fact. "fraud" is checked
# separately because legitimate hedged uses exist ("no finding of fraud").
BANNED = [
    r"\bis fraudulent\b",
    r"\bis corrupt\b",
    r"\bconfirmed fraud\b",
    r"\bproven fraud\b",
    r"\bfraud detected\b",
    r"\bfraudulent project\b",
    r"\bembezzl",
    r"\bguilty\b",
    r"\bcriminal\b",
    r"\bmisappropriated funds\b",
]


def scan_source_language() -> None:
    section("Legal / language rule — source scan")
    targets = [
        *(ROOT / "anomaly_engine").glob("*.py"),
        *(ROOT / "backend").rglob("*.py"),
        *(ROOT / "frontend" / "src").rglob("*.jsx"),
        *(ROOT / "frontend" / "src").rglob("*.js"),
    ]
    hits: list[str] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for pattern in BANNED:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                line_no = text[: match.start()].count("\n") + 1
                hits.append(f"{path.relative_to(ROOT)}:{line_no} '{match.group(0)}'")
    check(
        "no unhedged accusatory language in source",
        not hits,
        "; ".join(hits[:5]) if hits else f"{len(targets)} files scanned",
    )


def scan_payload_language(payload: object) -> None:
    """Walk every string in an API response looking for banned phrasing."""
    strings: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, str):
            strings.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    hits = [
        f"'{m.group(0)}' in {s[:60]!r}"
        for s in strings
        for p in BANNED
        for m in [re.search(p, s, re.IGNORECASE)]
        if m
    ]
    check(
        "no accusatory language in hero analysis payload",
        not hits,
        "; ".join(hits[:3]) if hits else f"{len(strings)} strings checked",
    )


def main() -> int:
    client = Client(app)
    client.startup()

    # ------------------------------------------------------------------
    section("Backend reachability and seeding")
    r = client.get("/api/health")
    check("GET /api/health returns 200", r.status == 200, f"status={r.status}")
    health = r.json()
    check("health reports ok", health.get("status") == "ok", str(health.get("status")))
    check(
        "database seeded with projects",
        health.get("projects_in_database", 0) >= 20,
        f"{health.get('projects_in_database')} projects",
    )
    check("data notice present on health", "Synthetic" in health.get("data_notice", ""))

    # ------------------------------------------------------------------
    section("Dashboard loads with populated statistics")
    r = client.get("/api/dashboard/stats")
    check("GET /api/dashboard/stats returns 200", r.status == 200, f"status={r.status}")
    stats = r.json()
    check("total projects > 0", stats["total_projects"] > 0, str(stats["total_projects"]))
    check("total anomalies > 0", stats["total_anomalies"] > 0, str(stats["total_anomalies"]))
    dist = {d["level"]: d["count"] for d in stats["risk_distribution"]}
    check(
        "risk distribution covers all four bands",
        set(dist) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
        str(dist),
    )
    check("at least one CRITICAL work", dist.get("CRITICAL", 0) >= 1, f"critical={dist.get('CRITICAL')}")
    check("at least one HIGH work", dist.get("HIGH", 0) >= 1, f"high={dist.get('HIGH')}")
    check(
        "distribution sums to total projects",
        sum(dist.values()) == stats["total_projects"],
        f"{sum(dist.values())} vs {stats['total_projects']}",
    )
    check(
        "anomaly type breakdown non-empty",
        len(stats["anomaly_breakdown"]) > 0,
        f"{len(stats['anomaly_breakdown'])} families",
    )
    check(
        "all five detector families appear in the corpus",
        {b["type"] for b in stats["anomaly_breakdown"]}
        == {"COST_ANOMALY", "PROGRESS_MISMATCH", "DELAY_RISK", "POTENTIAL_DUPLICATE", "DATA_QUALITY"},
        str(sorted(b["type"] for b in stats["anomaly_breakdown"])),
    )
    check(
        "headline counts agree with the distribution",
        stats["critical_projects"] == dist["CRITICAL"]
        and stats["high_risk_projects"] == dist["HIGH"] + dist["CRITICAL"],
        f"high={stats['high_risk_projects']} critical={stats['critical_projects']}",
    )
    check("top risk list is populated", len(stats["top_risk_projects"]) > 0)
    check(
        "hero leads the top risk list",
        stats["top_risk_projects"][0]["project_id"] == HERO,
        stats["top_risk_projects"][0]["project_id"],
    )

    # ------------------------------------------------------------------
    section("Project list, search and risk filter")
    r = client.get("/api/projects")
    check("GET /api/projects returns 200", r.status == 200, f"status={r.status}")
    listing = r.json()
    total = listing["total"]
    check("project list non-empty", total >= 20, f"{total} projects")
    check(
        "every row carries a computed risk score and level",
        all(
            isinstance(p["risk_score"], (int, float)) and p["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            for p in listing["projects"]
        ),
    )
    check(
        "default sort is risk descending",
        [p["risk_score"] for p in listing["projects"]]
        == sorted((p["risk_score"] for p in listing["projects"]), reverse=True),
    )

    r = client.get("/api/projects", params={"search": "Rampur"})
    hits = r.json()["projects"]
    check("search matches the hero work", any(p["project_id"] == HERO for p in hits), f"{len(hits)} hits")

    r = client.get("/api/projects", params={"search": "zzzznotathing"})
    check(
        "search with no matches returns an empty list, not an error",
        r.status == 200 and r.json()["matched"] == 0 and r.json()["projects"] == [],
        f"status={r.status} matched={r.json().get('matched')}",
    )

    for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        r = client.get("/api/projects", params={"risk_level": level})
        rows = r.json()["projects"]
        check(
            f"risk filter {level} returns only {level} rows",
            r.status == 200 and all(p["risk_level"] == level for p in rows),
            f"{len(rows)} rows",
        )

    r = client.get("/api/projects", params={"risk_level": "banana"})
    check("invalid risk filter is rejected cleanly", r.status == 422, f"status={r.status}")

    # ------------------------------------------------------------------
    section("Hero work: detail, analysis and explainability")
    r = client.get(f"/api/projects/{HERO}")
    check(f"GET /api/projects/{HERO} returns 200", r.status == 200, f"status={r.status}")
    detail = r.json()
    check("hero name matches the specification", "Community Hall" in detail["project_name"], detail["project_name"])
    check("hero has payment records", len(detail["payments"]) > 0, f"{len(detail['payments'])} payments")

    r = client.post(f"/api/projects/{HERO}/analyze")
    check("POST analyze returns 200", r.status == 200, f"status={r.status}")
    analysis = r.json()

    score = analysis["risk"]["risk_score"]
    level = analysis["risk"]["risk_level"]
    check("hero reaches HIGH or CRITICAL", level in {"HIGH", "CRITICAL"}, f"{score} {level}")
    check("hero score was not clamped", analysis["risk"]["was_clamped"] is False)

    anomalies = analysis["anomalies"]
    families = {a["type"] for a in anomalies}
    check("hero carries multiple anomaly families", len(families) >= 4, ", ".join(sorted(families)))
    for expected in ("COST_ANOMALY", "PROGRESS_MISMATCH", "DELAY_RISK", "POTENTIAL_DUPLICATE", "DATA_QUALITY"):
        check(f"hero raises {expected}", expected in families)

    # Score must be reconstructible from the published breakdown.
    breakdown = analysis["risk"]["breakdown"]
    reconstructed = sum(b["points"] for b in breakdown)
    check(
        "score equals the sum of its published contributions",
        abs(reconstructed - analysis["risk"]["raw_total"]) < 0.01,
        f"sum={reconstructed:.2f} raw={analysis['risk']['raw_total']:.2f}",
    )
    check(
        "every contribution equals weight x severity factor",
        all(
            abs(b["points"] - b["max_weight"] * b["severity_factor"]) < 0.01
            for b in breakdown
        ),
    )

    # Explainability: §9 requires all five elements on every signal.
    explanations = analysis["explanations"]
    check(
        "one explanation per detected anomaly",
        len(explanations) == len(anomalies),
        f"{len(explanations)} vs {len(anomalies)}",
    )
    missing = [
        f"{e['type']}.{f}"
        for e in explanations
        for f in ("what_happened", "actual_value", "expected_value", "difference", "why_it_matters")
        if not e.get(f)
    ]
    check("every explanation carries all five §9 elements", not missing, "; ".join(missing[:4]))
    check(
        "explanations are ordered by contribution, largest first",
        [e["points_contributed"] for e in explanations]
        == sorted((e["points_contributed"] for e in explanations), reverse=True),
    )
    check(
        "every explanation states its own scoring contribution",
        all(e.get("scoring_note") for e in explanations),
    )

    check(
        "every anomaly carries a severity band",
        all(a["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} for a in anomalies),
    )
    check(
        "every anomaly carries evidence rows",
        all(len(a.get("evidence", [])) > 0 for a in anomalies),
    )
    check(
        "every anomaly carries a recommended action",
        all(a.get("recommended_actions") for a in anomalies),
    )
    check(
        "every explanation carries recommended actions for its own signal",
        all(e.get("recommended_actions") for e in explanations),
    )
    check(
        "priority verification is recommended for the hero",
        "Priority verification recommended" in analysis["recommendation"]["headline"],
        analysis["recommendation"]["headline"],
    )
    check(
        "recommendation includes a verification checklist",
        len(analysis["recommendation"]["checklist"]) >= 3,
        f"{len(analysis['recommendation']['checklist'])} items",
    )
    check(
        "lineage chain is published",
        len(analysis["lineage"]["stages"]) >= 5,
        " -> ".join(s["stage"] for s in analysis["lineage"]["stages"]),
    )
    check(
        "lineage names the source as synthetic",
        "Synthetic" in analysis["lineage"]["source"],
        analysis["lineage"]["source"],
    )
    check("analysis carries the data notice", "Synthetic" in analysis["data_notice"])
    check(
        "analysis states the decision rests with the officer",
        "officer" in analysis["disclaimer"].lower(),
        analysis["disclaimer"][:60],
    )
    scan_payload_language(analysis)

    # Determinism — the spec forbids randomness anywhere in scoring.
    second = client.post(f"/api/projects/{HERO}/analyze").json()
    check(
        "repeated analysis is identical (no randomness)",
        second["risk"]["risk_score"] == score and len(second["anomalies"]) == len(anomalies),
        f"{second['risk']['risk_score']} vs {score}",
    )

    # ------------------------------------------------------------------
    section("Duplicate / overlap detection")
    r = client.get(f"/api/projects/{HERO}/similar")
    check("GET similar returns 200", r.status == 200, f"status={r.status}")
    similar = r.json()["matches"]
    check("hero has a comparable nearby work", len(similar) >= 1, f"{len(similar)} matches")
    if similar:
        top = similar[0]
        check("comparable work reports a similarity score", 0 < top["similarity"] <= 1, str(top["similarity"]))
        check("comparable work reports a distance", top.get("distance_km") is not None, f"{top.get('distance_km')} km")
        check(
            "duplicate wording is a verification prompt, not an allegation",
            "verif" in str(r.json()).lower(),
        )

    r = client.get("/api/projects/MPLAD-2026-019/similar")
    check(
        "the seeded overlapping pair is detected symmetrically",
        r.status == 200 and any(s["project_id"] == "MPLAD-2026-020" for s in r.json()["matches"]),
    )

    # ------------------------------------------------------------------
    section("Whole-corpus behaviour")
    scores: dict[str, float] = {}
    for project in listing["projects"]:
        pid = project["project_id"]
        a = client.post(f"/api/projects/{pid}/analyze")
        if a.status != 200:
            check(f"analyze {pid}", False, f"status={a.status}")
            continue
        body = a.json()
        scores[pid] = body["risk"]["risk_score"]
        ok = (
            0 <= body["risk"]["risk_score"] <= 100
            and body["risk"]["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        )
        if not ok:
            check(f"analyze {pid} within bounds", False, str(body["risk"]))

    check(
        "every project in the corpus analyses without error",
        len(scores) == total,
        f"{len(scores)}/{total}",
    )
    check(
        "list scores agree with per-project analysis",
        all(abs(p["risk_score"] - scores[p["project_id"]]) < 0.01 for p in listing["projects"]),
    )
    check(
        "hero is the highest-scoring work in the corpus",
        max(scores, key=scores.get) == HERO,
        f"top={max(scores, key=scores.get)} ({max(scores.values())})",
    )
    check(
        "scores are spread, not uniform",
        len(set(round(v) for v in scores.values())) >= 5,
        f"{len(set(round(v) for v in scores.values()))} distinct values",
    )

    # A clean record should genuinely come out clean.
    clean = [pid for pid, s in scores.items() if s == 0]
    check("at least one work scores zero (no false positives everywhere)", len(clean) >= 1, f"{len(clean)} clean")

    # ------------------------------------------------------------------
    section("Data inconsistency handling (§6)")
    r = client.post("/api/projects/MPLAD-2026-017/analyze")
    check("work with bad fields still analyses", r.status == 200, f"status={r.status}")
    bad = r.json()
    issues = bad["validation"]["issues"]
    check("validation reports issues on the malformed record", len(issues) > 0, f"{len(issues)} issues")
    check(
        "validation issues carry the structured shape",
        all({"type", "severity", "field", "reason"} <= set(i) for i in issues),
    )
    fields = {i["field"] for i in issues}
    check("out-of-range progress is caught", "physical_progress" in fields, str(sorted(fields)))
    check(
        "missing fields are caught",
        any(i["type"] == "DATA_INCONSISTENCY" for i in issues),
    )
    check(
        "a record with nulls does not crash the engine",
        bad["risk"]["risk_score"] >= 0 and "DATA_QUALITY" in {a["type"] for a in bad["anomalies"]},
    )

    # ------------------------------------------------------------------
    section("Invalid input and error handling (§26)")
    r = client.get("/api/projects/NOPE-000")
    check("unknown project id returns 404", r.status == 404, f"status={r.status}")
    check("404 carries a readable message", "No project found" in r.json().get("detail", ""), r.json().get("detail", ""))

    r = client.post("/api/projects/NOPE-000/analyze")
    check("analyze on unknown id returns 404", r.status == 404, f"status={r.status}")

    r = client.get("/api/projects/NOPE-000/similar")
    check("similar on unknown id returns 404", r.status == 404, f"status={r.status}")

    r = client.get("/api/projects/NOPE-000/anomalies")
    check("anomalies on unknown id returns 404", r.status == 404, f"status={r.status}")

    r = client.get("/api/projects", params={"limit": "0"})
    check("out-of-range limit is rejected cleanly", r.status == 422, f"status={r.status}")

    # ------------------------------------------------------------------
    section("Remaining endpoints (§16, §21–23)")
    r = client.get("/api/investigation-queue")
    check("GET /api/investigation-queue returns 200", r.status == 200, f"status={r.status}")
    queue = r.json()["items"]
    check("queue is ordered risk descending", [q["risk_score"] for q in queue] == sorted((q["risk_score"] for q in queue), reverse=True))
    check("queue priorities are 1..n", [q["priority"] for q in queue] == list(range(1, len(queue) + 1)))
    check("hero is first in the queue", queue and queue[0]["project_id"] == HERO, queue[0]["project_id"] if queue else "empty")
    check("every queue row names a main risk driver", all(q["primary_risk"] for q in queue))

    r = client.get("/api/agencies")
    check("GET /api/agencies returns 200", r.status == 200, f"status={r.status}")
    agencies = r.json()["agencies"]
    check("agency profiles are non-empty", len(agencies) > 0, f"{len(agencies)} agencies")
    check(
        "agency work counts sum to the corpus",
        sum(a["project_count"] for a in agencies) == total,
        f"{sum(a['project_count'] for a in agencies)} vs {total}",
    )

    r = client.get(f"/api/projects/{HERO}/anomalies")
    check("GET anomalies returns 200", r.status == 200, f"status={r.status}")
    check("anomalies endpoint agrees with analyze", len(r.json()["anomalies"]) == len(anomalies))

    r = client.get(f"/api/projects/{HERO}/nearby")
    check("GET nearby returns 200", r.status == 200, f"status={r.status}")

    r = client.get("/api/methodology")
    check("GET /api/methodology returns 200", r.status == 200, f"status={r.status}")
    method = r.json()
    check(
        "published weights match the specification",
        method["weights"] == {
            "COST_ANOMALY": 25,
            "PROGRESS_MISMATCH": 25,
            "DELAY_RISK": 20,
            "POTENTIAL_DUPLICATE": 20,
            "DATA_QUALITY": 10,
        },
        str(method["weights"]),
    )
    check(
        "published bands match the specification",
        [(b["level"], b["min"], b["max"]) for b in method["bands"]]
        == [("LOW", 0, 24), ("MEDIUM", 25, 49), ("HIGH", 50, 74), ("CRITICAL", 75, 100)],
        str(method["bands"]),
    )

    r = client.get("/api")
    check("GET /api index returns 200", r.status == 200, f"status={r.status}")

    # ------------------------------------------------------------------
    scan_source_language()

    section("Result")
    print(f"  {_checks - len(_failures)}/{_checks} checks passed")
    if _failures:
        print("\n  Failures:")
        for f in _failures:
            print(f"    - {f}")
        return 1
    print("  All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
