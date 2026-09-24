# NIRIKSHAN AI — SIH Presentation Content Pack

Everything here is extracted from the actual codebase. All figures are verified
and safe to put on a slide.

**Project:** NIRIKSHAN AI — MPLADS Risk Intelligence & Investigation Network
**Type:** Decision-support prototype on synthetic data

---

## 1. Tech stack

### Backend

| Component | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.12 | Pinned via `.python-version` |
| API framework | FastAPI | 0.115.6 | Async, auto-generates OpenAPI/Swagger docs |
| ASGI server | Uvicorn | 0.34.0 | Local development only |
| ORM | SQLAlchemy | 2.0.41 | Typed 2.0 declarative style |
| Validation | Pydantic | 2.10.5 | Request/response schema enforcement |
| Numerics | NumPy | 2.4.3 | TF-IDF, cosine similarity, Haversine |
| Data handling | pandas | 2.2.3 | Seed and tabular work |
| Database | SQLite | built-in | Zero-config, file-based, auto-seeded |

### Frontend

| Component | Choice | Version |
|---|---|---|
| UI library | React | 18.3.1 |
| Build tool | Vite | 6.4.3 |
| Routing | React Router | 6.30.6 |
| Charts | Recharts | 2.15.4 |
| Styling | Tailwind CSS | 3.4.19 |
| CSS pipeline | PostCSS + Autoprefixer | 8.5 / 10.5.2 |

### Deployment

| Layer | Choice |
|---|---|
| Host | Vercel |
| Backend runtime | Python serverless function (`api/index.py`) |
| Frontend | Prebuilt static bundle, CDN-served |
| CI trigger | Git push to `main` → auto-deploy |

### Algorithms — implemented from scratch, no ML library

| Algorithm | Used for | Detail |
|---|---|---|
| TF-IDF vectorisation | Text similarity | Hand-written in NumPy. Smooth IDF `ln((1+n)/(1+df))+1`, L2 row normalisation, token pattern `(?u)\b\w\w+\b` — matches scikit-learn's `TfidfVectorizer` defaults |
| Cosine similarity | Duplicate detection | Dot product of L2-normalised vectors |
| Haversine formula | Co-location | Great-circle distance between lat/long pairs |
| Weighted additive fusion | Risk scoring | `clamp(Σ(weightᵢ × severityᵢ), 0, 100)` |

**Slide callout:** scikit-learn was *deliberately* not used. Two functions over
~26 short strings did not justify pulling in scikit-learn + SciPy. Implementing
them directly keeps the arithmetic auditable and the deploy bundle small. This
is an engineering decision, not a gap.

---

## 2. Codebase scale — stat tiles

| Metric | Value |
|---|---|
| Total source files | **52** |
| Total lines of code | **~7,000** |
| Anomaly engine | 1,754 lines / 11 modules |
| Backend API | 1,655 lines / 13 modules |
| Frontend | 2,810 lines / 24 modules |
| Tooling & tests | 780 lines / 4 modules |
| API endpoints | **11** |
| Total routes | 17 |
| Acceptance tests | **96 / 96 passing** |
| UI render tests | **73 / 73 passing** |
| Production bundle | 612 kB JS + 23 kB CSS |

---

## 3. Architecture diagram — infographic spec

Horizontal left-to-right flow, 8 boxes. This is the most important visual in the
deck.

```
┌─────────────┐   ┌────────────┐   ┌─────────────┐   ┌─────────────┐
│  Synthetic  │──▶│ Validation │──▶│   Feature   │──▶│  5 Anomaly  │
│   Dataset   │   │   Layer    │   │ Engineering │   │  Detectors  │
│ 26 works    │   │ schema +   │   │ ratios,     │   │  (parallel) │
│ 24 agencies │   │ integrity  │   │ gaps, dates │   │             │
└─────────────┘   └────────────┘   └─────────────┘   └──────┬──────┘
                                                            │
┌─────────────┐   ┌────────────┐   ┌─────────────┐   ┌──────▼──────┐
│  React UI   │◀──│  FastAPI   │◀──│ Explanation │◀──│    Risk     │
│  6 screens  │   │ 11 REST    │   │   Engine    │   │   Fusion    │
│             │   │ endpoints  │   │ evidence +  │   │  weighted   │
│             │   │            │   │ lineage     │   │  additive   │
└─────────────┘   └────────────┘   └─────────────┘   └─────────────┘
```

**Design note:** the anomaly-detector box should *fan out into five* sub-boxes
and *converge* into risk fusion. That fan-out-fan-in shape is what visually
communicates "parallel independent signals, one combined score."

---

## 4. The five detectors — infographic spec

Best rendered as **five cards in a row**, each with an icon, weight badge, and
one-line trigger.

| # | Detector | Weight | Triggers when | Full severity at |
|---|---|---|---|---|
| A | Cost Anomaly | **25 pts** | Expenditure exceeds sanctioned amount by >5% | +30% overrun |
| B | Progress Mismatch | **25 pts** | Financial progress runs ahead of physical by >10 pp | 40 pp gap |
| C | Delay Risk | **20 pts** | Work lags straight-line schedule by >15 pp | 50 pp deficit, or 180 days overdue |
| D | Potential Duplicate | **20 pts** | TF-IDF cosine ≥ 0.62 **AND** within 3 km | 0.90 similarity |
| E | Data Quality | **10 pts** | Missing fields, impossible dates, inconsistent values | — |
| | **Total** | **100 pts** | | |

**Every threshold lives in one file** — `anomaly_engine/config.py`. Nothing is
hidden inside detector logic. Worth a callout box: *"Single auditable source of
truth for all thresholds."*

### Duplicate detection — sub-thresholds (zoom-in slide)

| Parameter | Value |
|---|---|
| Similarity threshold | 0.62 |
| Similarity for full weight | 0.90 |
| Max co-location distance | 3.0 km |
| "Very close" bonus distance | 0.5 km → +0.15 severity |
| Reporting floor | 0.45 |

### Other thresholds (for an appendix slide)

| Parameter | Value |
|---|---|
| Cost tolerance | 5% |
| Cost full severity | 30% overrun |
| Delay deficit tolerance | 15 pp |
| Delay deficit full severity | 50 pp |
| Overdue full severity | 180 days |
| Overdue base factor | 0.5 |
| Deadline horizon | 90 days |
| Mismatch tolerance | 10 pp |
| Mismatch full severity | 40 pp |

---

## 5. Risk scoring — infographic spec

### Formula

```
risk_score = clamp( Σ (weightᵢ × severity_factorᵢ) , 0 , 100 )
```

### Bands — render as a 4-segment horizontal gauge

| Band | Range | Meaning | Suggested colour |
|---|---|---|---|
| LOW | 0 – 24 | Routine monitoring | Green `#16A34A` |
| MEDIUM | 25 – 49 | Watchlist | Amber `#D97706` |
| HIGH | 50 – 74 | Verification recommended | Orange `#EA580C` |
| CRITICAL | 75 – 100 | Priority verification | Red `#DC2626` |

*(Colours are a recommendation for the deck — match them to the app's actual
badges when you take screenshots.)*

### The hero breakdown — strongest slide in the deck

**MPLAD-2026-024** — Construction of Community Hall, Village Rampur, Jaipur,
Rajasthan

Render as a **stacked horizontal bar** totalling 94, segments labelled:

| Signal | Weight | × Severity | = Points |
|---|---|---|---|
| Cost anomaly — ₹33,00,000 spent vs ₹25,00,000 sanctioned (+32%) | 25 | 1.00 | **25.0** |
| Progress mismatch — 82% financial vs 41% physical (41 pp gap) | 25 | 1.00 | **25.0** |
| Delay risk — 41% complete vs 97% expected (56 pp behind) | 20 | 1.00 | **20.0** |
| Potential duplicate — 91% similarity w/ MPLAD-2026-025, 0.41 km apart | 20 | 1.00 | **20.0** |
| Data quality — 82/100, missing estimated cost, start before sanction | 10 | 0.45 | **4.5** |
| **TOTAL** | | | **94.5 → 94 · CRITICAL** |

Caption: **"Not clamped. Not assigned. Computed."**

---

## 6. Dataset composition — pie / donut

| Band | Count |
|---|---|
| LOW | 18 |
| MEDIUM | 5 |
| HIGH | 2 |
| CRITICAL | 1 |
| **Total works** | **26** |

Other figures: **27 risk signals** · **24 implementing agencies** ·
**12 works in investigation queue**

### The credibility detail

MPLAD-2026-020 scores **24 (LOW)** while its own overlap partner MPLAD-2026-019
scores **33 (MEDIUM)** — because 020's progress gap is exactly 10 pp and falls
inside tolerance. The asymmetry is inconvenient, which is precisely why it
proves the scores are computed rather than assigned. Keep this in reserve for a
technical judge.

---

## 7. API surface — table slide

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/api/health` | Liveness + record count |
| GET | `/api/projects` | All works |
| GET | `/api/projects/{id}` | Single work detail |
| GET | `/api/projects/{id}/similar` | TF-IDF comparable works |
| GET | `/api/projects/{id}/nearby` | Haversine proximity matches |
| **POST** | `/api/projects/{id}/analyze` | **Live full re-analysis** |
| GET | `/api/projects/{id}/anomalies` | Signals for one work |
| GET | `/api/dashboard/stats` | Aggregates + distribution |
| GET | `/api/investigation-queue` | Risk-ranked priority list |
| GET | `/api/agencies` | Agency-level rollup |
| GET | `/api/methodology` | Weights, thresholds, bands |

---

## 8. Screens — 6 UI modules

| Screen | Purpose |
|---|---|
| Dashboard | Aggregate stats + risk distribution chart |
| Investigation Queue | Risk-ranked priority list (the core product) |
| Projects | Searchable full register |
| Project Details | Evidence, signal breakdown, **Analyze Risk** button, map, lineage |
| Agencies | Agency-level risk rollup |
| About | Methodology, weights, synthetic-data notice |

### Anomaly engine modules (11)

`config` · `validation` · `detectors` · `duplicate_detection` ·
`text_similarity` · `risk_engine` · `explanation_engine` · `lineage` ·
`pipeline` · `formatting` · `__init__`

**Slide callout:** the engine is pure logic over plain dictionaries — no
FastAPI, no ORM, no HTTP. It can be lifted into a batch job, a notebook, or a
different service unchanged.

---

## 9. Suggested slide order

| # | Slide | Key visual |
|---|---|---|
| 1 | Title — NIRIKSHAN AI | Logo + tagline |
| 2 | Problem | Manual MPLADS review cannot scale |
| 3 | Solution | One-line + 3 pillars: **Rank · Explain · Trace** |
| 4 | **Architecture** | The 8-box flow diagram |
| 5 | **5 Detectors** | 5 cards with weight badges |
| 6 | Risk Scoring | Formula + 4-band gauge |
| 7 | **Hero case study** | Stacked bar to 94 |
| 8 | **Duplicate detection** | Map with 2 pins, 0.41 km, 91% |
| 9 | Tech stack | Layered stack diagram |
| 10 | Screenshots | Queue + Project Details |
| 11 | Validation | 96/96 + 73/73 test badges |
| 12 | Limitations & Roadmap | Honest 3-phase plan |
| 13 | Legal / Disclaimer | Decision-support framing |

---

## 10. Two statements that must appear verbatim

> **"This prototype uses synthetic MPLADS-style demonstration data and does not
> represent official government records."**

> The system uses language such as *"Potential irregularity"*, *"High-risk
> pattern"*, *"Potential duplicate work"*, *"Requires verification"*,
> *"Priority verification recommended."* It never asserts fraud. **The final
> determination rests with the authorised officer.**

Put the second on its own slide titled **"Decision-support, not accusation."**
It is a differentiator — most teams skip it, and it is the first thing a
government evaluator checks.

---

## 11. What to leave out

- Do not call it AI/ML-powered in the deep-learning sense. It is a
  **deterministic, rule-based, explainable engine** — and that is the *stronger*
  claim for an audit context, because the output is defensible in writing.
- Do not imply real government data anywhere.
- Do not show deployment or dependency troubleshooting — irrelevant to judges.

---

## 12. Known limitations — put these on the roadmap slide

| Limitation | Roadmap phase |
|---|---|
| 26 synthetic records, not real MPLADS extracts | Phase 1 — data foundation |
| No authentication or role-based access | Phase 1 |
| Weights hand-set and documented, not learned | Phase 3 — requires confirmed outcome labels |
| Five detector families only | Phase 2 — broader signals |
| No case-management workflow | Phase 2 |

Stating these yourself reads as rigour. Being caught omitting them reads as the
opposite.
