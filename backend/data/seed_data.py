"""
Synthetic MPLADS-style demonstration dataset.

IMPORTANT
---------
Every record in this file is invented for demonstration purposes. Constituency
names, MP names, agency names, villages, amounts and dates are fictitious and do
not correspond to any real sanctioned work, any real Member of Parliament, or
any real government record. The structure imitates the shape of MPLADS data so
that the analysis journey is realistic; the contents do not.

The dataset is deliberately mixed:

  * ~14 ordinary works that should produce little or no risk signal
  * one clean cost-overrun case            (MPLAD-2026-014)
  * one clean schedule-delay case          (MPLAD-2026-015)
  * one clean progress-mismatch case       (MPLAD-2026-016)
  * one clean data-inconsistency case      (MPLAD-2026-017)
  * two potential-overlap pairs            (024/025 and 019/020)
  * one multi-signal hero case             (MPLAD-2026-024)

No risk score is stored here. Scores are computed by the anomaly engine from
these fields at request time.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import Payment, Project

# Fictitious MP names used purely as record labels.
MP = {
    "jaipur": "Shri R. K. Meena (illustrative)",
    "nagpur": "Smt. A. V. Deshmukh (illustrative)",
    "varanasi": "Shri S. P. Tripathi (illustrative)",
    "coimbatore": "Shri M. Karthikeyan (illustrative)",
    "cuttack": "Smt. B. Mohanty (illustrative)",
    "guntur": "Shri K. Venkat Rao (illustrative)",
    "ludhiana": "Sardar J. S. Gill (illustrative)",
    "kamrup": "Shri D. Baruah (illustrative)",
    "bhopal": "Smt. N. Chouhan (illustrative)",
    "patna": "Shri A. K. Singh (illustrative)",
    "thrissur": "Shri P. J. Varghese (illustrative)",
    "dharwad": "Smt. S. R. Patil (illustrative)",
}

D = date  # brevity in the table below


# --------------------------------------------------------------------------- #
# The dataset. Read this table as the "source system" for the prototype.
# --------------------------------------------------------------------------- #
PROJECTS: list[dict] = [
    # ---------------------- ordinary works ------------------------------- #
    dict(
        project_id="MPLAD-2026-001",
        project_name="Installation of Solar Street Lights at Wadi Ward No. 3",
        description="Supply and installation of 40 LED solar street lights along internal roads of Ward No. 3, Wadi.",
        work_type="Solar Lighting", sector="Energy",
        location="Ward No. 3, Wadi", village="Wadi", district="Nagpur", state="Maharashtra",
        constituency="Nagpur", mp_name=MP["nagpur"],
        implementing_agency="Nagpur Municipal Corporation",
        recommendation_date=D(2025, 1, 12), sanction_date=D(2025, 2, 20),
        start_date=D(2025, 3, 10), expected_completion_date=D(2025, 9, 30),
        actual_completion_date=D(2025, 9, 18),
        estimated_cost=1400000, sanctioned_cost=1400000, actual_expenditure=1382000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=21.1102, longitude=79.0234,
    ),
    dict(
        project_id="MPLAD-2026-002",
        project_name="Construction of Anganwadi Centre at Chiraigaon",
        description="Construction of a single-room anganwadi centre with kitchen and store for the integrated child development scheme.",
        work_type="Anganwadi Building", sector="Women and Child Development",
        location="Chiraigaon Block", village="Chiraigaon", district="Varanasi", state="Uttar Pradesh",
        constituency="Varanasi", mp_name=MP["varanasi"],
        implementing_agency="District Rural Development Agency, Varanasi",
        recommendation_date=D(2025, 11, 5), sanction_date=D(2025, 12, 15),
        start_date=D(2026, 1, 20), expected_completion_date=D(2026, 12, 31),
        actual_completion_date=None,
        estimated_cost=1800000, sanctioned_cost=1800000, actual_expenditure=1030000,
        physical_progress=58, financial_progress=57, status="In Progress",
        latitude=25.4211, longitude=83.0512,
    ),
    dict(
        project_id="MPLAD-2026-003",
        project_name="Installation of RO Water Purification Plant at Sulur",
        description="Supply and commissioning of a 1000 litre per hour reverse osmosis drinking water plant with storage tank.",
        work_type="Drinking Water", sector="Water Supply",
        location="Sulur Panchayat", village="Sulur", district="Coimbatore", state="Tamil Nadu",
        constituency="Coimbatore", mp_name=MP["coimbatore"],
        implementing_agency="Tamil Nadu Water Supply and Drainage Board",
        recommendation_date=D(2024, 12, 3), sanction_date=D(2025, 1, 28),
        start_date=D(2025, 3, 5), expected_completion_date=D(2025, 11, 30),
        actual_completion_date=D(2025, 11, 12),
        estimated_cost=2200000, sanctioned_cost=2200000, actual_expenditure=2168000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=11.0247, longitude=77.1265,
    ),
    dict(
        project_id="MPLAD-2026-004",
        project_name="Construction of Additional Classroom at Government Upper Primary School, Salepur",
        description="Construction of one additional classroom of 600 square feet with flooring, plastering and electrification.",
        work_type="School Building", sector="Education",
        location="Salepur Block", village="Salepur", district="Cuttack", state="Odisha",
        constituency="Cuttack", mp_name=MP["cuttack"],
        implementing_agency="Odisha Rural Housing and Development Corporation",
        recommendation_date=D(2025, 9, 18), sanction_date=D(2025, 10, 25),
        start_date=D(2025, 12, 1), expected_completion_date=D(2026, 11, 30),
        actual_completion_date=None,
        estimated_cost=1650000, sanctioned_cost=1650000, actual_expenditure=1180000,
        physical_progress=72, financial_progress=72, status="In Progress",
        latitude=20.4571, longitude=86.0912,
    ),
    dict(
        project_id="MPLAD-2026-005",
        project_name="Construction of Cement Concrete Road at Pedakakani Village",
        description="Construction of 480 metre cement concrete village road with side drains from the bus stop to the primary school.",
        work_type="Rural Road", sector="Infrastructure",
        location="Pedakakani Mandal", village="Pedakakani", district="Guntur", state="Andhra Pradesh",
        constituency="Guntur", mp_name=MP["guntur"],
        implementing_agency="Panchayat Raj Engineering Department, Guntur",
        recommendation_date=D(2024, 10, 8), sanction_date=D(2024, 11, 22),
        start_date=D(2025, 1, 15), expected_completion_date=D(2025, 10, 31),
        actual_completion_date=D(2025, 10, 24),
        estimated_cost=2600000, sanctioned_cost=2600000, actual_expenditure=2574000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=16.3402, longitude=80.4988,
    ),
    dict(
        project_id="MPLAD-2026-006",
        project_name="Construction of Passenger Bus Shelter at Sahnewal",
        description="Construction of a covered passenger waiting shelter with seating and information board at the Sahnewal bus stop.",
        work_type="Bus Shelter", sector="Transport",
        location="Sahnewal", village="Sahnewal", district="Ludhiana", state="Punjab",
        constituency="Ludhiana", mp_name=MP["ludhiana"],
        implementing_agency="Punjab Mandi Board",
        recommendation_date=D(2025, 2, 14), sanction_date=D(2025, 3, 28),
        start_date=D(2025, 5, 6), expected_completion_date=D(2025, 12, 15),
        actual_completion_date=D(2025, 12, 2),
        estimated_cost=780000, sanctioned_cost=780000, actual_expenditure=771000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=30.8452, longitude=75.9622,
    ),
    dict(
        project_id="MPLAD-2026-007",
        project_name="Supply of Furniture and Books to Panchayat Public Library, Ollur",
        description="Supply of reading tables, chairs, book racks and reference books to the panchayat public library.",
        work_type="Library Equipment", sector="Education",
        location="Ollur Panchayat", village="Ollur", district="Thrissur", state="Kerala",
        constituency="Thrissur", mp_name=MP["thrissur"],
        implementing_agency="Kerala State Library Council",
        recommendation_date=D(2026, 1, 9), sanction_date=D(2026, 2, 17),
        start_date=D(2026, 3, 20), expected_completion_date=D(2026, 12, 20),
        actual_completion_date=None,
        estimated_cost=950000, sanctioned_cost=950000, actual_expenditure=480000,
        physical_progress=52, financial_progress=51, status="In Progress",
        latitude=10.4842, longitude=76.2411,
    ),
    dict(
        project_id="MPLAD-2026-008",
        project_name="Construction of Borewell with Submersible Pump at Rani",
        description="Drilling of a 180 metre deep borewell with submersible pump, panel board and platform for drinking water supply.",
        work_type="Drinking Water", sector="Water Supply",
        location="Rani Development Block", village="Rani", district="Kamrup", state="Assam",
        constituency="Gauhati", mp_name=MP["kamrup"],
        implementing_agency="Assam Public Health Engineering Department",
        recommendation_date=D(2025, 3, 11), sanction_date=D(2025, 4, 24),
        start_date=D(2025, 6, 2), expected_completion_date=D(2026, 1, 31),
        actual_completion_date=D(2026, 1, 19),
        estimated_cost=1250000, sanctioned_cost=1250000, actual_expenditure=1231000,
        physical_progress=100, financial_progress=98, status="Completed",
        latitude=26.0512, longitude=91.5433,
    ),
    dict(
        project_id="MPLAD-2026-009",
        project_name="Construction of Toilet Block at Government Girls School, Berasia",
        description="Construction of a six-seat sanitary toilet block with water connection and septic tank for the government girls school.",
        work_type="Sanitation", sector="Sanitation",
        location="Berasia Tehsil", village="Berasia", district="Bhopal", state="Madhya Pradesh",
        constituency="Bhopal", mp_name=MP["bhopal"],
        implementing_agency="Madhya Pradesh Rural Road Development Authority",
        recommendation_date=D(2025, 12, 2), sanction_date=D(2026, 1, 16),
        start_date=D(2026, 2, 25), expected_completion_date=D(2026, 12, 31),
        actual_completion_date=None,
        estimated_cost=1450000, sanctioned_cost=1450000, actual_expenditure=790000,
        physical_progress=56, financial_progress=54, status="In Progress",
        latitude=23.6301, longitude=77.4322,
    ),
    dict(
        project_id="MPLAD-2026-010",
        project_name="Supply of Ambulance to Primary Health Centre, Bihta",
        description="Supply of one fully equipped basic life support ambulance to the primary health centre.",
        work_type="Health Equipment", sector="Health",
        location="Bihta Block", village="Bihta", district="Patna", state="Bihar",
        constituency="Pataliputra", mp_name=MP["patna"],
        implementing_agency="Bihar Medical Services and Infrastructure Corporation",
        recommendation_date=D(2025, 5, 20), sanction_date=D(2025, 6, 30),
        start_date=D(2025, 8, 11), expected_completion_date=D(2026, 2, 28),
        actual_completion_date=D(2026, 2, 14),
        estimated_cost=2400000, sanctioned_cost=2400000, actual_expenditure=2381000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=25.5512, longitude=84.8712,
    ),
    dict(
        project_id="MPLAD-2026-011",
        project_name="Construction of Covered Drainage at Navalgund Ward No. 7",
        description="Construction of 320 metre covered reinforced cement concrete storm water drain along the ward main road.",
        work_type="Drainage", sector="Infrastructure",
        location="Ward No. 7, Navalgund", village="Navalgund", district="Dharwad", state="Karnataka",
        constituency="Dharwad", mp_name=MP["dharwad"],
        implementing_agency="Karnataka Rural Infrastructure Development Limited",
        recommendation_date=D(2025, 10, 14), sanction_date=D(2025, 11, 27),
        start_date=D(2026, 1, 8), expected_completion_date=D(2026, 12, 15),
        actual_completion_date=None,
        estimated_cost=1950000, sanctioned_cost=1950000, actual_expenditure=1290000,
        physical_progress=67, financial_progress=66, status="In Progress",
        latitude=15.5612, longitude=75.3611,
    ),
    dict(
        project_id="MPLAD-2026-012",
        project_name="Development of Playground at Zilla Parishad School, Kamptee",
        description="Levelling, fencing and installation of play equipment in the school playground area.",
        work_type="Sports Infrastructure", sector="Sports",
        location="Kamptee Tehsil", village="Kamptee", district="Nagpur", state="Maharashtra",
        constituency="Ramtek", mp_name=MP["nagpur"],
        implementing_agency="Zilla Parishad, Nagpur",
        recommendation_date=D(2025, 11, 21), sanction_date=D(2026, 1, 5),
        start_date=D(2026, 2, 16), expected_completion_date=D(2026, 12, 10),
        actual_completion_date=None,
        estimated_cost=1120000, sanctioned_cost=1120000, actual_expenditure=680000,
        physical_progress=61, financial_progress=61, status="In Progress",
        latitude=21.2312, longitude=79.1944,
    ),
    dict(
        project_id="MPLAD-2026-013",
        project_name="Construction of Shed at Public Crematorium, Ramnagar",
        description="Construction of a roofed shed with seating platform and water point at the public crematorium ground.",
        work_type="Public Amenity", sector="Urban Development",
        location="Ramnagar", village="Ramnagar", district="Varanasi", state="Uttar Pradesh",
        constituency="Varanasi", mp_name=MP["varanasi"],
        implementing_agency="Varanasi Nagar Nigam",
        recommendation_date=D(2024, 11, 26), sanction_date=D(2025, 1, 14),
        start_date=D(2025, 2, 24), expected_completion_date=D(2025, 12, 20),
        actual_completion_date=D(2025, 12, 8),
        estimated_cost=1680000, sanctioned_cost=1680000, actual_expenditure=1654000,
        physical_progress=100, financial_progress=98, status="Completed",
        latitude=25.2822, longitude=83.0201,
    ),
    dict(
        project_id="MPLAD-2026-026",
        project_name="Supply of Sports Equipment to Youth Club, Pollachi",
        description="Supply of indoor and outdoor sports equipment including kits, nets and mats to the registered youth club.",
        work_type="Sports Equipment", sector="Sports",
        location="Pollachi Taluk", village="Pollachi", district="Coimbatore", state="Tamil Nadu",
        constituency="Pollachi", mp_name=MP["coimbatore"],
        implementing_agency="Tamil Nadu Sports Development Authority",
        recommendation_date=D(2025, 6, 17), sanction_date=D(2025, 7, 29),
        start_date=D(2025, 9, 8), expected_completion_date=D(2026, 3, 31),
        actual_completion_date=D(2026, 3, 20),
        estimated_cost=620000, sanctioned_cost=620000, actual_expenditure=611000,
        physical_progress=100, financial_progress=99, status="Completed",
        latitude=10.6588, longitude=77.0086,
    ),

    # ---------------------- single-signal cases --------------------------- #
    # Cost overrun only.
    dict(
        project_id="MPLAD-2026-014",
        project_name="Construction of Cement Concrete Road at Jagraon Link Road",
        description="Construction of 610 metre cement concrete link road with kerb stones connecting the grain market to the highway.",
        work_type="Rural Road", sector="Infrastructure",
        location="Jagraon", village="Jagraon", district="Ludhiana", state="Punjab",
        constituency="Ludhiana", mp_name=MP["ludhiana"],
        implementing_agency="Punjab Public Works Department",
        recommendation_date=D(2024, 9, 4), sanction_date=D(2024, 10, 18),
        start_date=D(2024, 12, 9), expected_completion_date=D(2025, 12, 31),
        actual_completion_date=D(2025, 12, 22),
        estimated_cost=1800000, sanctioned_cost=1800000, actual_expenditure=2430000,
        physical_progress=100, financial_progress=100, status="Completed",
        latitude=30.7889, longitude=75.4731,
    ),
    # Schedule delay only.
    dict(
        project_id="MPLAD-2026-015",
        project_name="Construction of Additional Classrooms at Government High School, Chandrapur",
        description="Construction of two additional classrooms with verandah, flooring and electrical fittings.",
        work_type="School Building", sector="Education",
        location="Chandrapur Block", village="Chandrapur", district="Kamrup", state="Assam",
        constituency="Gauhati", mp_name=MP["kamrup"],
        implementing_agency="Assam Public Works Department",
        recommendation_date=D(2024, 3, 8), sanction_date=D(2024, 4, 22),
        start_date=D(2024, 6, 10), expected_completion_date=D(2025, 12, 31),
        actual_completion_date=None,
        estimated_cost=2800000, sanctioned_cost=2800000, actual_expenditure=1596000,
        physical_progress=55, financial_progress=57, status="In Progress",
        latitude=26.2033, longitude=91.8811,
    ),
    # Financial vs physical mismatch only.
    dict(
        project_id="MPLAD-2026-016",
        project_name="Construction of Community Toilet Block at Bairagarh",
        description="Construction of a ten-seat community sanitary complex with overhead tank, bathing cubicles and caretaker room.",
        work_type="Sanitation", sector="Sanitation",
        location="Bairagarh", village="Bairagarh", district="Bhopal", state="Madhya Pradesh",
        constituency="Bhopal", mp_name=MP["bhopal"],
        implementing_agency="Bhopal Municipal Corporation",
        recommendation_date=D(2026, 1, 15), sanction_date=D(2026, 2, 10),
        start_date=D(2026, 3, 1), expected_completion_date=D(2027, 6, 30),
        actual_completion_date=None,
        estimated_cost=1200000, sanctioned_cost=1200000, actual_expenditure=1104000,
        physical_progress=48, financial_progress=92, status="In Progress",
        latitude=23.2511, longitude=77.3644,
    ),
    # Data inconsistency only: invalid progress, missing fields, small overrun
    # below the cost tolerance (so validation fires but the cost detector does not).
    dict(
        project_id="MPLAD-2026-017",
        project_name="Supply and Installation of Solar Street Lights at Tenali",
        description="Supply and installation of 25 solar powered street lights with poles and batteries in the municipal area.",
        work_type="Solar Lighting", sector="Energy",
        location="Tenali Municipality", village="Tenali", district="Guntur", state="Andhra Pradesh",
        constituency="Guntur", mp_name=MP["guntur"],
        implementing_agency="Andhra Pradesh State Energy Conservation Mission",
        recommendation_date=None, sanction_date=D(2025, 4, 15),
        start_date=D(2025, 6, 1), expected_completion_date=D(2026, 3, 31),
        actual_completion_date=D(2026, 3, 25),
        estimated_cost=None, sanctioned_cost=900000, actual_expenditure=930000,
        physical_progress=105, financial_progress=100, status="Completed",
        latitude=None, longitude=None,
    ),

    # ---------------------- multi-signal cases ---------------------------- #
    dict(
        project_id="MPLAD-2026-018",
        project_name="Construction of Cement Concrete Road from Main Road to Harijan Tola, Bihta",
        description="Construction of 750 metre cement concrete road with side drains and culvert crossing in the habitation.",
        work_type="Rural Road", sector="Infrastructure",
        location="Bihta Block", village="Bihta", district="Patna", state="Bihar",
        constituency="Pataliputra", mp_name=MP["patna"],
        implementing_agency="Bihar Rural Works Department",
        recommendation_date=D(2025, 2, 6), sanction_date=D(2025, 3, 20),
        start_date=D(2025, 5, 15), expected_completion_date=D(2026, 6, 30),
        actual_completion_date=None,
        estimated_cost=3200000, sanctioned_cost=3200000, actual_expenditure=4300000,
        physical_progress=60, financial_progress=88, status="In Progress",
        latitude=25.5601, longitude=84.8901,
    ),
    dict(
        project_id="MPLAD-2026-021",
        project_name="Construction of Boundary Wall and Gate at Primary School, Chiraigaon",
        description="Construction of 220 metre boundary wall with iron gate, plastering and painting around the primary school premises.",
        work_type="School Building", sector="Education",
        location="Chiraigaon Block", village="Chiraigaon", district="Varanasi", state="Uttar Pradesh",
        constituency="Varanasi", mp_name=MP["varanasi"],
        implementing_agency="Uttar Pradesh Rural Engineering Services",
        recommendation_date=D(2025, 1, 28), sanction_date=D(2025, 3, 12),
        start_date=D(2025, 4, 25), expected_completion_date=D(2026, 5, 31),
        actual_completion_date=None,
        estimated_cost=1500000, sanctioned_cost=1500000, actual_expenditure=1830000,
        physical_progress=52, financial_progress=79, status="In Progress",
        latitude=25.4188, longitude=83.0489,
    ),
    dict(
        project_id="MPLAD-2026-022",
        project_name="Renovation of Panchayat Library Building at Chalakudy",
        description="Renovation of the existing panchayat library building including roof repair, flooring and rewiring.",
        work_type="Library Building", sector="Education",
        location="Chalakudy Municipality", village="Chalakudy", district="Thrissur", state="Kerala",
        constituency="Chalakudy", mp_name=MP["thrissur"],
        implementing_agency="Kerala Public Works Department",
        recommendation_date=D(2025, 8, 19), sanction_date=D(2025, 9, 30),
        start_date=D(2025, 11, 14), expected_completion_date=D(2026, 10, 31),
        actual_completion_date=None,
        estimated_cost=1750000, sanctioned_cost=1750000, actual_expenditure=1435000,
        physical_progress=54, financial_progress=82, status="In Progress",
        latitude=10.3061, longitude=76.3344,
    ),
    dict(
        project_id="MPLAD-2026-023",
        project_name="Installation of Overhead Water Tank at Navalgund",
        description="Construction of a 50000 litre overhead reinforced cement concrete water tank with pumping arrangement.",
        work_type="Drinking Water", sector="Water Supply",
        location="Navalgund Taluk", village="Navalgund", district="Dharwad", state="Karnataka",
        constituency="Dharwad", mp_name=MP["dharwad"],
        implementing_agency="Karnataka Urban Water Supply and Drainage Board",
        recommendation_date=D(2025, 4, 7), sanction_date=D(2025, 5, 19),
        start_date=D(2025, 7, 1), expected_completion_date=D(2026, 8, 15),
        actual_completion_date=None,
        estimated_cost=2900000, sanctioned_cost=2900000, actual_expenditure=3380000,
        physical_progress=71, financial_progress=88, status="In Progress",
        latitude=15.5644, longitude=75.3688,
    ),

    # ---------------------- overlap pair #2 (Nagpur) ---------------------- #
    dict(
        project_id="MPLAD-2026-019",
        project_name="Construction of Cement Concrete Road at Wadi Ward No. 5",
        description="Construction of 380 metre cement concrete internal road with side drain in Ward No. 5 of Wadi.",
        work_type="Rural Road", sector="Infrastructure",
        location="Ward No. 5, Wadi", village="Wadi", district="Nagpur", state="Maharashtra",
        constituency="Nagpur", mp_name=MP["nagpur"],
        implementing_agency="Nagpur Municipal Corporation",
        recommendation_date=D(2025, 6, 11), sanction_date=D(2025, 7, 23),
        start_date=D(2025, 9, 4), expected_completion_date=D(2026, 8, 31),
        actual_completion_date=None,
        estimated_cost=2100000, sanctioned_cost=2100000, actual_expenditure=1638000,
        physical_progress=66, financial_progress=78, status="In Progress",
        latitude=21.1119, longitude=79.0251,
    ),
    dict(
        project_id="MPLAD-2026-020",
        project_name="Construction of Internal Cement Concrete Road in Ward No. 5, Wadi",
        description="Construction of 360 metre cement concrete internal road with side drain in Ward No. 5 of Wadi.",
        work_type="Rural Road", sector="Infrastructure",
        location="Ward No. 5, Wadi", village="Wadi", district="Nagpur", state="Maharashtra",
        constituency="Nagpur", mp_name=MP["nagpur"],
        implementing_agency="Zilla Parishad, Nagpur",
        recommendation_date=D(2025, 7, 2), sanction_date=D(2025, 8, 14),
        start_date=D(2025, 10, 6), expected_completion_date=D(2026, 9, 30),
        actual_completion_date=None,
        estimated_cost=1980000, sanctioned_cost=1980000, actual_expenditure=1584000,
        physical_progress=70, financial_progress=80, status="In Progress",
        latitude=21.1131, longitude=79.0268,
    ),

    # ---------------------- HERO: multi-signal case ----------------------- #
    dict(
        project_id="MPLAD-2026-024",
        project_name="Construction of Community Hall at Village Rampur",
        description="Construction of a community hall with assembly area, store room and toilet block for public use at Rampur village.",
        work_type="Community Hall", sector="Rural Development",
        location="Rampur, Sanganer Tehsil", village="Rampur", district="Jaipur", state="Rajasthan",
        constituency="Jaipur Rural", mp_name=MP["jaipur"],
        implementing_agency="Rural Development Department, Jaipur",
        recommendation_date=D(2025, 6, 24),
        sanction_date=D(2025, 8, 20),
        # Work start recorded BEFORE the sanction date: a date-sequence error the
        # validation engine flags and the data-quality detector scores.
        start_date=D(2025, 8, 4),
        expected_completion_date=D(2026, 9, 15),
        actual_completion_date=None,
        estimated_cost=None,  # missing: recorded as a completeness issue
        sanctioned_cost=2500000,
        actual_expenditure=3300000,
        physical_progress=41,
        financial_progress=82,
        status="In Progress",
        latitude=26.9601, longitude=75.6421,
    ),
    # The comparable work that triggers the overlap signal on both records.
    dict(
        project_id="MPLAD-2026-025",
        project_name="Construction of Community Centre at Rampur Village",
        description="Construction of a community centre with assembly hall, store room and toilet block for public use at Rampur village.",
        work_type="Community Hall", sector="Rural Development",
        location="Rampur, Sanganer Tehsil", village="Rampur", district="Jaipur", state="Rajasthan",
        constituency="Jaipur Rural", mp_name=MP["jaipur"],
        implementing_agency="Zilla Parishad, Jaipur",
        recommendation_date=D(2025, 9, 16), sanction_date=D(2025, 10, 28),
        start_date=D(2025, 11, 10), expected_completion_date=D(2026, 11, 30),
        actual_completion_date=None,
        estimated_cost=2200000, sanctioned_cost=2200000, actual_expenditure=1980000,
        physical_progress=72, financial_progress=90, status="In Progress",
        latitude=26.9628, longitude=75.6449,
    ),
]


# --------------------------------------------------------------------------- #
# Payments
# --------------------------------------------------------------------------- #
VENDORS = [
    "Shree Balaji Constructions",
    "Nav Bharat Infra Works",
    "Vishwakarma Builders and Suppliers",
    "Annapurna Engineering Works",
    "Konark Traders and Contractors",
    "Sunrise Infratech Private Limited",
]


def _payments_for(project: dict) -> list[dict]:
    """Split the recorded expenditure into a small, deterministic set of releases.

    The tranche pattern is derived from the project id so the data is stable
    across restarts — there is no randomness anywhere in the seed.
    """
    total = project.get("actual_expenditure") or 0
    if total <= 0:
        return []

    seed_int = int(project["project_id"].split("-")[-1])
    n = 2 + (seed_int % 3)  # 2, 3 or 4 tranches
    start = project.get("start_date") or project.get("sanction_date")
    if start is None:
        return []

    # Front-loaded split, normalised so the tranches sum to the expenditure.
    raw = [1.0 / (i + 1) for i in range(n)]
    scale = total / sum(raw)
    amounts = [round(v * scale, 2) for v in raw]
    amounts[-1] = round(total - sum(amounts[:-1]), 2)

    rows = []
    for i, amount in enumerate(amounts):
        month_offset = 2 + i * 3
        year = start.year + (start.month - 1 + month_offset) // 12
        month = (start.month - 1 + month_offset) % 12 + 1
        day = min(start.day, 28)
        rows.append(
            {
                "payment_amount": amount,
                "payment_date": date(year, month, day),
                "vendor": VENDORS[(seed_int + i) % len(VENDORS)],
                "transaction_sequence": i + 1,
            }
        )
    return rows


def seed(db: Session) -> dict:
    """Insert the synthetic dataset. Returns row counts."""
    payment_count = 0
    for record in PROJECTS:
        db.add(Project(**record))
        for payment in _payments_for(record):
            db.add(Payment(project_id=record["project_id"], **payment))
            payment_count += 1

    db.commit()
    return {"projects": len(PROJECTS), "payments": payment_count}
