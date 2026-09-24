import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { orDash, riskStyle } from '../utils/format'

/**
 * The compliance monitor.
 *
 * Each check compares one record against a timeline or a completeness level the
 * register itself implies — a sanction dated before its own recommendation, an
 * expenditure recorded with no payment behind it, a mandatory field left empty.
 * Every grade states the fields it was derived from, because a grade nobody can
 * trace is not a finding, it is an assertion.
 *
 * "Requires review" is a statement about the record, not about the agency that
 * filed it or the officer who approved it.
 */

const STATUS_STYLES = {
  COMPLIANT: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  WATCH: 'bg-amber-50 text-amber-800 border-amber-200',
  'REQUIRES REVIEW': 'bg-red-50 text-red-800 border-red-200',
}

function ComplianceBadge({ status }) {
  const style = STATUS_STYLES[status] || 'bg-ink-100 text-ink-700 border-ink-200'
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded border px-1.5 py-0.5 text-2xs font-bold uppercase tracking-wide ${style}`}
    >
      {status}
    </span>
  )
}

export default function Compliance() {
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi((opts) => api.compliance(opts), [roleKey])
  const [expanded, setExpanded] = useState(null)

  if (loading) return <LoadingPanel label="Running compliance checks…" rows={8} />
  if (error) return <ErrorPanel error={error} onRetry={reload} context="GET /api/compliance" />

  const projects = data.projects || []
  const counts = data.counts || []
  const byCheck = data.by_check || []

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">Compliance monitor</h2>
        <p className="mt-0.5 max-w-3xl text-[13px] leading-relaxed text-ink-500">
          Every work graded against the timelines and completeness its own record implies. A grade of
          &ldquo;requires review&rdquo; means the record cannot be reconciled as it stands — it is a
          statement about the record, not a finding against any person or agency.
        </p>
      </div>

      {/* -------------------------------------------------- grade summary */}
      <div className="grid gap-3 sm:grid-cols-3">
        {counts.map((c) => (
          <div key={c.status} className="panel px-4 py-3">
            <div className="flex items-center justify-between">
              <ComplianceBadge status={c.status} />
              <span className="tnum text-xl font-bold leading-none text-ink-900">{c.count}</span>
            </div>
            <div className="mt-1.5 text-2xs text-ink-500">
              {c.status === 'COMPLIANT'
                ? 'Record reconciles on every check'
                : c.status === 'WATCH'
                  ? 'One or more checks worth a look'
                  : 'At least one check cannot be reconciled'}
            </div>
          </div>
        ))}
      </div>

      {/* -------------------------------------------------- systemic view */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Checks across the register</h3>
          <span className="text-2xs text-ink-500">
            Which checks fail most often · {data.total} works
            {data.scope ? ` · Scope: ${data.scope}` : ''}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="th">Check</th>
                <th className="th text-right">Requires review</th>
                <th className="th text-right">Watch</th>
                <th className="th text-right">Compliant</th>
                <th className="th w-40">Distribution</th>
              </tr>
            </thead>
            <tbody>
              {byCheck.map((b) => {
                const total = b.review + b.watch + b.compliant || 1
                return (
                  <tr key={b.check} className="transition-colors hover:bg-ink-50">
                    <td className="td text-[13px] font-semibold text-ink-800">{b.check}</td>
                    <td className="td tnum text-right text-[13px]">
                      {b.review > 0 ? (
                        <span className="font-semibold text-red-700">{b.review}</span>
                      ) : (
                        <span className="text-ink-400">0</span>
                      )}
                    </td>
                    <td className="td tnum text-right text-[13px]">
                      {b.watch > 0 ? (
                        <span className="font-semibold text-amber-700">{b.watch}</span>
                      ) : (
                        <span className="text-ink-400">0</span>
                      )}
                    </td>
                    <td className="td tnum text-right text-[13px] text-ink-600">{b.compliant}</td>
                    <td className="td">
                      <div className="flex h-1.5 w-36 overflow-hidden rounded-full bg-ink-100">
                        <div
                          className="h-full bg-red-600"
                          style={{ width: `${(b.review / total) * 100}%` }}
                        />
                        <div
                          className="h-full bg-amber-500"
                          style={{ width: `${(b.watch / total) * 100}%` }}
                        />
                        <div
                          className="h-full bg-emerald-500"
                          style={{ width: `${(b.compliant / total) * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* -------------------------------------------------- per-work grades */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Grade by work</h3>
          <span className="text-2xs text-ink-500">
            Worst grade first · select a row to see every check
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="th">Project</th>
                <th className="th">Compliance</th>
                <th className="th text-right">Risk score</th>
                <th className="th">Risk level</th>
                <th className="th">District</th>
                <th className="th text-right">Review / watch</th>
                <th className="th w-8" />
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => {
                const style = riskStyle(p.risk_level)
                const open = expanded === p.project_id
                return (
                  <Fragment key={p.project_id}>
                    <tr
                      className="cursor-pointer transition-colors hover:bg-ink-50"
                      onClick={() => setExpanded(open ? null : p.project_id)}
                    >
                      <td className="td max-w-[20rem]">
                        <span className="tnum block text-[13px] font-semibold text-ink-800">
                          {p.project_id}
                        </span>
                        <span className="mt-0.5 line-clamp-1 block text-[13px] text-ink-700">
                          {orDash(p.project_name)}
                        </span>
                      </td>
                      <td className="td">
                        <ComplianceBadge status={p.compliance_status} />
                      </td>
                      <td className="td text-right">
                        <span className={`tnum text-[13px] font-bold ${style.text}`}>
                          {Math.round(p.risk_score)}
                        </span>
                      </td>
                      <td className="td">
                        <RiskBadge level={p.risk_level} size="sm" />
                      </td>
                      <td className="td whitespace-nowrap text-[13px] text-ink-700">
                        {orDash(p.district)}
                      </td>
                      <td className="td tnum whitespace-nowrap text-right text-[13px] text-ink-600">
                        {p.review_count} / {p.watch_count}
                      </td>
                      <td className="td text-center text-2xs text-ink-400">{open ? '▾' : '▸'}</td>
                    </tr>

                    {open && (
                      <tr>
                        <td colSpan={7} className="border-b border-ink-200 bg-ink-50 px-4 py-3">
                          <div className="mb-2 flex items-baseline gap-3">
                            <span className="label">Every check on this record</span>
                            <Link
                              to={`/projects/${p.project_id}`}
                              className="link text-2xs font-semibold"
                            >
                              Open the work →
                            </Link>
                          </div>
                          <ul className="space-y-1.5">
                            {(p.checks || []).map((check) => (
                              <li
                                key={check.check}
                                className="flex flex-wrap items-baseline gap-x-2 rounded border border-ink-200 bg-white px-2.5 py-2"
                              >
                                <ComplianceBadge status={check.status} />
                                <span className="text-[13px] font-semibold text-ink-800">
                                  {check.check}
                                </span>
                                <span className="text-[13px] text-ink-700">{check.detail}</span>
                                <span className="ml-auto text-2xs text-ink-400">
                                  Derived from: {check.basis}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
    </div>
  )
}
