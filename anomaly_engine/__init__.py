"""
NIRIKSHAN AI — anomaly and risk engine.

Pure analysis logic with no web-framework or database dependency: it takes
plain dictionaries and returns plain dictionaries. That separation is what lets
the same engine be unit-tested directly (see ``tests/test_engine.py``), driven
by the FastAPI layer, or pointed at a different data source later.
"""

from .config import RISK_BANDS, WEIGHTS, risk_level, severity_from_factor
from .duplicate_detection import (
    build_similarity_index,
    detect_duplicate_anomaly,
    find_similar_projects,
)
from .explanation_engine import DISCLAIMER, build_explanations, build_recommendation
from .lineage import lineage_for
from .pipeline import analyze_corpus, analyze_project
from .risk_engine import fuse, primary_risk_label
from .validation import validate_project

__all__ = [
    "analyze_project",
    "analyze_corpus",
    "validate_project",
    "build_similarity_index",
    "find_similar_projects",
    "detect_duplicate_anomaly",
    "build_explanations",
    "build_recommendation",
    "lineage_for",
    "fuse",
    "primary_risk_label",
    "risk_level",
    "severity_from_factor",
    "WEIGHTS",
    "RISK_BANDS",
    "DISCLAIMER",
]
