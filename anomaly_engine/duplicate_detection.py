"""
Potential duplicate / overlapping work detection.

Two independent signals must agree before a pair is flagged:

  1. Textual   — TF-IDF cosine similarity over the work's name, description and
                 work type. Location words are deliberately excluded from the
                 text so that "every project in Jaipur" does not look similar.
  2. Spatial   — the works must be co-located: same village, or within
                 ``DUPLICATE_DISTANCE_KM`` by Haversine distance.

Language note: a match here is never described as fraud or as a confirmed
duplicate. It is a *potential* overlap that a human officer must verify — two
genuinely different works can legitimately sit in the same village with similar
names, and the system has no authority to conclude otherwise.
"""

from __future__ import annotations

import numpy as np

from . import config as C
from .formatting import human_date, rupees
from .text_similarity import (
    build_tfidf_matrix,
    cosine_similarity_matrix,
    haversine_km,
    shared_terms,
)


def _document(project: dict) -> str:
    """The text compared across projects. Location is intentionally omitted."""
    parts = [
        project.get("project_name") or "",
        project.get("description") or "",
        project.get("work_type") or "",
    ]
    return " ".join(parts)


def _same_village(a: dict, b: dict) -> bool:
    va = (a.get("village") or "").strip().lower()
    vb = (b.get("village") or "").strip().lower()
    return bool(va) and va == vb


def build_similarity_index(projects: list[dict]) -> dict:
    """Vectorise the whole corpus once so pairwise lookups are cheap."""
    documents = [_document(p) for p in projects]
    matrix, vocab = build_tfidf_matrix(documents)
    sim = cosine_similarity_matrix(matrix)
    np.fill_diagonal(sim, 0.0)
    return {
        "projects": projects,
        "matrix": matrix,
        "vocab": vocab,
        "similarity": sim,
        "index_by_id": {p["project_id"]: i for i, p in enumerate(projects)},
    }


def find_similar_projects(
    index: dict, project_id: str, limit: int = 5, include_weak: bool = True
) -> list[dict]:
    """All comparable works for one project, strongest match first."""
    i = index["index_by_id"].get(project_id)
    if i is None:
        return []

    projects = index["projects"]
    sim_row = index["similarity"][i]
    source = projects[i]

    matches = []
    for j, score in enumerate(sim_row):
        if j == i:
            continue
        other = projects[j]
        distance = haversine_km(
            source.get("latitude"),
            source.get("longitude"),
            other.get("latitude"),
            other.get("longitude"),
        )
        same_village = _same_village(source, other)
        co_located = same_village or (
            distance is not None and distance <= C.DUPLICATE_DISTANCE_KM
        )

        if score < C.DUPLICATE_REPORT_FLOOR:
            continue
        if not include_weak and not co_located:
            continue

        flagged = bool(score >= C.DUPLICATE_SIMILARITY_THRESHOLD and co_located)
        matches.append(
            {
                "project_id": other["project_id"],
                "project_name": other.get("project_name"),
                "village": other.get("village"),
                "district": other.get("district"),
                "work_type": other.get("work_type"),
                "implementing_agency": other.get("implementing_agency"),
                "sanctioned_cost": other.get("sanctioned_cost"),
                "sanction_date": (
                    str(other["sanction_date"]) if other.get("sanction_date") else None
                ),
                "status": other.get("status"),
                "latitude": other.get("latitude"),
                "longitude": other.get("longitude"),
                "similarity": round(float(score), 4),
                "similarity_pct": round(float(score) * 100, 1),
                "distance_km": distance,
                "same_village": same_village,
                "co_located": co_located,
                "flagged": flagged,
                "shared_terms": shared_terms(index["matrix"], index["vocab"], i, j),
            }
        )

    matches.sort(key=lambda m: (m["flagged"], m["similarity"]), reverse=True)
    return matches[:limit]


def detect_duplicate_anomaly(index: dict, project_id: str) -> tuple[dict | None, list[dict]]:
    """Return (anomaly or None, all comparable works) for one project."""
    matches = find_similar_projects(index, project_id, limit=5)
    flagged = [m for m in matches if m["flagged"]]
    if not flagged:
        return None, matches

    best = flagged[0]
    span = C.DUPLICATE_SIMILARITY_FULL - C.DUPLICATE_SIMILARITY_THRESHOLD
    factor = (best["similarity"] - C.DUPLICATE_SIMILARITY_THRESHOLD) / span
    if (
        best["distance_km"] is not None
        and best["distance_km"] <= C.DUPLICATE_CLOSE_DISTANCE_KM
    ):
        factor += C.DUPLICATE_CLOSE_BONUS

    if best["distance_km"] is not None:
        proximity = f"{best['distance_km']:.2f} km apart"
    elif best["same_village"]:
        proximity = "same village"
    else:
        proximity = "co-located"

    evidence = [
        _row("Comparable work", f"{best['project_id']} — {best['project_name']}", "bad"),
        _row("Text similarity", f"{best['similarity_pct']:.0f}%", "bad", best["similarity_pct"]),
        _row(
            "Similarity threshold",
            f"{C.DUPLICATE_SIMILARITY_THRESHOLD * 100:.0f}%",
            "neutral",
            C.DUPLICATE_SIMILARITY_THRESHOLD * 100,
        ),
        _row("Geographic distance", proximity, "bad", best["distance_km"]),
        _row(
            "Distance threshold",
            f"{C.DUPLICATE_DISTANCE_KM:.0f} km",
            "neutral",
            C.DUPLICATE_DISTANCE_KM,
        ),
        _row("Village", best["village"] or "Not recorded", "neutral"),
        _row("Implementing agency", best["implementing_agency"] or "Not recorded", "neutral"),
        _row("Sanctioned cost of comparable work", rupees(best["sanctioned_cost"]), "neutral"),
        _row("Sanction date of comparable work", human_date(best["sanction_date"]), "neutral"),
    ]
    if best["shared_terms"]:
        evidence.append(
            _row("Shared descriptive terms", ", ".join(best["shared_terms"]), "warn")
        )

    factor = max(0.0, min(1.0, factor))
    weight = C.WEIGHTS["POTENTIAL_DUPLICATE"]
    anomaly = {
        "type": "POTENTIAL_DUPLICATE",
        "title": "Potential Duplicate / Overlapping Work",
        "severity": C.severity_from_factor(factor),
        "severity_factor": round(factor, 4),
        "weight": weight,
        "contribution": round(weight * factor, 2),
        "headline": (
            f"Potentially overlapping work detected: {best['similarity_pct']:.0f}% "
            f"textual similarity with {best['project_id']}, {proximity}."
        ),
        "reason": (
            "Two works with closely matching descriptions at the same location "
            "may represent duplicated sanction of the same asset — or may be "
            "genuinely distinct works with similar names. This is a verification "
            "trigger, not a finding: the scope and site of both works must be "
            "compared by an authorised officer before any conclusion is drawn."
        ),
        "actual_value": (
            f"{best['similarity_pct']:.0f}% textual similarity with "
            f"{best['project_id']}, {proximity}"
        ),
        "expected_value": (
            f"Below {C.DUPLICATE_SIMILARITY_THRESHOLD * 100:.0f}% similarity, "
            f"or further than {C.DUPLICATE_DISTANCE_KM:.0f} km from a similar work"
        ),
        "difference": (
            f"{best['similarity_pct'] - C.DUPLICATE_SIMILARITY_THRESHOLD * 100:.0f} "
            f"percentage points above the similarity threshold, at {proximity}"
        ),
        "evidence": evidence,
        "metrics": {
            "matched_project_id": best["project_id"],
            "matched_project_name": best["project_name"],
            "similarity": best["similarity"],
            "similarity_pct": best["similarity_pct"],
            "distance_km": best["distance_km"],
            "same_village": best["same_village"],
            "similarity_threshold_pct": C.DUPLICATE_SIMILARITY_THRESHOLD * 100,
            "distance_threshold_km": C.DUPLICATE_DISTANCE_KM,
            "shared_terms": best["shared_terms"],
            "all_flagged": flagged,
        },
    }
    return anomaly, matches


def _row(label: str, value: str, tone: str = "neutral", raw=None) -> dict:
    return {"label": label, "value": value, "tone": tone, "raw": raw}
