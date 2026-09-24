import { Fragment, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AnomalyCard from '../components/AnomalyCard'
import EvidenceCard from '../components/EvidenceCard'
import ProgressBar, { ProgressPair } from '../components/ProgressBar'
import RiskBadge from '../components/RiskBadge'
import RiskScore from '../components/RiskScore'
import ProximityMap from '../components/ProximityMap'
import InvestigationNetwork from '../components/InvestigationNetwork'
import Lineage from '../components/Lineage'
import { Disclaimer } from '../components/DataNotice'
import { ErrorPanel, LoadingInline, LoadingPanel, NotFoundPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import useVerification from '../hooks/useVerification'
import { humanDate, orDash, pct, rupees, rupeesShort, riskStyle, signedPct } from '../utils/format'

/**
 * Project record and risk assessment.
 *
 * The page loads with the stored record and the current assessment already
 * present. "Analyze Risk" re-runs the pipeline on the server and replaces the
 * assessment with the fresh result — it is a real round trip, not an animation.
 */
export default function ProjectDetails() {
  const { projectId } = useParams()
  const { data, error, loading, reload } = useApi(
    (opts) => api.project(projectId, opts),
    [projectId],
  )

  // Analysis state is held separately so a re-run can show its own progress and
  // its own failure without discarding the record on screen.
  const [fresh, setFresh] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)
  const [ranAt, setRanAt] = useState(null)

  const runAnalysis = async () => {
    setAnalysing(true)
    setAnalysisError(null)
    try {
      const result = await api.analyze(projectId)
      setFresh(result)
      setRanAt(new Date())
    } catch (err) {
      setAnalysisError(err)
    } finally {
      setAnalysing(false)
    }
  }

  // Derived before the guard clauses below, because the verification state is a
  // hook and hooks must run in the same order on every render.
  const project = data
  const analysis = fresh || project?.analysis || null
  const anomalies = analysis?.anomalies || []

  // One source of truth for "which signals has the officer marked as checked",
  // held here so that a tick on any anomaly moves the headline score, the band
  // and the arithmetic together rather than a figure in an isolated panel.
  const verification = useVerification({
    projectId,
    anomalies,
    baseScore: analysis?.risk_score,
    baseLevel: analysis?.risk_level,
    baseRisk: analysis?.risk,
  })

  if (loading) return <LoadingPanel label={`Loading ${projectId}…`} rows={8} />

  if (error) {
    if (error.status === 404) return <NotFoundPanel what="project" />
    return <ErrorPanel error={error} onRetry={reload} context={`GET /api/projects/${projectId}`} />
  }

  const style = riskStyle(verification.level)
  const explanationFor = (type) => (analysis.explanations || []).find((e) => e.type === type)

  return (
    <div className="space-y-4">
      {/* Breadcrumb ------------------------------------------------------ */}
      <nav className="flex items-center gap-1.5 text-2xs text-ink-500" aria-label="Breadcrumb">
        <Link to="/projects" className="link">
          Works register
        </Link>
        <span aria-hidden>/</span>
        <span className="tnum font-semibold text-ink-700">{project.project_id}</span>
      </nav>

      {/* Record header --------------------------------------------------- */}
      <section className={`panel border-l-4 ${style.border} p-4`} style={{ borderLeftColor: style.hex }}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="tnum rounded bg-ink-100 px-2 py-0.5 text-2xs font-bold text-ink-700">
                {project.project_id}
              </span>
              <RiskBadge level={verification.level} />
              <span className="text-2xs text-ink-500">
                {analysis.anomaly_count} risk signal{analysis.anomaly_count === 1 ? '' : 's'}
              </span>
              {verification.markCount > 0 && (
                <span className="tnum rounded border border-ink-300 bg-white px-1.5 py-0.5 text-2xs font-semibold text-ink-600">
                  {verification.markCount} marked checked · assessed{' '}
                  {String(analysis.risk_level).toUpperCase()}
                </span>
              )}
            </div>

            <h2 className="mt-2 text-lg font-bold leading-snug tracking-tight text-ink-900">
              {orDash(project.project_name)}
            </h2>

            <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-ink-600">
              {project.description || 'No description recorded.'}
            </p>

            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 text-[13px] text-ink-600">
              <span>
                <span className="label mr-1.5">Location</span>
                {orDash(project.location)}
              </span>
              <span>
                <span className="label mr-1.5">District</span>
                {orDash(project.district)}
                {project.state ? `, ${project.state}` : ''}
              </span>
              <span>
                <span className="label mr-1.5">Agency</span>
                {orDash(project.implementing_agency)}
              </span>
            </div>
          </div>

          <div className="w-full max-w-xs shrink-0 space-y-2">
            <RiskScore
              score={verification.score}
              level={verification.level}
              bands={analysis.risk_bands}
              original={analysis.risk_score}
              originalLevel={analysis.risk_level}
              withheld={verification.withheld}
              markCount={verification.markCount}
              pending={verification.busy}
            />

            {verification.markCount > 0 && (
              <button
                type="button"
                className="btn-secondary w-full"
                onClick={verification.reset}
              >
                Clear all verification marks
              </button>
            )}

            {verification.error && (
              <p className="rounded border border-amber-300 bg-amber-50 px-2.5 py-2 text-2xs leading-relaxed text-amber-800">
                {verification.error} The assessed score is shown unchanged.
              </p>
            )}

            <button
              type="button"
              className="btn-primary w-full"
              onClick={runAnalysis}
              disabled={analysing}
            >
              {analysing ? <LoadingInline label="Running analysis…" /> : 'Analyze Risk'}
            </button>

            <p className="text-center text-2xs leading-relaxed text-ink-400">
              {ranAt
                ? `Re-analysed on the server at ${ranAt.toLocaleTimeString()}. Score recomputed from the record.`
                : 'Runs validation, four anomaly detectors, overlap search and risk fusion on the server.'}
            </p>
          </div>
        </div>

        {analysisError && (
          <div className="mt-3">
            <ErrorPanel
              error={analysisError}
              onRetry={runAnalysis}
              context={`POST /api/projects/${projectId}/analyze`}
            />
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Left: the record ------------------------------------------- */}
        <div className="space-y-4 lg:col-span-1">
          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Financials</h3>
            </div>
            <div className="p-4">
              <EvidenceCard
                rows={[
                  { label: 'Estimated cost', value: project.estimated_cost ? rupees(project.estimated_cost) : 'Not recorded', tone: project.estimated_cost ? 'neutral' : 'warn' },
                  { label: 'Sanctioned cost', value: rupees(project.sanctioned_cost) },
                  {
                    label: 'Actual expenditure',
                    value: rupees(project.actual_expenditure),
                    tone:
                      project.actual_expenditure > project.sanctioned_cost ? 'bad' : 'neutral',
                  },
                  {
                    label: 'Variance',
                    value:
                      project.sanctioned_cost
                        ? signedPct(
                            ((project.actual_expenditure - project.sanctioned_cost) /
                              project.sanctioned_cost) *
                              100,
                          )
                        : '—',
                    tone:
                      project.actual_expenditure > project.sanctioned_cost ? 'bad' : 'good',
                  },
                ]}
              />
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Progress</h3>
            </div>
            <div className="p-4">
              <ProgressPair
                physical={project.physical_progress}
                financial={project.financial_progress}
              />
              <div className="mt-3 border-t border-ink-100 pt-3">
                <span className="label mr-2">Status</span>
                <span className="text-[13px] font-semibold text-ink-800">
                  {orDash(project.status)}
                </span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Timeline</h3>
            </div>
            <div className="p-4">
              <EvidenceCard
                rows={[
                  { label: 'Recommended', value: humanDate(project.recommendation_date) },
                  { label: 'Sanctioned', value: humanDate(project.sanction_date) },
                  {
                    label: 'Work started',
                    value: humanDate(project.start_date),
                    tone:
                      project.start_date &&
                      project.sanction_date &&
                      project.start_date < project.sanction_date
                        ? 'bad'
                        : 'neutral',
                  },
                  { label: 'Expected completion', value: humanDate(project.expected_completion_date) },
                  {
                    label: 'Actual completion',
                    value: project.actual_completion_date
                      ? humanDate(project.actual_completion_date)
                      : 'Not completed',
                  },
                ]}
              />
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Record</h3>
            </div>
            <div className="p-4">
              <EvidenceCard
                rows={[
                  { label: 'Work type', value: orDash(project.work_type) },
                  { label: 'Sector', value: orDash(project.sector) },
                  { label: 'Village', value: orDash(project.village) },
                  { label: 'Constituency', value: orDash(project.constituency) },
                  { label: 'Member of Parliament', value: orDash(project.mp_name) },
                  {
                    label: 'Coordinates',
                    value:
                      project.latitude != null && project.longitude != null
                        ? `${project.latitude.toFixed(4)}, ${project.longitude.toFixed(4)}`
                        : 'Not recorded',
                    tone: project.latitude != null ? 'neutral' : 'warn',
                  },
                ]}
                note="MP and agency names in this dataset are fictitious."
              />
            </div>
          </section>

          {project.payments?.length > 0 && (
            <section className="panel overflow-hidden">
              <div className="panel-header">
                <h3 className="panel-title">Payment releases</h3>
                <span className="tnum text-2xs text-ink-500">{project.payments.length} entries</span>
              </div>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <th className="th">#</th>
                    <th className="th">Date</th>
                    <th className="th">Vendor</th>
                    <th className="th text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {project.payments.map((p) => (
                    <tr key={p.transaction_sequence}>
                      <td className="td tnum text-2xs text-ink-500">{p.transaction_sequence}</td>
                      <td className="td whitespace-nowrap text-[13px]">{humanDate(p.payment_date)}</td>
                      <td className="td text-[13px] text-ink-700">{orDash(p.vendor)}</td>
                      <td className="td tnum whitespace-nowrap text-right text-[13px] font-semibold">
                        {rupeesShort(p.payment_amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </div>

        {/* Right: the assessment -------------------------------------- */}
        <div className="space-y-4 lg:col-span-2">
          {/* WHY FLAGGED ------------------------------------------------ */}
          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Why flagged?</h3>
              <span className="tnum text-2xs text-ink-500">
                {analysis.risk.detected_count} of 5 signal families raised
                {verification.markCount > 0 ? ` · ${verification.markCount} checked` : ''}
              </span>
            </div>

            <div className="space-y-3 p-4">
              {anomalies.length === 0 ? (
                <div className="rounded border border-risk-lowBorder bg-risk-lowBg px-3 py-4 text-center">
                  <div className="text-[13px] font-semibold text-risk-low">
                    No risk signal detected
                  </div>
                  <p className="mt-1 text-[13px] text-ink-600">
                    Every check passed within tolerance. The absence of a signal is not a
                    certification that the work is sound — it means nothing in the recorded fields
                    warranted attention.
                  </p>
                </div>
              ) : (
                <>
                  <p className="text-[13px] leading-relaxed text-ink-600">
                    The composite score of{' '}
                    <span className="tnum font-bold">{Math.round(verification.score)}</span>{' '}
                    {verification.active ? (
                      <>
                        is the sum of the contributions below with{' '}
                        {verification.markCount === 1 ? 'one signal' : `${verification.markCount} signals`}{' '}
                        withheld. The assessed score of{' '}
                        <span className="tnum font-bold">{analysis.risk_score}</span> stays on
                        record.
                      </>
                    ) : (
                      <>
                        is the sum of the contributions below. Each is derived from the recorded
                        field values shown as evidence.
                      </>
                    )}
                  </p>

                  <p className="rounded border border-ink-200 bg-ink-50 px-3 py-2 text-[13px] leading-relaxed text-ink-600">
                    Checked a signal and found it explained? Tick it on the signal itself. The score
                    above is recomputed by the engine with that signal withheld, so you can see how
                    much of the total rests on it. Marks are not saved and no finding is removed.
                  </p>

                  {anomalies.map((anomaly, i) => (
                    <AnomalyCard
                      key={anomaly.type}
                      anomaly={anomaly}
                      explanation={explanationFor(anomaly.type)}
                      defaultOpen={i === 0}
                      cleared={verification.isCleared(anomaly.type)}
                      onToggleCleared={verification.toggle}
                    />
                  ))}

                  <ScoreArithmetic
                    risk={verification.risk}
                    assessedScore={analysis.risk_score}
                    withheld={verification.withheld}
                  />

                  <ScoreDrivers drivers={analysis.score_drivers} />
                </>
              )}
            </div>
          </section>

          {/* RECOMMENDED ACTION -------------------------------------- */}
          <RecommendedAction
            recommendation={analysis.recommendation}
            verification={verification}
            assessedScore={analysis.risk_score}
            assessedLevel={analysis.risk_level}
          />

          {/* Comparable works --------------------------------------- */}
          {analysis.similar_projects?.length > 0 && (
            <section className="panel">
              <div className="panel-header">
                <h3 className="panel-title">Comparable works</h3>
                <span className="text-2xs text-ink-500">Requires verification</span>
              </div>
              <div className="space-y-3 p-4">
                <p className="text-[13px] leading-relaxed text-ink-600">
                  Works with similar descriptions in a nearby location. Similarity is a reason to
                  compare records, not evidence that either work is improper — districts routinely
                  build several comparable assets.
                </p>
                {analysis.similar_projects.map((match) => (
                  <SimilarRow key={match.project_id} match={match} />
                ))}
              </div>
            </section>
          )}

          {/* Geography ----------------------------------------------- */}
          <ProximityMap
            origin={project}
            nearby={analysis.nearby_projects || []}
            riskLevel={analysis.risk_level}
          />

          {/* Related records ----------------------------------------- */}
          <InvestigationNetwork projectId={project.project_id} />

          {/* Data quality -------------------------------------------- */}
          <ValidationPanel validation={analysis.validation} />

          {/* Lineage ------------------------------------------------- */}
          <Lineage lineage={analysis.lineage} />

          <Disclaimer text={analysis.disclaimer} />
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

/**
 * The contribution table.
 *
 * Every line of the score is here, and every line opens out into the figures it
 * was derived from — the recorded values, the comparison, and the multiplication
 * that turned them into points. A score an officer cannot take apart is a number
 * they have to trust; a score they can take apart is one they can check.
 */
function ScoreArithmetic({ risk, assessedScore, withheld = 0 }) {
  const anyCleared = risk.breakdown.some((row) => row.cleared)
  const [open, setOpen] = useState(null)

  return (
    <div className="rounded border border-ink-200 bg-ink-50 p-3">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div className="label">How the score was reached</div>
        <div className="text-2xs text-ink-500">Select a contribution to see its evidence</div>
      </div>
      <table className="w-full border-collapse">
        <tbody>
          {risk.breakdown.map((row) => {
            const expanded = open === row.type
            return (
              <Fragment key={row.type}>
                <tr
                  className={`${row.detected ? 'cursor-pointer hover:bg-white' : 'text-ink-400'}`}
                  onClick={row.detected ? () => setOpen(expanded ? null : row.type) : undefined}
                >
                  <td className="py-1 pr-2 text-[13px]">
                    {row.detected && (
                      <span className="mr-1 text-2xs text-ink-400">{expanded ? '▾' : '▸'}</span>
                    )}
                    {row.title}
                    {row.cleared && (
                      <span className="ml-1.5 text-2xs uppercase tracking-wide text-ink-500">
                        checked
                      </span>
                    )}
                  </td>
                  <td className="tnum py-1 pr-2 text-right text-2xs text-ink-500">
                    {row.cleared
                      ? `withheld, was ${row.detected_points.toFixed(1)}`
                      : row.detected
                        ? `${(row.severity_factor * 100).toFixed(0)}% of ${row.max_weight}`
                        : '—'}
                  </td>
                  <td
                    className={`tnum w-14 py-1 text-right text-[13px] font-semibold ${
                      row.cleared ? 'text-ink-400' : ''
                    }`}
                  >
                    {row.detected && !row.cleared ? `+${row.points.toFixed(1)}` : '0'}
                  </td>
                </tr>

                {expanded && (
                  <tr>
                    <td colSpan={3} className="pb-2">
                      <div className="space-y-2 rounded border border-ink-200 bg-white px-3 py-2.5">
                        {row.headline && (
                          <p className="text-[13px] font-semibold leading-snug text-ink-900">
                            {row.headline}
                          </p>
                        )}

                        <div className="grid gap-x-4 gap-y-1.5 sm:grid-cols-3">
                          <ContributionFigure label="Recorded" value={row.actual_value} />
                          <ContributionFigure label="Expected" value={row.expected_value} />
                          <ContributionFigure label="Difference" value={row.difference} strong />
                        </div>

                        {row.reason && (
                          <p className="text-[13px] leading-relaxed text-ink-600">{row.reason}</p>
                        )}

                        {row.evidence?.length > 0 && (
                          <dl className="divide-y divide-ink-100 border-t border-ink-100 pt-1.5">
                            {row.evidence.map((ev) => (
                              <div
                                key={ev.label}
                                className="flex flex-wrap items-baseline justify-between gap-x-3 py-1"
                              >
                                <dt className="text-2xs uppercase tracking-wide text-ink-500">
                                  {ev.label}
                                </dt>
                                <dd
                                  className={`tnum text-[13px] ${
                                    ev.tone === 'bad'
                                      ? 'font-semibold text-ink-900'
                                      : 'text-ink-700'
                                  }`}
                                >
                                  {ev.value}
                                </dd>
                              </div>
                            ))}
                          </dl>
                        )}

                        <p className="tnum rounded bg-ink-50 px-2 py-1 text-2xs text-ink-600">
                          {row.arithmetic}
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
          <tr className="border-t border-ink-300">
            <td className="pt-1.5 text-[13px] font-semibold">Composite score</td>
            <td className="tnum pt-1.5 text-right text-2xs text-ink-500">
              {risk.was_clamped ? `raw ${risk.raw_total}, clamped to 100` : `of ${risk.max_possible}`}
            </td>
            <td className="tnum pt-1.5 text-right text-[15px] font-bold">{risk.risk_score}</td>
          </tr>
          {anyCleared && (
            <tr>
              <td colSpan={3} className="pt-1.5 text-2xs leading-relaxed text-ink-500">
                Assessed score <span className="tnum font-semibold">{assessedScore}</span> less{' '}
                <span className="tnum font-semibold">{Number(withheld).toFixed(1)}</span> points
                withheld against checked signals. Recomputed by the engine, not subtracted in the
                browser — the rows above still add to the total shown.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function ContributionFigure({ label, value, strong = false }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div
        className={`tnum text-[13px] leading-snug ${
          strong ? 'font-semibold text-ink-900' : 'text-ink-700'
        }`}
      >
        {orDash(value)}
      </div>
    </div>
  )
}

/**
 * What the score rests on.
 *
 * Each line is the composite recomputed by the engine with one signal withheld
 * — the same arithmetic, one input removed. It answers "how much of this number
 * is this one finding", which is the first thing an officer asks of a score. It
 * is not a prediction and not a revised assessment: nothing here is stored and
 * no signal has been cleared.
 */
function ScoreDrivers({ drivers }) {
  if (!drivers?.scenarios?.length) return null

  return (
    <div className="rounded border border-ink-200 bg-white p-3">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div className="label">What the score rests on</div>
        <div className="text-2xs text-ink-500">
          Composite recomputed with one signal withheld
        </div>
      </div>

      <ul className="space-y-1.5">
        {drivers.scenarios.map((s) => (
          <li
            key={s.type}
            className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 border-b border-ink-100 pb-1.5 last:border-0 last:pb-0"
          >
            <span className="text-[13px] text-ink-700">
              If <span className="font-semibold text-ink-900">{s.title}</span> were found explained
            </span>
            <span className="tnum text-[13px] text-ink-500">
              {drivers.current_score} → <span className="font-bold text-ink-900">{s.score_without}</span>
            </span>
            <span className="tnum text-2xs text-ink-500">
              −{Number(s.score_drop).toFixed(1)} points
            </span>
            {s.band_changes && (
              <span className="rounded border border-ink-300 bg-ink-50 px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide text-ink-600">
                band would move to {s.level_without}
              </span>
            )}
          </li>
        ))}
      </ul>

      <p className="mt-2 text-2xs leading-relaxed text-ink-500">{drivers.note}</p>
    </div>
  )
}

function RecommendedAction({ recommendation, verification, assessedScore, assessedLevel }) {
  if (!recommendation) return null

  const tone =
    recommendation.priority === 'PRIORITY'
      ? { border: 'border-risk-criticalBorder', bg: 'bg-risk-criticalBg', text: 'text-risk-critical' }
      : recommendation.priority === 'HIGH'
        ? { border: 'border-risk-highBorder', bg: 'bg-risk-highBg', text: 'text-risk-high' }
        : { border: 'border-ink-200', bg: 'bg-ink-50', text: 'text-ink-700' }

  return (
    <section className={`panel ${tone.border}`}>
      <div className={`panel-header ${tone.bg}`}>
        <h3 className="panel-title">Recommended action</h3>
        <span className={`text-2xs font-bold uppercase tracking-wide ${tone.text}`}>
          {recommendation.priority}
        </span>
      </div>

      <div className="space-y-3 p-4">
        {verification?.markCount > 0 && (
          <div className="rounded border border-ink-300 bg-white px-3 py-2 text-[13px] leading-relaxed text-ink-600">
            This priority was derived from the assessed score of{' '}
            <span className="tnum font-semibold">{assessedScore}</span> (
            {String(assessedLevel).toUpperCase()}). With{' '}
            {verification.markCount === 1
              ? 'one signal'
              : `${verification.markCount} signals`}{' '}
            marked checked the provisional score is{' '}
            <span className="tnum font-semibold">{Math.round(verification.score)}</span> (
            {String(verification.level).toUpperCase()}), so the steps below that relate to a checked
            signal can be treated as addressed. Priority is re-derived on the server when the
            analysis is re-run.
          </div>
        )}

        <div>
          <div className={`text-[15px] font-bold ${tone.text}`}>{recommendation.headline}</div>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-600">{recommendation.summary}</p>
        </div>

        {recommendation.checklist?.length > 0 && (
          <div>
            <div className="label mb-2">Verification checklist</div>
            <ul className="space-y-1.5">
              {recommendation.checklist.map((item, i) => (
                <li
                  key={`${item.driver_type}-${i}`}
                  className="flex items-start gap-2.5 rounded border border-ink-200 bg-white px-3 py-2"
                >
                  <span
                    aria-hidden
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-sm border border-ink-400"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] text-ink-800">{item.action}</span>
                    <span className="mt-0.5 block text-2xs text-ink-400">
                      Raised by: {item.driver}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-2xs leading-relaxed text-ink-400">
              This checklist is a suggested starting point for verification. It is not a finding and
              carries no administrative effect.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

function SimilarRow({ match }) {
  return (
    <div className="rounded border border-ink-200 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link to={`/projects/${match.project_id}`} className="tnum text-[13px] font-semibold text-ink-800 hover:underline">
            {match.project_id}
          </Link>
          <div className="mt-0.5 text-[13px] text-ink-700">{match.project_name}</div>
          <div className="mt-1 text-2xs text-ink-500">
            {match.implementing_agency} · {rupeesShort(match.sanctioned_cost)} sanctioned
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="tnum text-lg font-bold text-ink-800">{pct(match.similarity_pct, 0)}</div>
          <div className="text-2xs text-ink-500">text similarity</div>
          {match.distance_km != null && (
            <div className="tnum mt-1 text-2xs text-ink-600">{match.distance_km} km apart</div>
          )}
        </div>
      </div>

      {match.shared_terms?.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-ink-100 pt-2">
          <span className="label mr-1">Shared terms</span>
          {match.shared_terms.map((term) => (
            <span key={term} className="rounded bg-ink-100 px-1.5 py-0.5 text-2xs text-ink-700">
              {term}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function ValidationPanel({ validation }) {
  if (!validation) return null
  const score = validation.data_quality_score

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Record quality</h3>
        <span className="tnum text-2xs text-ink-500">
          {score}/100 · {pct(validation.completeness_pct, 1)} complete
        </span>
      </div>

      <div className="p-4">
        <ProgressBar
          label="Data quality score"
          value={score}
          tone={score >= 90 ? 'neutral' : 'warn'}
        />

        {validation.issues?.length > 0 ? (
          <ul className="mt-3 space-y-1.5">
            {validation.issues.map((issue, i) => (
              <li
                key={`${issue.field}-${i}`}
                className="flex items-start gap-2.5 rounded border border-ink-200 px-3 py-2"
              >
                <span
                  className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-2xs font-semibold uppercase ${riskStyle(issue.severity).border} ${riskStyle(issue.severity).text} ${riskStyle(issue.severity).bg}`}
                >
                  {issue.severity}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px] text-ink-800">{issue.reason}</span>
                  <span className="tnum mt-0.5 block text-2xs text-ink-500">
                    {issue.field}: recorded “{String(issue.actual ?? '—')}”, expected{' '}
                    {String(issue.expected ?? '—')}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[13px] text-ink-600">
            No validation issues found in this record.
          </p>
        )}
      </div>
    </section>
  )
}
