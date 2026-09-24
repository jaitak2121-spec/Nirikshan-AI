"""
Tunable constants for the NIRIKSHAN AI risk engine.

Everything the engine treats as a "threshold" lives here so that the numbers a
judge sees on screen can be traced back to one auditable place. No thresholds
are hidden inside detector code.
"""

# --------------------------------------------------------------------------
# Risk weights: the maximum number of points each anomaly family can add.
# These are the weights specified for the prototype's risk model.
# --------------------------------------------------------------------------
WEIGHTS = {
    "COST_ANOMALY": 25.0,
    "PROGRESS_MISMATCH": 25.0,
    "DELAY_RISK": 20.0,
    "POTENTIAL_DUPLICATE": 20.0,
    "DATA_QUALITY": 10.0,
}

MAX_RISK_SCORE = 100.0

# --------------------------------------------------------------------------
# Risk bands
# --------------------------------------------------------------------------
RISK_BANDS = [
    (0, 24, "LOW"),
    (25, 49, "MEDIUM"),
    (50, 74, "HIGH"),
    (75, 100, "CRITICAL"),
]

# --------------------------------------------------------------------------
# A. Cost anomaly
# --------------------------------------------------------------------------
# Expenditure up to this % above the sanctioned amount is treated as normal
# variation (rate revisions, rounding) and is not flagged.
COST_TOLERANCE_PCT = 5.0
# A cost overrun of this size or more attracts the full cost weight.
COST_FULL_SEVERITY_PCT = 30.0

# --------------------------------------------------------------------------
# B. Delay risk
# --------------------------------------------------------------------------
# A project may lag its straight-line schedule by this many percentage points
# before it is considered behind schedule.
DELAY_DEFICIT_TOLERANCE_PP = 15.0
# A schedule deficit of this size attracts the full delay weight.
DELAY_DEFICIT_FULL_PP = 50.0
# Days past the expected completion date that attract the full delay weight.
OVERDUE_FULL_SEVERITY_DAYS = 180
# Base severity applied the moment a project becomes overdue.
OVERDUE_BASE_FACTOR = 0.5
# Window in which a project counts as "approaching" its completion date.
DEADLINE_HORIZON_DAYS = 90

# --------------------------------------------------------------------------
# C. Financial vs physical progress mismatch
# --------------------------------------------------------------------------
# Financial progress may legitimately run ahead of physical progress by this
# much (advances, mobilisation payments, material procurement).
MISMATCH_TOLERANCE_PP = 10.0
# A gap of this size attracts the full mismatch weight.
MISMATCH_FULL_PP = 40.0

# --------------------------------------------------------------------------
# D. Potential duplicate / overlapping work
# --------------------------------------------------------------------------
# Minimum TF-IDF cosine similarity for two works to be considered comparable.
DUPLICATE_SIMILARITY_THRESHOLD = 0.62
# Similarity at which the duplicate signal reaches full weight.
DUPLICATE_SIMILARITY_FULL = 0.90
# Two works must also be co-located: same village, or within this distance.
DUPLICATE_DISTANCE_KM = 3.0
# Works closer than this get an extra severity nudge.
DUPLICATE_CLOSE_DISTANCE_KM = 0.5
DUPLICATE_CLOSE_BONUS = 0.15
# Similarity below this is not even reported as a weak match.
DUPLICATE_REPORT_FLOOR = 0.45

# --------------------------------------------------------------------------
# E. Data quality
# --------------------------------------------------------------------------
# Penalty points contributed by a validation issue of each severity.
VALIDATION_PENALTY = {
    "CRITICAL": 20,
    "HIGH": 12,
    "MEDIUM": 6,
    "LOW": 3,
}
# Total validation penalty that attracts the full data-quality weight.
DATA_QUALITY_FULL_PENALTY = 40.0

# Fields that must be present for a record to be considered complete.
REQUIRED_FIELDS = [
    "project_name",
    "district",
    "implementing_agency",
    "sanctioned_cost",
    "sanction_date",
    "expected_completion_date",
    "physical_progress",
    "financial_progress",
    "status",
]

# Fields that are expected but whose absence is a softer signal.
RECOMMENDED_FIELDS = [
    "description",
    "village",
    "constituency",
    "work_type",
    "sector",
    "estimated_cost",
    "start_date",
    "recommendation_date",
    "latitude",
    "longitude",
]


def severity_from_factor(factor: float) -> str:
    """Map a 0..1 severity factor onto the shared severity vocabulary."""
    if factor >= 0.80:
        return "CRITICAL"
    if factor >= 0.50:
        return "HIGH"
    if factor >= 0.25:
        return "MEDIUM"
    return "LOW"


def risk_level(score: float) -> str:
    """Map a 0..100 risk score onto a risk band."""
    for low, high, label in RISK_BANDS:
        if low <= score <= high:
            return label
    return "CRITICAL" if score > 100 else "LOW"
