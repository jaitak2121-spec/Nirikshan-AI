"""
Data lineage.

Every number the investigation screen shows should be traceable back to where
it came from and what transformed it. For this prototype the origin is always a
synthetic record, and stating that explicitly on every project page is part of
the design — the system should never let a viewer mistake demonstration data
for official government records.
"""

from __future__ import annotations

SOURCE_LABEL = "Synthetic Demonstration Record"
DATASET_LABEL = "Synthetic MPLADS-style dataset (prototype)"


def lineage_for(project: dict, anomaly_count: int) -> dict:
    """The lineage trail for one analysed project."""
    return {
        "source": SOURCE_LABEL,
        "dataset": DATASET_LABEL,
        "is_synthetic": True,
        "record_id": project.get("project_id"),
        "stages": [
            {
                "stage": "Ingestion",
                "detail": f"{DATASET_LABEL}; record {project.get('project_id')}",
                "status": "complete",
            },
            {
                "stage": "Validation",
                "detail": "Field completeness, range and date-sequence checks",
                "status": "complete",
            },
            {
                "stage": "Feature Engineering",
                "detail": "Cost deviation, schedule deficit, progress gap, TF-IDF vector",
                "status": "complete",
            },
            {
                "stage": "Anomaly Engine",
                "detail": f"5 detector families evaluated; {anomaly_count} signal(s) raised",
                "status": "complete",
            },
            {
                "stage": "Risk Fusion",
                "detail": "Weighted additive combination, clamped to 0-100",
                "status": "complete",
            },
            {
                "stage": "Investigation",
                "detail": "Explanations, evidence and recommended actions generated",
                "status": "complete",
            },
        ],
    }
