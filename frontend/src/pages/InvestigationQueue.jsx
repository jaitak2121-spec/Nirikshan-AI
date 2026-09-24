import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { CaseOutcomeBadge, CaseStatusBadge } from '../components/CaseStatusBadge'
import { EmptyState, ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { orDash, riskStyle, rupeesShort } from '../utils/format'

/**
 * The prioritised worklist.
 *
 * Ordered by risk score descending — the point of the whole system is to answer
 * "what should be looked at first?" Works with no signal are excluded rather
 * than listed at the bottom, because an empty verification task wastes time.
 *
 * Each row also carries the state of its investigation case, so the queue shows
 * what has already been picked up rather than presenting the same list to every
 * officer every day.
 */
export default function InvestigationQueue() {
  const { roleKey, can } = useRole()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useApi(
    (opts) => api.investigationQueue(opts),
    [roleKey],
  )
  const [opening, setOpening] = useState(null)
  const [actionError, setActionError] = useState(null)

  if (loading) return <LoadingPanel label="Building the investigation queue…" rows={8} />
  if (error)
    return <ErrorPanel error={error} onRetry={reload} context="GET /api/investigation-queue" />

  const items = data.items || []
  const canCreate = can('case.create')

  async function openCase(projectId) {
    setOpening(projectId)
    setActionError(null)
    try {
      const detail = await api.openCase({ project_id: projectId })
      navigate(`/cases/${detail.case_id}`)
    } catch (err) {
      setActionError(err)
      setOpening(null)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">Investigation queue</h2>
        <p className="mt-0.5 max-w-3xl text-[13px] leading-relaxed text-ink-500">
          Works carrying at least one risk signal, ordered highest risk first. This is a suggested
          verification sequence for prioritisation — the order carries no administrative effect and
          no work on this list has been found to be improper.
        </p>
      </div>

      {actionError && (
        <ErrorPanel
          error={actionError}
          onRetry={() => setActionError(null)}
          context="POST /api/cases"
        />
      )}

      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Prioritised worklist</h3>
          <div className="flex items-center gap-3">
            {data.scope && <span className="text-2xs text-ink-500">Scope: {data.scope}</span>}
            <span className="tnum text-2xs text-ink-500">
              {data.total} works with signals
              {data.open_cases > 0 && ` · ${data.open_cases} with a case`}
            </span>
          </div>
        </div>

        {items.length === 0 ? (
          <EmptyState
            title="No works carry a risk signal"
            hint="Every record within your area of responsibility passed all checks within tolerance."
            action={
              <Link to="/projects" className="btn-secondary">
                Open works register
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="th w-14 text-center">Priority</th>
                  <th className="th">Project</th>
                  <th className="th text-right">Risk score</th>
                  <th className="th">Risk level</th>
                  <th className="th">Main risk driver</th>
                  <th className="th">District</th>
                  <th className="th text-right">Sanctioned</th>
                  <th className="th">Investigation</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const style = riskStyle(item.risk_level)
                  return (
                    <tr key={item.project_id} className="group transition-colors hover:bg-ink-50">
                      <td className="td text-center">
                        <span
                          className={`tnum inline-flex h-6 w-6 items-center justify-center rounded-full text-2xs font-bold ${
                            item.priority <= 3 ? 'text-white' : 'bg-ink-100 text-ink-600'
                          }`}
                          style={item.priority <= 3 ? { backgroundColor: style.hex } : undefined}
                        >
                          {item.priority}
                        </span>
                      </td>

                      <td className="td max-w-[22rem]">
                        <Link to={`/projects/${item.project_id}`} className="block">
                          <span className="tnum text-[13px] font-semibold text-ink-800 group-hover:underline">
                            {item.project_id}
                          </span>
                          <span className="mt-0.5 line-clamp-2 block text-[13px] text-ink-700">
                            {orDash(item.project_name)}
                          </span>
                        </Link>
                        <span className="mt-0.5 block truncate text-2xs text-ink-400">
                          {orDash(item.implementing_agency)}
                        </span>
                      </td>

                      <td className="td text-right">
                        <span className={`tnum text-[15px] font-bold ${style.text}`}>
                          {Math.round(item.risk_score)}
                        </span>
                      </td>

                      <td className="td">
                        <RiskBadge level={item.risk_level} size="sm" />
                      </td>

                      <td className="td">
                        <span className="text-[13px] text-ink-700">{item.primary_risk}</span>
                        <span className="mt-0.5 block text-2xs text-ink-400">
                          {item.anomaly_count} signal{item.anomaly_count === 1 ? '' : 's'}
                        </span>
                      </td>

                      <td className="td whitespace-nowrap text-[13px] text-ink-700">
                        {orDash(item.district)}
                      </td>

                      <td className="td tnum whitespace-nowrap text-right text-[13px]">
                        {rupeesShort(item.sanctioned_cost)}
                      </td>

                      <td className="td whitespace-nowrap">
                        {item.case_id ? (
                          <Link to={`/cases/${item.case_id}`} className="block">
                            <CaseStatusBadge status={item.case_status} />
                            <span className="mt-0.5 block text-2xs text-ink-500 group-hover:underline">
                              {item.case_id}
                              {item.case_assigned_to ? ` · ${item.case_assigned_to}` : ''}
                            </span>
                            {item.case_outcome && (
                              <span className="mt-0.5 block">
                                <CaseOutcomeBadge outcome={item.case_outcome} />
                              </span>
                            )}
                          </Link>
                        ) : canCreate ? (
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={opening === item.project_id}
                            onClick={() => openCase(item.project_id)}
                          >
                            {opening === item.project_id ? 'Opening…' : 'Open case'}
                          </button>
                        ) : (
                          <span className="text-2xs text-ink-400">No case opened</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">
        Opening a case starts a verification record against the work. It generates a checklist from
        the signals actually detected and begins an audit trail. It is a request for verification,
        not a finding.
      </p>
    </div>
  )
}
