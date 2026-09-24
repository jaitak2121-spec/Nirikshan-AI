# NIRIKSHAN AI

**MPLADS Risk Intelligence & Investigation Network**

A working prototype that reads a register of MPLADS-style public works, applies
deterministic checks to each record, and produces a prioritised list of works
that warrant verification first — with a full, auditable account of why each one
was flagged.

> **This prototype uses synthetic MPLADS-style demonstration data and does not
> represent official government records.**

---

## The problem

Under the Members of Parliament Local Area Development Scheme, each MP recommends
local development works — roads, community halls, drains, school rooms, water
supply — implemented through district agencies. The works are numerous,
geographically dispersed, and reviewed by a small number of officers.

Reviewing every record with equal attention is not feasible. Problems therefore
surface late, often after funds have been released: a work billed at 92% while
the site shows 48% complete, expenditure past the sanctioned limit with no
recorded revision, two sanctions for what appears to be one asset in the same
village.

The gap is not a shortage of data. It is that nobody can tell, from a list of
several hundred rows, **which twelve rows to look at this week, and why**.

## What this system does

NIRIKSHAN AI is a triage and decision-support layer over the works register.
For every work it:

1. **Validates** the record — missing fields, impossible values, dates out of
   sequence.
2. **Runs five deterministic detectors** — cost overrun, financial-vs-physical
   progress mismatch, schedule delay, potential duplicate/overlapping work, and
   record quality.
3. **Fuses the signals** into a single 0–100 risk score using fixed published
   weights.
4. **Explains every signal** — what happened, the actual value, the expected or
   threshold value, the difference, and why it matters.
5. **Recommends concrete verification steps** for each signal and for the work
   as a whole.

Everything reported is derived from values already present in the record. There
is no black box: the score can be reconstructed by hand from the breakdown shown
on screen.

### What it explicitly does not do

It does not establish irregularity, misappropriation or wrongdoing of any kind,
and it produces no finding of fraud. A high score means the recorded values
match a pattern worth verifying — nothing more. Signals have legitimate
explanations: a cost overrun may have an approved revision absent from the
dataset; two similar works may be genuinely distinct assets. **Every
determination rests with the authorised officer reviewing the source records.**

This constraint is enforced in the code, not just in documentation — every
detector's wording is written as a verification prompt, and an automated check
(`tools/acceptance_test.py`) scans both the source and every API response for
accusatory phrasing.

---

## Architecture

```
Synthetic MPLADS-style dataset  (backend/data/seed_data.py → SQLite)
              │
              ▼
      Validation engine          (anomaly_engine/validation.py)
              │   missing fields, range violations, date-sequence errors
              ▼
      Feature engineering        (deviation %, progress gap, schedule deficit,
              │                   TF-IDF vectors, Haversine distances)
              ▼
      Anomaly detectors          (anomaly_engine/detectors.py,
              │                   anomaly_engine/duplicate_detection.py)
              ▼
      Risk fusion                (anomaly_engine/risk_engine.py)
              │   weighted additive score, clamped 0–100, banded
              ▼
      Explanation + actions      (anomaly_engine/explanation_engine.py)
              │
              ▼
      FastAPI                    (backend/routers/*)
              │
              ▼
      React interface            (frontend/src/*)
```

The `anomaly_engine/` package operates on **plain dictionaries only**. It has no
dependency on FastAPI, SQLAlchemy or HTTP, so it can be unit-tested directly or
pointed at a different data source. `backend/services/analysis_service.py` is
the thin bridge that loads ORM rows, hands dicts to the engine, and shapes the
result for the API.

**Risk scores are never stored.** There is no `risk_score` column. Every figure
in the interface is computed on request — analysing the full 26-work corpus takes
about 3 ms, so caching would add complexity for no benefit.

### Repository layout

```
MPlads/
├── anomaly_engine/              # Pure analysis logic — no web, no DB
│   ├── config.py                #   all weights, bands and thresholds
│   ├── validation.py            #   §6 record validation
│   ├── detectors.py             #   cost, delay, progress mismatch, data quality
│   ├── duplicate_detection.py   #   TF-IDF + cosine + Haversine
│   ├── text_similarity.py       #   TF-IDF and cosine similarity in NumPy
│   ├── risk_engine.py           #   weighted fusion and banding
│   ├── explanation_engine.py    #   explanations + recommended actions
│   ├── lineage.py               #   data provenance chain
│   ├── formatting.py            #   ₹ / % / date display helpers
│   └── pipeline.py              #   orchestrates one work end to end
│
├── backend/
│   ├── main.py                  # app, CORS, lifespan seeding, error handler
│   ├── database.py              # engine, session, init_db
│   ├── models.py                # Project, Payment
│   ├── schemas.py               # Pydantic response models
│   ├── data/seed_data.py        # 26 synthetic works + 79 payment records
│   ├── services/
│   │   └── analysis_service.py  # DB ↔ engine bridge, aggregations
│   └── routers/
│       ├── projects.py          # list, detail, similar, nearby
│       ├── dashboard.py         # stats, investigation queue, agencies
│       └── analysis.py          # analyze, anomalies, methodology
│
├── frontend/
│   ├── src/
│   │   ├── components/          # DashboardCard, RiskBadge, RiskScore,
│   │   │                        #   ProgressBar, ProjectTable, AnomalyCard,
│   │   │                        #   EvidenceCard, ProximityMap, Lineage,
│   │   │                        #   Sidebar, Header, DataNotice, States
│   │   ├── pages/               # Dashboard, Projects, ProjectDetails,
│   │   │                        #   InvestigationQueue, Agencies, About
│   │   ├── services/api.js      # the only place the frontend talks to HTTP
│   │   ├── hooks/useApi.js      # fetch + abort + loading/error state
│   │   └── utils/format.js      # ₹ / % / date / risk-colour helpers
│   └── test/                    # server-side page render test
│
├── database/nirikshan.db        # created and seeded on first backend start
└── tools/                       # test and inspection scripts
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite 6, Tailwind CSS 3, React Router 6, Recharts 2 |
| Backend | FastAPI, Uvicorn, Pydantic 2 |
| Database | SQLite via SQLAlchemy 2 |
| Analysis | NumPy (TF-IDF, cosine similarity), plain Python |

**On scikit-learn:** the specification allows it "only where genuinely useful".
The one place it would have been used is TF-IDF vectorisation for duplicate
detection, which is about forty lines of NumPy. It is implemented directly in
`anomaly_engine/text_similarity.py`, matching scikit-learn's default
`TfidfVectorizer` behaviour (smooth IDF `ln((1+n)/(1+df)) + 1`, L2 row
normalisation, token pattern `(?u)\b\w\w+\b`). This removes a large dependency
without changing the arithmetic.

---

## How to run

No credentials, no login — the prototype has no authentication.

### Quickest: one command, one terminal

`frontend/dist` is committed, and the API serves it, so the backend alone serves
the whole prototype:

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
```

```bash
.venv/bin/uvicorn backend.main:app --port 8000
```

Open `http://localhost:8000`. The database is created and seeded automatically on
first start. Interactive API docs are at `http://localhost:8000/docs`.

Use this for a demo. It has the fewest moving parts and matches what the
deployment serves.

### For frontend development: two terminals

Vite's dev server gives hot reload, which the built bundle does not.

```bash
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`, so
no environment variables are needed.

After changing frontend code, run `cd frontend && npm run build` and commit the
regenerated `frontend/dist` — that directory is what the single-command run and
the deployment both serve.

### Deploying

`vercel.json` deploys without a Node build step: the committed `frontend/dist` is
served as static files and `api/index.py` exposes the same FastAPI app as a
serverless function. Only two project settings matter — **Framework Preset:
Other** and **Root Directory:** the repository root, not `backend`. `.python-version`
pins CPython 3.12, because 3.14 has no prebuilt wheel for `pydantic-core` and
would try to compile it from source.

### Tests

```bash
.venv/bin/python -m tools.acceptance_test
```

96 checks over the live API: seeding, every endpoint, the hero journey, score
reconstruction from the published breakdown, determinism, error handling, and a
scan of both source and API responses for accusatory language.

```bash
cd frontend && npm test
```

73 checks that render all nine pages server-side against recorded backend
payloads, asserting no `undefined`/`NaN`/`[object Object]` reaches the screen, no
React warnings are raised, expected content is present, and the rendered text
obeys the language rule.

The payloads the render test uses are captured from the real API, not
hand-written. Refresh them after changing the engine or any response shape:

```bash
.venv/bin/python -m tools.dump_fixtures
```

`tools/offline_npm_install.mjs` is a development-environment fallback that
resolves `frontend/package.json` from an existing local npm cache when the
registry is unreachable. It is not needed if `npm install` works.

---

## How the synthetic data works

`backend/data/seed_data.py` defines 26 works as literal Python dictionaries.
Every value is invented. MP names, agency names and village names are fictitious
and marked as illustrative. Coordinates are plausible for their stated districts
but are not real work sites.

The corpus is composed so that each detector has something to find and most
records have nothing wrong with them:

| Works | Character |
|---|---|
| 001–013, 026 | Ordinary works — on budget, on schedule, consistent. 14 of the 26 score exactly 0. |
| 014 | Cost overrun only (₹18,00,000 sanctioned → ₹24,30,000 spent) |
| 015 | Schedule delay only |
| 016 | Financial-vs-physical mismatch only (48% physical, 92% financial) |
| 017 | Data inconsistency only — `physical_progress = 105`, null estimated cost, null recommendation date, missing coordinates |
| 018, 021, 022, 023 | Two or three concurrent signals |
| 019, 020 | An overlapping pair — two drain works in the same ward, 0.2 km apart |
| **024** | **The hero work** — five concurrent signals |
| 025 | The hero's overlap partner, 0.41 km away |

Payments are derived deterministically from each work: 2–4 front-loaded tranches
summing to the recorded expenditure, dated from the start date, with vendors
picked by a fixed index. No randomness anywhere — the same input always produces
the same output, which is what makes the demo reproducible.

---

## Anomaly detection logic

All five detectors are rule-based and deterministic. Each returns a *severity
factor* between 0 and 1, which scales linearly from the tolerance threshold (0)
to the full-severity threshold (1). A marginal breach therefore scores far lower
than a severe one.

### A. Cost anomaly — max 25 points

```
cost_deviation_pct = (actual_expenditure − sanctioned_cost) / sanctioned_cost × 100
```

Ignored at or below 5% tolerance; full severity at 25% over. Only overruns are
flagged — underspend is not a cost anomaly.

### B. Progress mismatch — max 25 points

```
gap_pp = financial_progress − physical_progress
```

Ignored at or below 10 percentage points; full severity at 40 pp. Only money
running *ahead* of work is flagged; the reverse is not penalised.

### C. Delay risk — max 20 points

Two tests, whichever is worse:

```
overdue_days        = as_of − expected_completion_date
expected_progress   = elapsed_days / total_days × 100      (straight line)
schedule_deficit_pp = expected_progress − physical_progress
```

Deficit is ignored at or below 15 pp and reaches full severity at 50 pp.
Completed works are skipped — finishing late is a performance fact, not an open
risk signal.

### D. Potential duplicate / overlapping work — max 20 points

TF-IDF vectors are built over project name, description and work type, then
compared pairwise by cosine similarity. Location words are **excluded from the
text** so that two works do not look similar merely for being in the same
district. A pair is raised only when it is *both* textually similar (≥ 0.62) and
co-located (same village, or within 3 km by Haversine great-circle distance).

```
similarity = cosine(tfidf(work_a), tfidf(work_b))
raised when similarity ≥ 0.62  AND  (same_village OR distance ≤ 3 km)
```

This detector never asserts duplication. Its wording is always
*"Potential duplicate/overlapping work requiring verification."*

### E. Data quality — max 10 points

The validation engine checks, per §6: required fields present; expenditure not
exceeding sanctioned cost; no negative cost or expenditure; progress within
0–100; dates parseable; completion not before sanction; expected completion not
before start. Each issue carries a penalty; the total is scaled against a
full-penalty threshold.

A record that cannot be trusted cannot be assessed reliably, so its quality is
scored as a signal in its own right rather than silently ignored. Issues that
another detector already scores are excluded here, so nothing is counted twice.

---

## Risk scoring logic

```
risk_score = clamp( Σ (weight_i × severity_factor_i), 0, 100 )
```

| Signal | Max weight |
|---|---|
| Cost anomaly | 25 |
| Progress mismatch | 25 |
| Delay risk | 20 |
| Potential duplicate | 20 |
| Data quality | 10 |

| Band | Range |
|---|---|
| LOW | 0–24 |
| MEDIUM | 25–49 |
| HIGH | 50–74 |
| CRITICAL | 75–100 |

The fusion is additive and linear **on purpose**. A reviewer can read the
breakdown on a project page and reconstruct the total by hand. A non-linear or
learned combination would score better on paper and be far harder to defend in a
file. `GET /api/methodology` publishes every weight, band and threshold the
engine applies, and the About page reads it live so documentation cannot drift
from behaviour.

Nothing is hardcoded. No project's score is set, adjusted or forced. The
corpus-wide distribution that emerges is:

```
LOW 18   MEDIUM 5   HIGH 2   CRITICAL 1
```

An honest consequence of this: MPLAD-2026-020 scores 24 (LOW) while its overlap
partner MPLAD-2026-019 scores 33 (MEDIUM), because 020's progress gap is exactly
10 pp and falls inside the tolerance. The asymmetry is left in place — it is
evidence that the scores are computed from data rather than assigned.

---

## Demo flow

**Hero project: `MPLAD-2026-024` — Construction of Community Hall at Village
Rampur, Jaipur, Rajasthan.**

1. Open `http://localhost:5173` (or `http://localhost:8000` for the single-command
   run). The dashboard loads with 26 works, 27 signals
   and the risk distribution chart.
2. The **Critical** card reads 1. Click through, or open **Investigation
   Queue** — MPLAD-2026-024 sits at priority 1 with a score of 94.
3. Open the work. The record header shows the score, band and signal count
   beside an **Analyze Risk** button.
4. Press **Analyze Risk**. This is a real round trip: `POST
   /api/projects/MPLAD-2026-024/analyze` re-runs validation, all five detectors,
   corpus-wide duplicate detection and risk fusion, then returns the result.
5. **WHY FLAGGED?** lists the five signals, largest contribution first.
6. Expand any signal for its actual value, expected value, difference, why it
   matters, evidence rows drawn from the record, and its own recommended
   verification steps.
7. **Score arithmetic** shows the five contributions summing to 94.5 → 94.
8. **Recommended action** gives the checklist and the headline
   *"Priority verification recommended."*
9. **Comparable works** and the proximity map show MPLAD-2026-025, 0.41 km away
   with 91% textual similarity.
10. **Data lineage** traces the record from synthetic dataset through validation,
    feature engineering, the anomaly engine and risk fusion to investigation.
11. The disclaimer states that the determination rests with the authorised
    officer.

### How the hero reaches 94

| Signal | Weight | × Severity | = Points |
|---|---|---|---|
| Cost anomaly — ₹33,00,000 spent against ₹25,00,000 sanctioned (+32%) | 25 | 1.00 | 25.0 |
| Progress mismatch — 82% financial against 41% physical (41 pp gap) | 25 | 1.00 | 25.0 |
| Delay risk — 41% complete against 97% expected (56 pp behind) | 20 | 1.00 | 20.0 |
| Potential duplicate — 91% similarity with MPLAD-2026-025, 0.41 km apart | 20 | 1.00 | 20.0 |
| Data quality — 82/100, missing estimated cost, start date before sanction | 10 | 0.45 | 4.5 |
| **Total** | | | **94.5 → 94, CRITICAL** |

The score was not clamped, and no part of it was assigned. It is the sum of what
the seeded field values produce.

---

## Known limitations

- **The dataset is synthetic.** Thresholds are calibrated against invented
  records and would need recalibration against real distributions before any
  operational use.
- **Duplicate detection compares text and location only.** It cannot distinguish
  a genuine duplicate sanction from two legitimately distinct works described in
  similar words at nearby sites — which is why it reports a verification prompt
  rather than a finding.
- **Delay assessment assumes straight-line progress** between start and expected
  completion. Real works are seasonal and lumpy, so an early-stage work can
  appear behind schedule when it is not.
- **A missing field cannot be distinguished from a field that is genuinely not
  applicable.** Both reduce the data quality score.
- **Scores are comparable within this dataset only.** A score of 60 is not an
  absolute measure of anything.
- **No authentication, no audit log, no role separation.** The prototype
  demonstrates the analysis, not the controls a deployed system would require.
- **Agency averages are descriptive, not diagnostic.** A mean over two or three
  works says more about those works than about the agency.
- **The geographic view is a plain SVG scatter**, not a basemap. It shows
  relative positions and Haversine distances, which is what the duplicate
  question needs.

---

## Future scope

### Phase 1 — Data foundation and validation
- Ingestion from official MPLADS data sources with schema mapping and
  reconciliation against sanction orders
- Threshold recalibration against observed distributions per work type and per
  state, replacing the fixed values used here
- Audit logging, role separation and officer authentication
- Reviewer feedback capture on each signal, so false positives are recorded
  rather than repeatedly re-raised

### Phase 2 — Broader signals and workflow
- Vendor and payment-pattern analysis across works, including concentration and
  sequencing checks
- Case management: assignment, status tracking and closure with recorded reasons
- Geo-tagged site evidence attached to a work and compared against recorded
  progress
- Cross-constituency and cross-agency comparison of similar work types at
  comparable cost

### Phase 3 — Learning from outcomes
- Supervised calibration against verified outcomes, once enough reviewed cases
  exist to learn from — retaining the explainable additive breakdown as the
  presented rationale
- Early-warning scoring at the sanction stage rather than after expenditure
- Public transparency views with appropriate aggregation and disclosure controls
- Integration with existing audit and monitoring workflows rather than a
  parallel system

---

## API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service and database status |
| `GET` | `/api` | Endpoint index |
| `GET` | `/api/projects` | All works with computed scores; `search`, `risk_level`, `district`, `agency`, `sort`, `limit` |
| `GET` | `/api/projects/{id}` | One work with payments and full analysis |
| `POST` | `/api/projects/{id}/analyze` | Run the full pipeline (the "Analyze Risk" button) |
| `GET` | `/api/projects/{id}/analyze` | Same result, linkable |
| `GET` | `/api/projects/{id}/anomalies` | Detected signals only |
| `GET` | `/api/projects/{id}/similar` | Textually and geographically comparable works |
| `GET` | `/api/projects/{id}/nearby` | Works within a radius, by `radius_km` |
| `GET` | `/api/dashboard/stats` | Headline counts, risk distribution, signal breakdown |
| `GET` | `/api/investigation-queue` | Prioritised worklist, risk descending |
| `GET` | `/api/agencies` | Risk aggregated by implementing agency |
| `GET` | `/api/methodology` | All weights, bands and thresholds the engine applies |

---

## Legal notice

NIRIKSHAN AI is a decision-support system. It reports statistical and rule-based
risk signals for prioritisation only. It does not establish irregularity,
misappropriation or wrongdoing of any kind. All findings require verification
against source records, and the determination rests with the authorised officer.

This prototype uses synthetic MPLADS-style demonstration data and does not
represent official government records. MP names, agency names and village names
in the dataset are fictitious.
