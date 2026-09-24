# NIRIKSHAN AI — Cross-Questioning Preparation Pack

Everything in this document is verified against the actual codebase. Figures are
safe to quote. Read §0 first — it is the part that decides how the rest lands.

---

## §0. The three rules of being cross-examined

**1. Never bluff a number.** If you don't know, say *"I'd have to check the
config file — every threshold is in one place."* That answer is stronger than a
wrong figure, and it demonstrates the auditability you're claiming.

**2. Volunteer your limitations before they're found.** Judges are testing
whether you understand your own system. A team that says "26 synthetic records,
here's exactly what that does and doesn't prove" beats a team caught hiding it.
Own it in the first two minutes.

**3. Never say "fraud."** Not once, not casually, not in answer to a leading
question. If a judge says *"so this catches corrupt officials?"* — correct the
frame politely: *"It surfaces patterns that need verification. Whether anything
improper occurred is the officer's determination, not ours."* That single
correction signals government-readiness more than any feature.

---

## §1. Hard numbers — memorise these

| Question | Answer |
|---|---|
| Works in dataset | **26** |
| Risk signals raised | **27** |
| Implementing agencies | **24** |
| Works in investigation queue | **12** |
| Band split | LOW 18 · MEDIUM 5 · HIGH 2 · CRITICAL 1 |
| Detectors | **5** |
| Validation rules | **14** |
| API endpoints | **11** (20 routes total) |
| Source files | **52** |
| Lines of code | **~7,000** |
| Acceptance tests | **96 / 96** |
| UI render tests | **73 / 73** |
| Hero score | **94, CRITICAL, not clamped** |
| Bundle size | 612 kB JS + 23 kB CSS |

**Split by area:** anomaly engine 1,754 lines / 11 modules · backend 1,655 / 13 ·
frontend 2,810 / 24 · tooling 780 / 4

---

## §2. The formula — three levels of depth

Have all three ready. Use the shallowest one that satisfies the question.

**Level 1 — one line:**

> Five checks, each worth a fixed share of 100 points. Add the points.

**Level 2 — normalised:**

```
R = 100 × (0.25·C + 0.25·M + 0.20·D + 0.20·P + 0.10·Q)
```
where each term is 0 to 1, and the coefficients sum to 1.00.

**Level 3 — general parameterised form:**

```
R = 100 · Σᵢ wᵢ · clip( (xᵢ − τᵢ) / (φᵢ − τᵢ), 0, 1 )

subject to   Σwᵢ = 1,   wᵢ ≥ 0,   sᵢ ∈ [0,1]
```

Parameters: `θ = { n, w, τ, φ }` — detector count, weights, tolerances,
full-severity thresholds.

**Property worth stating:** because weights sum to 1 and severities cap at 1,
the score is *automatically* bounded to [0,100]. Adding a sixth detector doesn't
inflate scores — the weights re-divide.

### Weights and thresholds

| Detector | Weight | Tolerance (τ) | Full severity (φ) |
|---|---|---|---|
| Cost anomaly | 25 | 5% overrun | 30% overrun |
| Progress mismatch | 25 | 10 pp | 40 pp |
| Delay risk | 20 | 15 pp deficit | 50 pp / 180 days |
| Potential duplicate | 20 | 0.62 similarity | 0.90 similarity |
| Data quality | 10 | — | penalty 40.0 |

Two special rules:
- `s_delay = max(s_overdue, s_deficit)` — whichever is worse.
  Overdue term: `0.5 + 0.5 × min(days_late / 180, 1)`
- `s_duplicate += 0.15` if the two works are within 0.5 km.
  Requires **both** similarity ≥ 0.62 **AND** distance ≤ 3 km.

### Bands

`0–24 LOW · 25–49 MEDIUM · 50–74 HIGH · 75–100 CRITICAL`

### The hero, worked

```
Cost:      (32−5)/(30−5)   = 1.08 → 1.0   →  25 × 1.0  = 25.0
Mismatch:  (41−10)/(40−10) = 1.03 → 1.0   →  25 × 1.0  = 25.0
Delay:     (56−15)/(50−15) = 1.17 → 1.0   →  20 × 1.0  = 20.0
Duplicate: (0.91−0.62)/(0.90−0.62) = 1.04 → 1.0 → 20 × 1.0 = 20.0
Quality:   0.45                            →  10 × 0.45 = 4.5
                                                  TOTAL = 94.5 → 94
```

**MPLAD-2026-024** — Community Hall, Village Rampur, Jaipur, Rajasthan.
₹33,00,000 spent against ₹25,00,000 sanctioned. 82% financial vs 41% physical.
41% complete vs 97% expected. 91% similar to MPLAD-2026-025, 0.41 km away.

---

## §3. The killer questions — with answers

### Q: "Did you just hardcode 94?"

**The single most likely question. Have a three-part answer.**

1. Press **Analyze Risk** live. It's a real `POST` that re-runs validation, all
   five detectors, corpus-wide duplicate detection, and fusion.
2. Show the score arithmetic panel — the five contributions summing on screen.
3. **The clincher:** open MPLAD-2026-020. It scores **24 (LOW)** while its own
   overlap partner MPLAD-2026-019 scores **33 (MEDIUM)** — because 020's progress
   gap is exactly 10 pp and falls *inside* tolerance.

> "That asymmetry is inconvenient for our demo. We left it in because it's proof
> the scores are computed, not assigned. Nobody fakes an inconvenient result."

There is also an automated check: the acceptance suite asserts the hero's score
is derived and `was_clamped = False`.

### Q: "Where's the AI? This is just if-else."

Do **not** get defensive. Reframe.

> "Three answers. First, there is real algorithmic work — TF-IDF vectorisation
> and cosine similarity for duplicate detection, Haversine geodesics for
> co-location. We implemented both from scratch in NumPy rather than importing
> them.
>
> Second, deterministic is a *deliberate* choice for audit. An officer has to
> defend a flag in writing to a superior. `25 + 25 + 20 + 20 + 4.5` is
> defensible; a neural network output is not.
>
> Third, we know exactly where ML goes — and it's not the fusion, it's the
> inputs. Replace TF-IDF with MuRIL embeddings for cross-lingual matching.
> Replace self-reported physical progress with a CV estimate from site photos.
> The formula stays additive; the measurements get smarter."

### Q: "Why not scikit-learn?"

> "Two functions applied to 26 short strings didn't justify pulling in
> scikit-learn plus SciPy — roughly 100 MB into a size-capped serverless bundle.
> We implemented TF-IDF and cosine similarity directly in NumPy, matching
> `TfidfVectorizer`'s defaults exactly: smooth IDF `ln((1+n)/(1+df))+1`, L2 row
> normalisation, token pattern `(?u)\b\w\w+\b`. It's ~40 lines, auditable, and
> we can show the arithmetic."

**This is a strength, not a gap.** Say it as a decision, never apologetically.

### Q: "Your weights are arbitrary. Why 25 and not 30?"

**The best answer is not "we'll learn them later." It's this:**

> "They're expert judgment, documented in one file. But the important question
> is whether that imprecision actually matters — so measure it.
>
> Perturb each weight ±20% and check how much the queue's top-10 reorders
> (Kendall's τ). In additive models with monotone severities, the *ranking* is
> far more robust than the absolute scores. The weights affect the number; they
> barely affect the order — and the order is what an officer acts on.
>
> To make them rigorous without waiting for outcome data, there are two
> established routes: **AHP** — officers fill a pairwise-importance matrix, the
> weights are the principal eigenvector, and the Consistency Ratio (`CR < 0.1`)
> proves the elicitation was coherent. And **entropy weighting**, which is
> label-free — weight each signal by how much it discriminates across the
> corpus, since a signal that fires identically everywhere separates nothing."

If pushed on the ML endpoint: logistic regression first (coefficients *are* the
weights, additivity survives), then GBM with SHAP for global weights and
**monotonic constraints** so more overrun can never lower risk.

### Q: "Isn't your data fake?"

> "It's synthetic, and we say so on every screen. What that does and doesn't
> prove: it does **not** prove the thresholds are calibrated to real MPLADS
> behaviour — they aren't, that needs pilot data. It **does** prove the engine
> works, because the detectors have no knowledge of which records were seeded as
> problematic. They compute from field values. Point the same code at a real
> extract and it runs unchanged — the engine takes plain dictionaries, it has no
> dependency on our schema."

### Q: "What if it flags an honest officer?"

> "That's the case we designed the language around. The system never asserts
> wrongdoing — it says 'potential irregularity', 'requires verification',
> 'priority verification recommended'. Every signal ships with its evidence rows
> and its own verification steps, so the officer is checking a specific claim
> against a specific record, not defending a score.
>
> And the verification worksheet exists precisely for this: the officer ticks
> what they've checked and found explained, and the score recomputes with that
> signal withheld. A legitimate explanation visibly reduces the priority. The
> finding stays on record; it just stops driving the queue."

### Q: "What are the false positives?"

Do not claim a rate — you have no labels, and inventing one is fatal.

> "We can't quote a false-positive rate honestly, because that requires
> confirmed outcomes we don't have. What we can say is where the design pushes
> the tradeoff: tolerances exist specifically to suppress benign variation — 5%
> on cost for rate revisions and rounding, 10 pp on progress for mobilisation
> advances, 15 pp on schedule. And duplicate detection requires text similarity
> **and** geographic proximity together, because either alone produces obvious
> false positives — districts routinely build several comparable assets.
>
> Measuring it properly needs a pilot, and the right metric isn't accuracy —
> it's precision@k, because the output is a ranked worklist and the classes are
> severely imbalanced. Cost-sensitive too: a missed irregularity and a wasted
> site visit cost very different amounts."

### Q: "Does it scale? 26 records is nothing."

Be precise about which part is the bottleneck.

> "Four of five detectors are O(n) — per-record field arithmetic. Duplicate
> detection is the one that doesn't scale naively: it's O(n²) pairwise
> similarity, which is fine at 26 and not fine at a million.
>
> The fix is standard and doesn't change the formula. Block candidates first —
> compare only within a district or a geographic grid cell, since the detector
> already requires proximity ≤ 3 km, so cross-state pairs can never fire. That
> alone cuts the space enormously. Beyond that, approximate nearest-neighbour
> search on the vectors — FAISS or pgvector — turns it into sub-linear lookup.
>
> The other change is SQLite → PostgreSQL, and moving analysis from
> request-time to a batch job with cached scores."

### Q: "Why SQLite? That's not production."

> "Deliberate for a prototype: zero configuration, no credentials, seeds itself
> on first run, and a judge can clone and run it in one command. The ORM is
> SQLAlchemy, so the migration to PostgreSQL is a connection-string change —
> we already read `NIRIKSHAN_DATABASE_URL` from the environment."

### Q: "No authentication?"

> "None — it's Phase 1 on the roadmap. For a real deployment you'd need
> role-based access, since a district officer shouldn't see another district's
> queue, plus an audit log of who viewed and who cleared what. That log is
> arguably more important than the auth itself, because the verification marks
> become accountability records."

### Q: "How does duplicate detection actually work?"

> "Two independent conditions, both required.
>
> Textual: TF-IDF over the work's name, description and type, then cosine
> similarity across the whole corpus. Threshold 0.62 to be reported, full weight
> at 0.90.
>
> Geographic: Haversine great-circle distance between recorded coordinates. Must
> be within 3 km — or the same village. Within 0.5 km adds a 0.15 severity bonus.
>
> Requiring both is the point. High similarity alone flags every road-repair work
> in the state. Proximity alone flags every work in a dense district."

**Follow-up you should expect — "what about different wording?"**

> "That's TF-IDF's real weakness and we'll name it: it's lexical, so 'Community
> Hall' and 'Panchayat Bhavan' score near zero despite being the same thing.
> Fix is a multilingual sentence embedding — MuRIL, which is trained on 17 Indian
> languages — and the formula doesn't change at all. Same cosine, better vectors."

### Q: "What's genuinely novel here?"

> "Not any single detector — cost overrun is obvious. Two things.
>
> First, the cross-record signal. Cost and delay are visible in a single row;
> a diligent officer with a spreadsheet finds those. A near-duplicate is only
> visible by comparing every work against every other work — 325 comparisons at
> 26 records, millions at district scale. That's a class of finding manual review
> structurally cannot produce.
>
> Second, the explanation is the product, not a feature. Every signal carries its
> actual value, expected value, the difference, evidence rows from the record, and
> its own verification checklist. Most risk-scoring tools output a number. A
> number an officer can't act on doesn't get used."

### Q: "How is this different from existing MPLADS monitoring?"

> "Existing portals report *status* — sanctioned, in progress, completed, funds
> released. They answer 'what is happening'. They don't rank by risk, and they
> don't cross-compare records. We're not replacing that reporting layer, we're
> the analysis layer on top of it. The input is exactly the data those portals
> already hold."

### Q: "What happens if the map doesn't load at the venue?"

> "It degrades to a schematic view automatically within six seconds and hides the
> toggle. We tested that path deliberately, because a demo should never open onto
> a blank frame."

*(Actually test this before you present — turn off Wi-Fi and reload.)*

---

## §4. Tech stack — with the reason for each choice

Judges ask "why this and not that." Have a reason, not a preference.

### Backend

| Component | Choice | Why this one |
|---|---|---|
| Language | Python 3.12 | Pinned — 3.14 has no `pydantic-core` wheel |
| API | FastAPI 0.115.6 | Auto-generates OpenAPI/Swagger; async |
| Server | Uvicorn 0.34.0 | Local only; serverless on deploy |
| ORM | SQLAlchemy 2.0.41 | DB-agnostic — SQLite → PostgreSQL is a URL change |
| Validation | Pydantic 2.10.5 | Schema enforced at the boundary, not by hand |
| Numerics | NumPy 2.4.3 | TF-IDF, cosine, Haversine |
| DB | SQLite | Zero-config, self-seeding, one-command demo |

### Frontend

| Component | Choice |
|---|---|
| UI | React 18.3.1 |
| Build | Vite 6.4.3 |
| Routing | React Router 6.30.6 |
| Charts | Recharts 2.15.4 |
| Styling | Tailwind CSS 3.4.19 |
| Maps | Leaflet 1.9.4 + OpenStreetMap (CDN, lazy-loaded) |

**Why Leaflet from CDN and not npm:** keeps it out of the bundle and off the
critical path, and lets the map fail gracefully to the schematic view. A tile
dependency that hard-fails during a demo is worse than no map.

### Algorithms — all implemented from scratch

| Algorithm | Used for |
|---|---|
| TF-IDF | Text vectorisation (matches sklearn defaults) |
| Cosine similarity | Duplicate detection |
| Haversine | Geographic co-location |
| Weighted additive fusion | Risk scoring |
| Linear severity ramps | Per-detector scaling |

### Architecture principle worth stating

> "The anomaly engine is pure logic over plain Python dictionaries — no FastAPI,
> no ORM, no HTTP anywhere in it. It can be lifted into a batch job, a notebook,
> or a different service unchanged. That's what makes the 'point it at real data'
> claim credible rather than aspirational."

### Deployment

Vercel. Frontend is a **prebuilt static bundle** committed to the repo; backend
is a Python serverless function (`api/index.py`) serving the same ASGI app. No
Node build step in the deploy path. FastAPI also serves the built frontend, so
`uvicorn backend.main:app` alone runs the entire prototype.

---

## §5. Future scope — the ML/NLP/CV answer

Structure every answer as: **the formula stays, the inputs improve.**

### NLP

| Now | Next | Catches |
|---|---|---|
| TF-IDF lexical match | **MuRIL / IndicBERT** embeddings | Paraphrase, synonyms, cross-lingual ("Community Hall" ≡ "पंचायत भवन") |
| — | **NER** on descriptions | Contractor / vendor / material extraction → concentration analysis |
| — | **Transliteration normalisation** | Roman-script Hindi vs Devanagari |
| — | **Document parsing** (LayoutLM) on utilisation certificates | Reported vs sanctioned mismatch straight from the PDF |

### Computer Vision

| Application | Method | Feeds |
|---|---|---|
| Physical progress from site photos | CNN stage classifier (foundation → plinth → roof) | Replaces self-reported `physical_progress` in the mismatch term |
| Did the asset get built? | Satellite change detection, before/after sanction | New detector term |
| Photo authenticity | EXIF + geotag + perceptual-hash reuse detection | New detector term — same photo submitted for two works |

**Say this explicitly:** the mismatch detector is currently comparing two
*self-reported* numbers. CV is what makes one of them independent. That's the
single highest-value ML addition, and it's worth naming as such.

### Learned weights

```
Now:      wᵢ  = expert judgment (documented)
Tier 1:   wᵢ  = AHP eigenvector (CR < 0.1) | entropy weighting (label-free)
Tier 2:   wᵢ  = normalised logistic regression coefficients
Tier 3:   wᵢ  = mean |SHAP| , with monotonic constraints
```

SHAP is the key: `R = φ₀ + Σφᵢ` still decomposes per signal, so explainability
survives the move to ML. That's *why* the additive shape is worth preserving.

### Calibration

Turn the ordinal score into a probability via Platt scaling or isotonic
regression; validate with a reliability diagram and Brier score. Target: works
scoring 80 are confirmed irregular ~80% of the time. Also tune τ and φ from the
ROC curve (Youden's J) instead of choosing them.

### The label problem — and your answer to it

Every ML plan above needs confirmed outcomes. You have the collection mechanism
already:

> "The verification worksheet is the label source. Every time an officer ticks
> 'checked and explained', that's a labelled negative for that signal on that
> record. Thousands of those become the training set — and it's active learning
> by construction, because officers work the top of the queue, which is exactly
> where the model is most uncertain."

---

## §6. Limitations — state these before you're asked

| Limitation | Honest framing | Phase |
|---|---|---|
| 26 synthetic records | Proves the engine, not the calibration | 1 |
| Thresholds uncalibrated | Judgment, not measurement — needs pilot data | 2 |
| No authentication | Prototype has no access control | 1 |
| Weights hand-set | Documented, and sensitivity-testable now | 3 |
| Duplicate detection is O(n²) | Fine at 26, needs blocking + ANN at scale | 2 |
| TF-IDF is lexical | Misses paraphrase and cross-lingual duplicates | 2 |
| Mismatch uses self-reported progress | Both inputs are self-declared; CV fixes one | 2 |
| SQLite, single file | Migration is a connection string | 1 |
| No case-management workflow | Flags don't become tracked cases yet | 2 |
| No false-positive rate | Cannot be computed without labels | 2 |

---

## §7. Legal and language — non-negotiable

**Approved vocabulary:** "Potential irregularity" · "High-risk pattern" ·
"Potential duplicate work" · "Requires verification" · "Risk signal detected" ·
"Priority verification recommended"

**Never:** "fraudulent" · "corrupt" · "guilty" · "proven" · "caught" ·
"scam" · "embezzlement"

**Two statements that must appear in the deck verbatim:**

> "This prototype uses synthetic MPLADS-style demonstration data and does not
> represent official government records."

> "The system surfaces risk signals and the evidence behind them. It does not
> establish wrongdoing and does not make decisions. The final determination
> rests with the authorised officer."

**Enforcement:** the acceptance suite includes an automated source scan for
unhedged accusatory language across all 50 source files. Mention this — it shows
the constraint is engineered, not just promised.

**If a judge uses the word "fraud" in their question, correct the frame before
answering.** Every time.

---

## §8. Demo failure playbook

| Failure | Response |
|---|---|
| Deployed site down | Switch to local: `.venv/bin/uvicorn backend.main:app --port 8000` |
| Map tiles won't load | Nothing to do — it self-degrades to the schematic in ~6s |
| Backend won't start | Delete `database/nirikshan.db`; it re-seeds on next start |
| Wrong Python | `.python-version` says 3.12; 3.14 breaks `pydantic-core` |
| Blank dashboard | Check `/api/health` — should report 26 projects |
| Asked for something not built | *"Not in the prototype — it's Phase N."* Never improvise a feature. |

Have the local server **already running** on a second terminal before you walk
up. Your biggest real risk is the venue network, not the code.

---

## §9. One-line answers to keep in your pocket

**What is it?**
> A risk-ranking and explanation layer for MPLADS works — it tells an officer
> which works to verify first, and exactly why.

**What's the innovation?**
> Cross-record duplicate detection, which manual review structurally cannot do,
> plus an explanation an officer can act on rather than just a score.

**Why should a government adopt it?**
> Because it doesn't ask anyone to trust a black box. Every flag decomposes into
> arithmetic the officer can check by hand and defend in writing.

**What's your honest weakness?**
> The thresholds are judgment, not measurement. They need a pilot on real data to
> calibrate — that's Phase 2, and we know how to do it.

**What would you do with 6 more months?**
> Pilot on one district's real extract to calibrate thresholds, add multilingual
> embeddings for duplicate detection, and build the audit log — because the
> verification marks are accountability records, not just UI state.
