import DataNotice from '../components/DataNotice'
import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { riskStyle } from '../utils/format'

/**
 * Method, scope and future work.
 *
 * The scoring rules are published here rather than described loosely, and they
 * are read from the backend so this page cannot drift out of sync with what the
 * engine actually applies.
 */
export default function About() {
  const { data, error, loading, reload } = useApi((opts) => api.methodology(opts), [])

  return (
    <div className="max-w-4xl space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">About this prototype</h2>
        <p className="mt-0.5 text-[13px] text-ink-500">
          What the system does, how it scores, and what it deliberately does not claim.
        </p>
      </div>

      <DataNotice variant="block" />

      {/* Purpose ---------------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Purpose and scope</h3>
        </div>
        <div className="space-y-3 p-4 text-[13px] leading-relaxed text-ink-700">
          <p>
            MPLADS works are numerous, geographically dispersed and reviewed by a small number of
            officers. Reviewing every record with equal attention is not feasible, so problems
            surface late — often after funds have been released. This prototype addresses the
            triage problem: given a register of works, which ones warrant a closer look first, and
            on what specific grounds?
          </p>
          <p>
            It reads the recorded fields of each work, applies deterministic checks to them, and
            combines the results into a single 0–100 score with a full account of how that score was
            reached. Everything it reports is derived from values already present in the record.
          </p>
          <div className="rounded border border-ink-300 bg-ink-50 px-3 py-2.5">
            <div className="label mb-1">What this system does not do</div>
            <p>
              It does not establish irregularity, misappropriation or wrongdoing of any kind, and it
              produces no finding of fraud. A high score means the recorded values match a pattern
              worth verifying — nothing more. Signals can have entirely legitimate explanations: a
              cost overrun may have an approved revision that is not in the dataset, and two similar
              works may be genuinely distinct assets. Every determination rests with the authorised
              officer reviewing the source records.
            </p>
          </div>
        </div>
      </section>

      {/* Method ---------------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Detection method</h3>
        </div>
        <div className="divide-y divide-ink-100">
          {DETECTORS.map((d) => (
            <div key={d.name} className="p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-[13px] font-semibold text-ink-800">{d.name}</span>
                <span className="tnum text-2xs font-semibold text-ink-500">
                  max {d.weight} points
                </span>
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-ink-600">{d.detail}</p>
              {d.formula && (
                <pre className="mt-2 overflow-x-auto rounded border border-ink-200 bg-ink-50 px-2.5 py-1.5 text-2xs text-ink-700">
                  {d.formula}
                </pre>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Scoring -------------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Scoring rules</h3>
          <span className="text-2xs text-ink-500">Read live from the engine</span>
        </div>

        {loading && <LoadingPanel label="Loading methodology…" rows={4} />}
        {error && (
          <div className="p-4">
            <ErrorPanel error={error} onRetry={reload} context="GET /api/methodology" />
          </div>
        )}

        {data && (
          <div className="space-y-4 p-4">
            <div>
              <div className="label mb-1.5">Fusion formula</div>
              <pre className="overflow-x-auto rounded border border-ink-200 bg-ink-50 px-3 py-2 text-2xs text-ink-800">
                {data.formula}
              </pre>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-600">{data.note}</p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-600">
                The fusion is additive and linear on purpose. A reviewer can read the breakdown on a
                project page and reconstruct the total by hand; a non-linear or learned combination
                would score better on paper and be far harder to defend in a file.
              </p>
            </div>

            <div>
              <div className="label mb-1.5">Risk bands</div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {data.bands.map((band) => {
                  const style = riskStyle(band.level)
                  return (
                    <div
                      key={band.level}
                      className={`rounded border px-3 py-2 ${style.bg} ${style.border}`}
                    >
                      <div className={`text-2xs font-bold uppercase tracking-wide ${style.text}`}>
                        {band.level}
                      </div>
                      <div className="tnum mt-0.5 text-[13px] text-ink-700">
                        {band.min}–{band.max}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div>
              <div className="label mb-1.5">Thresholds applied</div>
              <div className="overflow-x-auto rounded border border-ink-200">
                <table className="w-full border-collapse">
                  <tbody className="divide-y divide-ink-100">
                    {Object.entries(data.thresholds).map(([key, value]) => (
                      <tr key={key}>
                        <td className="px-3 py-1.5 text-[13px] text-ink-600">
                          {key.replace(/_/g, ' ')}
                        </td>
                        <td className="tnum px-3 py-1.5 text-right text-[13px] font-semibold text-ink-800">
                          {value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Limitations ---------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Known limitations</h3>
        </div>
        <ul className="divide-y divide-ink-100">
          {LIMITATIONS.map((item) => (
            <li key={item} className="px-4 py-2.5 text-[13px] leading-relaxed text-ink-700">
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Future scope --------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Future scope</h3>
        </div>
        <div className="divide-y divide-ink-100">
          {PHASES.map((phase) => (
            <div key={phase.name} className="p-4">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="rounded bg-ink-800 px-2 py-0.5 text-2xs font-bold uppercase tracking-wide text-white">
                  {phase.name}
                </span>
                <span className="text-[13px] font-semibold text-ink-800">{phase.title}</span>
              </div>
              <ul className="mt-2 space-y-1">
                {phase.items.map((item) => (
                  <li key={item} className="flex gap-2 text-[13px] leading-relaxed text-ink-600">
                    <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ink-400" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Stack ---------------------------------------------------------- */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Implementation</h3>
        </div>
        <div className="space-y-2 p-4 text-[13px] leading-relaxed text-ink-700">
          <p>
            <span className="font-semibold">Frontend:</span> React 18, Vite, Tailwind CSS, React
            Router, Recharts.{' '}
            <span className="font-semibold">Backend:</span> FastAPI, SQLAlchemy, SQLite.{' '}
            <span className="font-semibold">Analysis:</span> a standalone{' '}
            <code className="rounded bg-ink-100 px-1 py-0.5 text-2xs">anomaly_engine</code> package
            operating on plain dictionaries, with NumPy for the TF-IDF and cosine-similarity
            arithmetic.
          </p>
          <p>
            The engine has no dependency on the web framework or the database, so the same code can
            be unit-tested directly or pointed at a different data source. Risk scores are never
            stored — every figure in this interface is computed on request.
          </p>
        </div>
      </section>
    </div>
  )
}

const DETECTORS = [
  {
    name: 'Cost anomaly',
    weight: 25,
    detail:
      'Compares recorded expenditure against the sanctioned amount. Deviation within tolerance is ignored; severity then scales up to the full-severity threshold.',
    formula: 'cost_deviation_pct = (actual_expenditure − sanctioned_cost) / sanctioned_cost × 100',
  },
  {
    name: 'Progress mismatch',
    weight: 25,
    detail:
      'Compares financial progress against physical progress. Money moving materially ahead of work is the signal; the reverse is not penalised.',
    formula: 'gap_pp = financial_progress − physical_progress',
  },
  {
    name: 'Delay risk',
    weight: 20,
    detail:
      'Two tests, whichever is worse: whether the work is past its expected completion date, and how far physical progress trails a straight-line schedule between start and expected completion. Completed works are skipped.',
    formula:
      'expected_progress = elapsed_days / total_days × 100\nschedule_deficit_pp = expected_progress − physical_progress',
  },
  {
    name: 'Potential duplicate or overlapping work',
    weight: 20,
    detail:
      'TF-IDF vectors over project name, description and work type, compared by cosine similarity, and only raised when the works are also co-located — same village or within the distance threshold by great-circle distance. Location words are excluded from the text so that works in the same district do not appear similar merely for being in the same district.',
    formula: 'similarity = cosine(tfidf(work_a), tfidf(work_b))   AND   same_village OR distance ≤ threshold',
  },
  {
    name: 'Data quality',
    weight: 10,
    detail:
      'Field completeness, value ranges and date sequencing. A record that cannot be trusted cannot be assessed reliably, so its quality is scored as a signal in its own right rather than being silently ignored.',
  },
]

const LIMITATIONS = [
  'The dataset is synthetic. Thresholds are calibrated against invented records and would need recalibration against real distributions before any operational use.',
  'Duplicate detection compares text and location only. It cannot distinguish a genuine duplicate sanction from two legitimately distinct works that happen to be described in similar words at nearby sites — which is why it reports a verification prompt rather than a finding.',
  'Delay assessment assumes progress accrues in a straight line between the start and expected completion dates. Real works are seasonal and lumpy, so an early-stage work can appear behind schedule when it is not.',
  'A missing field cannot be distinguished from a field that is genuinely not applicable. Both reduce the data quality score.',
  'Scores are comparable within this dataset only. A score of 60 is not an absolute measure of anything.',
  'Authentication is a demonstration identity switcher, not a login. Role-based scoping and the audit trail are real and enforced on the server, but anyone can select any role — the prototype demonstrates what the controls do, not the identity assurance a deployed system would need.',
  'On the hosted deployment the database is written to temporary storage, so cases, verification marks and audit entries created there do not survive a cold start. Run the prototype locally for case work that needs to persist.',
  'No trained machine-learning model is used anywhere. Every score, similarity figure and indicator on these screens is arithmetic over the recorded fields, which is why each one can be shown in full.',
  'The prototype has been exercised against 26 records. No benchmark has been run at larger volumes, so no claim is made about its behaviour on a full national register.',
]

const PHASES = [
  {
    name: 'Phase 1',
    title: 'Data foundation and validation',
    items: [
      'Ingestion from official MPLADS data sources with schema mapping and reconciliation against sanction orders',
      'Threshold recalibration against observed distributions per work type and per state, replacing the fixed values used here',
      'Audit logging, role separation and officer authentication',
      'Reviewer feedback capture on each signal, so false positives are recorded rather than repeatedly re-raised',
    ],
  },
  {
    name: 'Phase 2',
    title: 'Broader signals and workflow',
    items: [
      'Vendor and payment-pattern analysis across works, including concentration and sequencing checks',
      'Case management: assignment, status tracking and closure with recorded reasons',
      'Geo-tagged site evidence attached to a work and compared against recorded progress',
      'Cross-constituency and cross-agency comparison of similar work types at comparable cost',
    ],
  },
  {
    name: 'Phase 3',
    title: 'Learning from outcomes',
    items: [
      'Supervised calibration against verified outcomes, once enough reviewed cases exist to learn from — retaining the explainable additive breakdown as the presented rationale',
      'Early-warning scoring at the sanction stage rather than after expenditure',
      'Public transparency views with appropriate aggregation and disclosure controls',
      'Integration with existing audit and monitoring workflows rather than a parallel system',
    ],
  },
]
