import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { riskStyle, rupeesShort } from '../utils/format'

/**
 * Risk composition by sanction period.
 *
 * This is deliberately *not* labelled a risk trend. The register holds one
 * current snapshot per work and no history of past scores, so there is no time
 * series of risk rising or falling to plot. What can honestly be shown is:
 * works are grouped by the quarter they were sanctioned in, and each group is
 * scored as it stands today.
 *
 * A chart that implied "risk is falling quarter on quarter" would be inventing
 * a history the data does not contain, so the page states its own basis in the
 * heading rather than burying it in a footnote.
 */

const SIGNAL_COLOURS = {
  COST_ANOMALY: '#b91c1c',
  PROGRESS_MISMATCH: '#c2410c',
  DELAY_RISK: '#a16207',
  POTENTIAL_DUPLICATE: '#1d4ed8',
  DATA_QUALITY: '#6b7280',
}

export default function Trends() {
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi((opts) => api.trends(opts), [roleKey])

  if (loading) return <LoadingPanel label="Grouping works by sanction period…" rows={8} />
  if (error) return <ErrorPanel error={error} onRetry={reload} context="GET /api/trends" />

  const series = data.series || []
  const signalSeries = data.signal_series || []
  const signalTotals = data.signal_totals || []

  const maxAvg = Math.max(1, ...series.map((s) => s.average_risk_score))
  const maxProjects = Math.max(1, ...series.map((s) => s.projects))
  const maxSignal = Math.max(
    1,
    ...signalSeries.flatMap((s) => (s.points || []).map((p) => p.count)),
  )

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">
          Risk composition by sanction period
        </h2>
        <p className="mt-0.5 max-w-3xl text-[13px] leading-relaxed text-ink-500">
          Works grouped by the quarter they were sanctioned in, each group scored as it stands
          today. Read it as &ldquo;how do works sanctioned in each period look now&rdquo; — not as
          risk rising or falling over time, which this data cannot show.
        </p>
      </div>

      {series.length === 0 ? (
        <section className="panel px-4 py-8 text-center">
          <p className="text-[13px] text-ink-600">
            No work in scope carries a sanction date, so there is nothing to group by period.
          </p>
        </section>
      ) : (
        <>
          {/* ---------------------------------------------- per-period bars */}
          <section className="panel overflow-hidden">
            <div className="panel-header">
              <h3 className="panel-title">Mean risk score of each sanction cohort</h3>
              <span className="tnum text-2xs text-ink-500">
                {data.periods} period{data.periods === 1 ? '' : 's'}
                {data.scope ? ` · Scope: ${data.scope}` : ''}
              </span>
            </div>

            <div className="space-y-3 p-4">
              {series.map((row) => {
                const style = riskStyle(
                  row.average_risk_score >= 75
                    ? 'CRITICAL'
                    : row.average_risk_score >= 50
                      ? 'HIGH'
                      : row.average_risk_score >= 25
                        ? 'MEDIUM'
                        : 'LOW',
                )
                return (
                  <div key={row.period}>
                    <div className="flex flex-wrap items-baseline gap-x-3">
                      <span className="tnum w-20 shrink-0 text-[13px] font-semibold text-ink-800">
                        {row.period}
                      </span>
                      <span className="tnum text-2xs text-ink-500">
                        {row.projects} work{row.projects === 1 ? '' : 's'} ·{' '}
                        {rupeesShort(row.sanctioned_cost)} sanctioned
                      </span>
                      <span className="ml-auto flex items-baseline gap-2">
                        <span className="tnum text-2xs text-ink-500">
                          highest {Math.round(row.max_risk_score)}
                        </span>
                        <span className={`tnum text-[15px] font-bold ${style.text}`}>
                          {row.average_risk_score}
                        </span>
                      </span>
                    </div>

                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-100">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(row.average_risk_score / maxAvg) * 100}%`,
                            backgroundColor: style.hex,
                          }}
                        />
                      </div>
                      <span className="w-28 shrink-0 text-right text-2xs text-ink-500">
                        {row.critical > 0 && (
                          <span className="font-semibold text-risk-critical">
                            {row.critical} critical
                          </span>
                        )}
                        {row.critical > 0 && row.high_risk > row.critical && ' · '}
                        {row.high_risk > row.critical && (
                          <span className="text-risk-high">
                            {row.high_risk - row.critical} high
                          </span>
                        )}
                        {row.high_risk === 0 && <span className="text-ink-400">none high</span>}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>

            <p className="border-t border-ink-200 px-4 py-2 text-2xs text-ink-500">
              Cohort sizes range from {Math.min(...series.map((s) => s.projects))} to {maxProjects}{' '}
              works. A mean over a handful of records moves sharply with one work and should not be
              read as a rate.
            </p>
          </section>

          {/* ---------------------------------------------- signal mix grid */}
          <section className="panel overflow-hidden">
            <div className="panel-header">
              <h3 className="panel-title">Signal mix per period</h3>
              <span className="text-2xs text-ink-500">
                Count of each signal raised on works sanctioned in that quarter
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <th className="th">Signal</th>
                    {series.map((row) => (
                      <th key={row.period} className="th tnum text-right">
                        {row.period}
                      </th>
                    ))}
                    <th className="th tnum text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {signalSeries.map((signal) => {
                    const total = (signal.points || []).reduce((sum, p) => sum + p.count, 0)
                    return (
                      <tr key={signal.type} className="transition-colors hover:bg-ink-50">
                        <td className="td whitespace-nowrap">
                          <span className="flex items-center gap-2">
                            <span
                              aria-hidden
                              className="h-2 w-2 shrink-0 rounded-sm"
                              style={{ backgroundColor: SIGNAL_COLOURS[signal.type] || '#6b7280' }}
                            />
                            <span className="text-[13px] font-semibold text-ink-800">
                              {signal.title}
                            </span>
                          </span>
                        </td>
                        {(signal.points || []).map((point) => (
                          <td key={point.period} className="td text-right">
                            {point.count === 0 ? (
                              <span className="text-2xs text-ink-300">—</span>
                            ) : (
                              <span className="inline-flex items-center justify-end gap-1.5">
                                <span
                                  aria-hidden
                                  className="inline-block h-1.5 rounded-full"
                                  style={{
                                    width: `${Math.max(6, (point.count / maxSignal) * 40)}px`,
                                    backgroundColor: SIGNAL_COLOURS[signal.type] || '#6b7280',
                                  }}
                                />
                                <span className="tnum text-[13px] font-semibold text-ink-700">
                                  {point.count}
                                </span>
                              </span>
                            )}
                          </td>
                        ))}
                        <td className="td tnum text-right text-[13px] font-bold text-ink-900">
                          {total}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* ---------------------------------------------- totals */}
          <section className="panel overflow-hidden">
            <div className="panel-header">
              <h3 className="panel-title">Signals across every period</h3>
              <span className="text-2xs text-ink-500">Most frequent first</span>
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
              {signalTotals.map((signal) => (
                <div key={signal.type} className="rounded border border-ink-200 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13px] font-semibold text-ink-800">{signal.title}</span>
                    <span className="tnum text-lg font-bold leading-none text-ink-900">
                      {signal.count}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink-100">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${
                          (signal.count / Math.max(1, ...signalTotals.map((s) => s.count))) * 100
                        }%`,
                        backgroundColor: SIGNAL_COLOURS[signal.type] || '#6b7280',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      <section className="panel px-4 py-3">
        <div className="label">Basis</div>
        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-700">{data.basis}</p>
        {data.projects_without_sanction_date > 0 && (
          <p className="mt-1.5 text-2xs text-ink-500">
            {data.projects_without_sanction_date} work
            {data.projects_without_sanction_date === 1 ? '' : 's'} in scope carry no sanction date
            and are excluded from every period above rather than being assigned to one.
          </p>
        )}
      </section>

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
    </div>
  )
}
