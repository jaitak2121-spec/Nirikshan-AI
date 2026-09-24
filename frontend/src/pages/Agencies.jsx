import { Link } from 'react-router-dom'
import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { riskStyle, rupeesShort } from '../utils/format'

/**
 * Risk aggregated by implementing agency.
 *
 * This is arithmetic over the per-work scores — a mean and some counts, not a
 * model of agency behaviour. With only a handful of works per agency in this
 * dataset, an average says more about the individual works than about the
 * agency, and the page says so rather than implying otherwise.
 */
export default function Agencies() {
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi((opts) => api.agencies(opts), [roleKey])

  if (loading) return <LoadingPanel label="Aggregating risk by agency…" rows={8} />
  if (error) return <ErrorPanel error={error} onRetry={reload} context="GET /api/agencies" />

  const agencies = data.agencies || []
  const maxAvg = Math.max(1, ...agencies.map((a) => a.average_risk_score))

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">Agency risk profile</h2>
        <p className="mt-0.5 max-w-3xl text-[13px] leading-relaxed text-ink-500">
          Mean risk score and signal counts per implementing agency, computed from the works recorded
          against each. These are descriptive summaries of a small number of records, not an
          assessment of any agency.
        </p>
      </div>

      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Agencies</h3>
          <span className="tnum text-2xs text-ink-500">
            {data.total} agencies
            {data.scope ? ` · Scope: ${data.scope}` : ''}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="th">Implementing agency</th>
                <th className="th">Districts</th>
                <th className="th text-right">Works</th>
                <th className="th text-right">High risk</th>
                <th className="th text-right">Critical</th>
                <th className="th text-right">Signals</th>
                <th className="th">Mean risk score</th>
                <th className="th text-right">Sanctioned</th>
                <th className="th">Highest-risk work</th>
              </tr>
            </thead>
            <tbody>
              {agencies.map((a) => {
                const style = riskStyle(
                  a.average_risk_score >= 75
                    ? 'CRITICAL'
                    : a.average_risk_score >= 50
                      ? 'HIGH'
                      : a.average_risk_score >= 25
                        ? 'MEDIUM'
                        : 'LOW',
                )

                return (
                  <tr key={a.implementing_agency} className="transition-colors hover:bg-ink-50">
                    <td className="td max-w-[18rem]">
                      <Link
                        to={`/agencies/${encodeURIComponent(a.implementing_agency)}`}
                        className="text-[13px] font-semibold text-ink-800 hover:underline"
                      >
                        {a.implementing_agency}
                      </Link>
                    </td>

                    <td className="td max-w-[10rem] text-[13px] text-ink-600">
                      {a.district_list.join(', ') || '—'}
                    </td>

                    <td className="td tnum text-right text-[13px]">{a.project_count}</td>

                    <td className="td tnum text-right text-[13px]">
                      {a.high_risk_count > 0 ? (
                        <span className="font-semibold text-risk-high">{a.high_risk_count}</span>
                      ) : (
                        <span className="text-ink-400">0</span>
                      )}
                    </td>

                    <td className="td tnum text-right text-[13px]">
                      {a.critical_count > 0 ? (
                        <span className="font-semibold text-risk-critical">{a.critical_count}</span>
                      ) : (
                        <span className="text-ink-400">0</span>
                      )}
                    </td>

                    <td className="td tnum text-right text-[13px] text-ink-700">
                      {a.total_anomalies}
                    </td>

                    <td className="td min-w-[9rem]">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-ink-100">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${(a.average_risk_score / maxAvg) * 100}%`,
                              backgroundColor: style.hex,
                            }}
                          />
                        </div>
                        <span className={`tnum text-[13px] font-semibold ${style.text}`}>
                          {a.average_risk_score}
                        </span>
                      </div>
                    </td>

                    <td className="td tnum whitespace-nowrap text-right text-[13px]">
                      {rupeesShort(a.total_sanctioned_cost)}
                    </td>

                    <td className="td whitespace-nowrap">
                      <Link
                        to={`/projects/${a.highest_risk_project}`}
                        className="tnum text-[13px] text-ink-700 hover:underline"
                      >
                        {a.highest_risk_project}
                      </Link>
                      <span className="tnum ml-1.5 text-2xs text-ink-500">
                        ({Math.round(a.highest_risk_score)})
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="border-t border-ink-200 bg-ink-50 px-4 py-2 text-2xs text-ink-500">
          Select an agency to open its risk profile: signal mix, highest-risk works and any open
          investigations. Agency names in this dataset are fictitious. A mean over two or three
          works is not a statistically meaningful measure of an agency and should not be read as
          one.
        </div>
      </section>

      {data.notice && (
        <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
      )}
    </div>
  )
}
