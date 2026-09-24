# NIRIKSHAN AI — Detailed Tech Stack & Technology Roadmap

Two strictly separated halves. **Part A is built and demonstrable.** **Part B is
roadmap.** Never blur them on a slide — the first question a technical judge asks
is "show me that running," and the answer must always be yes.

---

# PART A — BUILT IN THE PROTOTYPE

## A1. Backend

| Layer | Technology | Version | Role |
|---|---|---|---|
| Language | Python | 3.12 | Pinned via `.python-version` |
| API framework | FastAPI | 0.115.6 | REST endpoints, auto-generated OpenAPI/Swagger |
| ASGI server | Uvicorn | 0.34.0 | Local development server |
| ORM | SQLAlchemy | 2.0.41 | Typed 2.0 declarative mappers |
| Schema validation | Pydantic | 2.10.5 | Request/response contract enforcement |
| Numerics | NumPy | 2.4.3 | Vector maths for TF-IDF, cosine, Haversine |
| Data handling | pandas | 2.2.3 | Tabular operations, seeding |
| Database | SQLite | stdlib | File-based, zero-config, auto-seeded on boot |

## A2. Frontend

| Layer | Technology | Version | Role |
|---|---|---|---|
| UI library | React | 18.3.1 | 6 screens, 24 modules |
| Build tool | Vite | 6.4.3 | Dev server + production bundling |
| Routing | React Router | 6.30.6 | Client-side SPA routing |
| Charts | Recharts | 2.15.4 | Risk distribution, progress bars |
| Styling | Tailwind CSS | 3.4.19 | Utility-first design system |
| CSS pipeline | PostCSS / Autoprefixer | 8.5 / 10.5.2 | Vendor prefixing |
| **GIS mapping** | **Leaflet** | **1.9.4** | **Interactive basemap (CDN-loaded)** |
| **Tiles** | **OpenStreetMap** | — | **Raster basemap tiles** |

## A3. Deployment

| Layer | Technology |
|---|---|
| Host | Vercel |
| Backend runtime | Python serverless function (`api/index.py`) |
| Frontend delivery | Prebuilt static bundle, CDN-served |
| CI/CD | Git push to `main` → automatic deploy |
| Version control | Git / GitHub |

## A4. Algorithms — implemented from scratch

| Algorithm | Category | Used for | Implementation |
|---|---|---|---|
| **TF-IDF vectorisation** | **Classical NLP / IR** | Text representation of work descriptions | Hand-written in NumPy. Smooth IDF `ln((1+n)/(1+df))+1`, L2 row normalisation, token pattern `(?u)\b\w\w+\b` — matches scikit-learn `TfidfVectorizer` defaults |
| **Cosine similarity** | **Vector similarity** | Duplicate/overlap detection | Dot product of L2-normalised vectors |
| **Haversine formula** | **Geospatial** | Great-circle co-location distance | Direct spherical trigonometry |
| **Weighted additive fusion** | **Decision theory** | Risk scoring | `clamp(Σ(wᵢ × severityᵢ), 0, 100)` |
| **Piecewise-linear severity** | **Heuristic scaling** | Converting breach magnitude → severity factor | Linear interpolation between tolerance and full-severity thresholds |
| **Rule-based anomaly detection** | **Expert system** | 5 detector families | Deterministic, threshold-driven |

## A5. What kind of "AI" this actually is — say this precisely

The prototype is a **deterministic, rule-based, explainable risk engine with a
classical NLP component.**

- ✅ **It does contain real NLP.** TF-IDF + cosine similarity is textbook
  statistical natural-language processing / information retrieval. It is not
  neural, but it is genuinely NLP.
- ✅ **It does contain genuine geospatial analysis** — Haversine distance and
  co-location radius logic.
- ❌ **It contains no machine learning.** No training, no labels, no model
  weights, no neural network.
- ❌ **It contains no computer vision.**

**Do not say "AI/ML-powered" in the deep-learning sense.** For an audit context,
"deterministic and explainable" is the *stronger* claim — an officer can
reconstruct `25 + 25 + 20 + 20 + 4.5 = 94.5` by hand and defend it in writing. A
learned score cannot be defended that way.

### Why no ML in the prototype — the two-part answer

1. **Auditability.** Under MPLADS, a flag triggers a verification action against
   a named agency. That must be justifiable in writing to an officer, an auditor,
   and potentially a court. Linear additive weights are inspectable; gradient
   boosting is not.
2. **No labels exist.** Supervised learning needs confirmed outcomes — "this
   work was verified and found irregular." That dataset does not exist yet.
   Building the rule engine *is how you generate those labels*. ML is Phase 3
   because Phase 1 and 2 must produce its training data first.

## A6. Engineering decisions worth a slide

| Decision | Reason |
|---|---|
| scikit-learn deliberately **not** used | Two functions over ~26 short strings did not justify scikit-learn + SciPy. Hand-implementing in NumPy keeps the arithmetic auditable and the serverless bundle small |
| All thresholds in one file (`anomaly_engine/config.py`) | Single auditable source of truth; nothing hidden in detector code |
| Anomaly engine is pure logic over plain dicts | No FastAPI, no ORM, no HTTP imports — portable to a batch job, notebook, or different service unchanged |
| Leaflet loaded from CDN, not npm | Zero bundle growth, and the map degrades to an offline SVG schematic if tiles are unreachable |
| Adjusted score recomputed by the engine, not subtracted in JavaScript | Preserves the rule that no score is ever stored or faked client-side |

## A7. Verified scale

| Metric | Value |
|---|---|
| Source files | 54 |
| Lines of code | ~7,300 |
| Anomaly engine | 1,754 lines / 11 modules |
| Backend API | 1,655 lines / 13 modules |
| Frontend | ~3,000 lines / 26 modules |
| API endpoints | 12 |
| Detector families | 5 |
| Acceptance tests | 96 / 96 passing |
| UI render tests | 73 / 73 passing |

---

# PART B — ROADMAP (NOT BUILT)

Label every one of these **"Planned"** on the slide.

## B1. NLP — Phase 2

This is the **highest-value upgrade**, because it directly strengthens the
prototype's strongest signal (duplicate detection).

| Technology | Purpose | Why it matters for MPLADS |
|---|---|---|
| **Sentence embeddings** — MuRIL, IndicBERT, or multilingual sentence-transformers | Semantic duplicate detection | **The critical gap.** TF-IDF is lexical: it matches shared words. It will catch "Community Hall Rampur" vs "Community Hall, Rampur", but **miss** "Panchayat Bhavan", "समुदाय भवन", or "Village Meeting Hall" describing the same asset. MPLADS descriptions are entered by thousands of officials in many languages and transliterations, so paraphrase and cross-lingual matching is not optional at scale |
| **Transliteration & phonetic matching** — Indic NLP, Soundex/Metaphone variants | Place-name normalisation | "Rampur" / "Rampoor" / "रामपुर" must resolve to one village. Indian place names have no canonical spelling in practice |
| **Named Entity Recognition (NER)** — spaCy, or fine-tuned IndicNER | Structuring free text | Extract asset type, village, beneficiary count, and measurements from unstructured description fields so they become checkable numbers |
| **Approximate nearest neighbour** — FAISS or pgvector (HNSW) | Scaling similarity search | Pairwise comparison is O(n²). 26 works = 325 comparisons. **1 lakh works = 5 billion.** ANN indexing makes this sub-linear. This is a hard scaling blocker, not an optimisation |
| **Text classification** | Auto-tagging work type | Normalise inconsistent free-text categories into a controlled vocabulary |

## B2. Computer Vision — Phase 2 / 3

MPLADS **already mandates geotagged site photographs**, so the input data exists.
This is the most credible CV story available.

| Technology | Purpose | Why it matters |
|---|---|---|
| **Perceptual hashing (pHash / dHash)** | Duplicate-photo detection | Cheap, no training needed, immediately valuable. Detects the same photograph submitted for two different works, or re-used across reporting periods |
| **EXIF geotag verification** | Location cross-check | Compare photo GPS metadata against sanctioned coordinates. A "completed" work photographed 40 km from its sanctioned site is a hard, objective signal |
| **Satellite change detection** — Sentinel-2 (ESA), ISRO Bhuvan / Cartosat | **Ghost-work detection** | Compare imagery before sanction against after claimed completion. A work reporting 100% physical progress with **no observable change on the ground** is the single most serious pattern in public-works monitoring. This is the flagship CV capability |
| **Construction-stage estimation** — CNN classifier (ResNet/EfficientNet) or a vision-language model | Progress cross-validation | Independently estimate physical completion from site photos and compare against the *claimed* physical progress. Directly automates verification of the Progress Mismatch detector |
| **Image tampering / recency checks** | Evidence integrity | Detect edited or stock imagery submitted as site evidence |

## B3. Machine Learning — Phase 3

**Gated on confirmed audit outcomes existing.** State that gate explicitly — it
shows you understand why ML comes last, rather than sounding like you couldn't
build it.

| Technology | Purpose | Note |
|---|---|---|
| **Gradient boosting** — XGBoost / LightGBM | Learn signal weights from confirmed outcomes | Replaces hand-set weights *only once labels exist* |
| **SHAP values** | Preserve explainability | Non-negotiable. Per-feature attribution keeps the score defensible after moving off linear weights. Without SHAP, ML is a regression in auditability |
| **Isolation Forest / Local Outlier Factor** | Unsupervised anomaly detection | Surfaces patterns no hand-written rule anticipated — the known weakness of a rule engine |
| **Graph analytics** — NetworkX, Neo4j, community detection | Collusion-pattern detection | Model agency ↔ contractor ↔ work ↔ location as a network. Repeat clusters and unusual concentration are invisible to per-record analysis |
| **Time-series forecasting** — Prophet / ARIMA | Predictive delay risk | Forecast completion slippage *before* the deadline is breached, shifting the tool from detective to preventive |
| **Human-in-the-loop / active learning** | Continuous improvement | Officer verification outcomes feed back as labels. **The verification worksheet already in the prototype is the UI hook for this** — a real architectural continuity, worth pointing out |

## B4. Infrastructure scale-up — Phase 1 / 2

| Current | Planned | Reason |
|---|---|---|
| SQLite | **PostgreSQL + PostGIS** | Concurrency, and native spatial indexing replaces Haversine-in-Python. `ST_DWithin` on a GiST index instead of a full scan |
| — | **pgvector / FAISS** | Embedding storage and ANN search |
| — | **Redis** | Cache analysis results; scoring a lakh of works per request is not viable |
| In-request scoring | **Celery / Apache Airflow** | Scheduled batch re-scoring as data updates |
| Vercel serverless | **Docker + Kubernetes** | Long-running CV/ML workloads exceed serverless limits |
| None | **OAuth2 / JWT + RBAC** | Officer, auditor, and public roles. Currently no authentication at all |
| None | **Immutable audit log** | Every view and verification action recorded — a legal requirement for this class of system |
| None | **Prometheus + Grafana** | Observability |

## B5. Integration targets — Phase 1

| Source | Purpose |
|---|---|
| **MPLADS e-SAKSHI portal** | Primary work and sanction records |
| **PFMS** | Payment and fund-release reconciliation |
| **GeM** | Procurement cross-reference |
| **ISRO Bhuvan** | Satellite imagery and official basemaps |
| **Survey of India** | Authoritative administrative boundaries |
| **Census / LGD codes** | Canonical village and district identifiers |

---

# PART C — HOW TO PRESENT THIS

## C1. The one-slide summary

> **Built:** A deterministic, fully explainable risk engine — 5 detectors,
> classical NLP (TF-IDF + cosine similarity), geospatial analysis (Haversine),
> and GIS visualisation. Every score reconstructable by hand. 96/96 + 73/73
> tests passing, deployed and live.
>
> **Next:** Semantic NLP (MuRIL embeddings) for cross-lingual duplicate
> detection; computer vision on the geotagged site photos MPLADS already
> mandates, plus satellite change detection for ghost works; and supervised
> learning **once officer verification outcomes provide labels.**

## C2. Answering "why isn't there any ML?"

Do not apologise. Answer in three sentences:

> "Deliberate. A flag here triggers a verification action against a named
> agency, so the score has to be defensible in writing — an officer can
> reconstruct our 94 by hand, which they could not do with a learned model.
> And supervised learning needs confirmed audit outcomes as labels, which don't
> exist yet; this system is how you generate them. Phase 3 adds gradient
> boosting with SHAP attribution, so explainability survives the transition."

## C3. Answering "how would you scale to lakhs of works?"

Name the real blocker — it shows you've thought past the demo:

> "Pairwise similarity is O(n²): 26 works is 325 comparisons, a lakh is 5
> billion. That needs ANN indexing — FAISS or pgvector with HNSW — plus PostGIS
> for spatial filtering and Redis for cached scores. The detector logic itself
> is unchanged; it's pure functions over dictionaries with no database or HTTP
> coupling, so it lifts into a batch pipeline as-is."

## C4. Suggested roadmap slide — three columns

| Phase 1 · Foundation | Phase 2 · Intelligence | Phase 3 · Learning |
|---|---|---|
| e-SAKSHI / PFMS integration | MuRIL semantic embeddings | XGBoost + SHAP |
| PostgreSQL + PostGIS | FAISS / pgvector ANN | Isolation Forest |
| OAuth2 + RBAC | Photo pHash + EXIF checks | Graph collusion detection |
| Audit logging | Satellite change detection | Delay forecasting |
| Data-quality pipeline | NER field extraction | Active learning from officer outcomes |

## C5. What not to claim

- Do not imply embeddings, CV, or ML are running. They are not.
- Do not call TF-IDF "AI" without qualifying it as classical/statistical NLP.
- Do not imply real government data is in use anywhere.
- Do not present satellite change detection as easy — it needs cloud masking,
  co-registration, and a meaningful resolution floor. Say "Phase 2, with ISRO
  Bhuvan or Sentinel-2 imagery," not "we can just diff the pixels."
