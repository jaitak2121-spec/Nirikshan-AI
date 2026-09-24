import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'
import { EmptyState } from './States'
import { orDash, pct, rupeesShort, riskStyle } from '../utils/format'

/**
 * The works register.
 *
 * Rows are links rather than click handlers so a reviewer can open a record in
 * a new tab, and so keyboard navigation works without extra code.
 */
export default function ProjectTable({ projects = [], emptyHint, highlightId }) {
  if (!projects.length) {
    return (
      <EmptyState
        title="No works match the current filters"
        hint={emptyHint || 'Clear the search box or select a different risk band.'}
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="th">Project ID</th>
            <th className="th">Project name</th>
            <th className="th">District</th>
            <th className="th">Implementing agency</th>
            <th className="th text-right">Sanctioned</th>
            <th className="th">Progress (phys / fin)</th>
            <th className="th text-right">Risk score</th>
            <th className="th">Status</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => {
            const style = riskStyle(p.risk_level)
            const isHighlighted = highlightId && p.project_id === highlightId

            return (
              <tr
                key={p.project_id}
                className={`group transition-colors hover:bg-ink-50 ${
                  isHighlighted ? 'bg-risk-criticalBg/40' : ''
                }`}
              >
                <td className="td">
                  <Link
                    to={`/projects/${p.project_id}`}
                    className="tnum text-[13px] font-semibold text-ink-800 group-hover:underline"
                  >
                    {p.project_id}
                  </Link>
                </td>

                <td className="td max-w-[22rem]">
                  <Link to={`/projects/${p.project_id}`} className="block">
                    <span className="line-clamp-2 text-[13px] text-ink-800">
                      {orDash(p.project_name)}
                    </span>
                    {p.anomaly_count > 0 && (
                      <span className="mt-0.5 block text-2xs text-ink-500">{p.primary_risk}</span>
                    )}
                  </Link>
                </td>

                <td className="td whitespace-nowrap text-[13px] text-ink-700">{orDash(p.district)}</td>

                <td className="td max-w-[16rem]">
                  <span className="line-clamp-2 text-[13px] text-ink-700">
                    {orDash(p.implementing_agency)}
                  </span>
                </td>

                <td className="td tnum whitespace-nowrap text-right text-[13px] text-ink-800">
                  {rupeesShort(p.sanctioned_cost)}
                </td>

                <td className="td min-w-[9rem]">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-ink-100">
                      <div
                        className="h-full bg-ink-600"
                        style={{ width: `${Math.max(0, Math.min(100, p.physical_progress ?? 0))}%` }}
                      />
                    </div>
                    <span className="tnum whitespace-nowrap text-2xs text-ink-600">
                      {pct(p.physical_progress)} / {pct(p.financial_progress)}
                    </span>
                  </div>
                </td>

                <td className="td whitespace-nowrap text-right">
                  <div className="flex items-center justify-end gap-2">
                    <span className={`tnum text-[15px] font-bold ${style.text}`}>
                      {Math.round(p.risk_score)}
                    </span>
                    <RiskBadge level={p.risk_level} size="sm" />
                  </div>
                </td>

                <td className="td whitespace-nowrap text-[13px] text-ink-700">{orDash(p.status)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
