import { Link, useParams } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { CaseOutcomeBadge, CaseStatusBadge } from '../components/CaseStatusBadge'
import { ErrorPanel, LoadingPanel, NotFoundPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { humanDate, orDash, riskStyle, rupees, rupeesShort } from '../utils/format'

/**
 * One implementing agency's risk profile.
 *
 * Descriptive arithmetic over the works recorded against this agency: a mean,
 * some counts, the signal mix, the highest-risk items and any investigation
 * cases open against them. A high mean does not prove anything about the
 * agency — with two or three works on file it mostly reflects the individual
 * works, and the page says so instead of implying otherwise.
 *
 * The peer comparison is restricted to agencies operating in the same districts,
 * because comparing a municipal body against a state department across the
 * country would not be a comparison at all.
 */
export default function AgencyProfile() {
  const params = useParams()
  // The route is a wildcard: agency names are free text containing spaces and
  // commas, so the name arrives as the splat rather than a single segment.
  const agency = params['*'] || ''
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi(
    (opts) => api.agency(agency, opts),
    [agency, roleKey],
  )

  if (loading) return <LoadingPanel label={`Aggregating works for ${agency}…`} rows={8} />
  if (error?.status === 404)
    return (
      <NotFoundPanel
        what={`agency "${agency}"`}
        backTo="/agencies"
        backLabel="Back to agency list"
      />
    )
  if (error)
    return (
      <ErrorPanel
        error={error}
        onRetry={reload}
        context={`GET /api/agencies/${encodeURIComponent(agency)}`}
      />
    )

  const style = riskStyle(
    data.average_risk_score >= 75
      ? 'CRITICAL'
      : data.average_risk_score >= 50
        ? 'HIGH'
        : data.average_risk_score >= 25
          ? 'MEDIUM'
          : 'LOW',
  )
  const works = data.highest_risk_works || []
  const signals = data.signal_distribution || []
  const activeCases = data.active_cases || []
  const peers = data.peer_agencies || []
  const maxSignal = Math.max(1, ...signals.map((s) => s.count))
  const maxPeer = Math.max(data.average_risk_score, ...peers.map((p) => p.average_risk_score), 1)

  return (
    <div className="space-y-4">
      {/* -------------------------------------------------- header */}
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0">
          <Link to="/agencies" className="link text-2xs font-semibold">
            ← All agencies
          </Link>
          <h2 className="mt-0.5 text-lg font-bold tracking-tight text-ink-900">
            {data.implementing_agency}
          </h2>
          <p className="mt-0.5 text-[13px] text-ink-500">
            {(data.district_list || []).join(', ') || '—'}
            {(data.state_list || []).length > 0 && ` · ${data.state_list.join(', ')}`}
          </p>
        </div>

        <div className="ml-auto text-right">
          <div className="label">Mean risk score</div>
          <div className={`tnum text-2xl font-bold leading-none ${style.text}`}>
            {data.average_risk_score}
          </div>
          <div className="mt-0.5 text-2xs text-ink-500">
            across {data.project_count} work{data.project_count === 1 ? '' : 's'} · highest{' '}
            {Math.round(data.max_risk_score)}
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- counts */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Works recorded" value={data.project_count} />
        <Stat
          label="High or critical"
          value={data.high_risk_count}
          sub={`${data.critical_count} assessed critical`}
          tone={data.high_risk_count > 0 ? 'text-risk-high' : undefined}
        />
        <Stat label="Risk signals raised" value={data.total_anomalies} />
        <Stat
          label="Sanctioned"
          value={rupeesShort(data.total_sanctioned_cost)}
          sub={`${rupeesShort(data.total_expenditure)} recorded as spent`}
          wide
        />
      </div>

      {/* -------------------------------------------------- signal mix */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Risk signal distribution</h3>
          <span className="text-2xs text-ink-500">
            Share of this agency&rsquo;s works carrying each signal
            {data.scope ? ` · Scope: ${data.scope}` : ''}
          </span>
        </div>

        {signals.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-ink-500">
            No risk signal was raised on any work recorded against this agency.
          </p>
        ) : (
          <div className="space-y-2.5 p-4">
            {signals.map((signal) => (
              <div key={signal.type}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-semibold text-ink-800">{signal.title}</span>
                  <span className="tnum shrink-0 text-2xs text-ink-500">
                    <span className="text-[13px] font-bold text-ink-900">{signal.count}</span> of{' '}
                    {data.project_count} works · {signal.share_pct}%
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-100">
                  <div
                    className="h-full rounded-full bg-ink-700"
                    style={{ width: `${(signal.count / maxSignal) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* -------------------------------------------------- active cases */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Active investigations</h3>
          <span className="tnum text-2xs text-ink-500">
            {activeCases.length} open · {(data.all_cases || []).length} in total
          </span>
        </div>

        {activeCases.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-ink-500">
            No investigation case is currently open against a work of this agency.
          </p>
        ) : (
          <ul className="divide-y divide-ink-100">
            {activeCases.map((c) => (
              <li key={c.case_id} className="flex flex-wrap items-baseline gap-x-3 px-4 py-2.5">
                <Link to={`/cases/${c.case_id}`} className="link tnum text-[13px] font-semibold">
                  {c.case_id}
                </Link>
                <CaseStatusBadge status={c.status} />
                <CaseOutcomeBadge outcome={c.outcome} />
                <Link
                  to={`/projects/${c.project_id}`}
                  className="tnum text-2xs text-ink-500 hover:underline"
                >
                  {c.project_id}
                </Link>
                <span className="ml-auto text-2xs text-ink-400">
                  {c.assigned_to ? `${c.assigned_to} · ` : 'Unassigned · '}
                  opened {humanDate(c.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* -------------------------------------------------- highest-risk works */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h3 className="panel-title">Highest-risk works</h3>
          <span className="tnum text-2xs text-ink-500">
            {works.length} of {data.project_count} shown · highest score first
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="th">Project</th>
                <th className="th text-right">Risk score</th>
                <th className="th">Risk level</th>
                <th className="th">Main risk driver</th>
                <th className="th">Status</th>
                <th className="th text-right">Sanctioned</th>
                <th className="th text-right">Spent</th>
              </tr>
            </thead>
            <tbody>
              {works.map((w) => {
                const rowStyle = riskStyle(w.risk_level)
                return (
                  <tr key={w.project_id} className="group transition-colors hover:bg-ink-50">
                    <td className="td max-w-[20rem]">
                      <Link to={`/projects/${w.project_id}`} className="block">
                        <span className="tnum text-[13px] font-semibold text-ink-800 group-hover:underline">
                          {w.project_id}
                        </span>
                        <span className="mt-0.5 line-clamp-2 block text-[13px] text-ink-700">
                          {orDash(w.project_name)}
                        </span>
                      </Link>
                      <span className="mt-0.5 block truncate text-2xs text-ink-400">
                        {orDash(w.village)} · {orDash(w.district)}
                      </span>
                    </td>
                    <td className="td text-right">
                      <span className={`tnum text-[15px] font-bold ${rowStyle.text}`}>
                        {Math.round(w.risk_score)}
                      </span>
                    </td>
                    <td className="td">
                      <RiskBadge level={w.risk_level} size="sm" />
                    </td>
                    <td className="td">
                      <span className="text-[13px] text-ink-700">{orDash(w.primary_risk)}</span>
                      <span className="mt-0.5 block text-2xs text-ink-400">
                        {w.anomaly_count} signal{w.anomaly_count === 1 ? '' : 's'}
                      </span>
                    </td>
                    <td className="td whitespace-nowrap text-[13px] text-ink-700">
                      {orDash(w.status)}
                    </td>
                    <td className="td tnum whitespace-nowrap text-right text-[13px]">
                      {rupeesShort(w.sanctioned_cost)}
                    </td>
                    <td className="td tnum whitespace-nowrap text-right text-[13px]">
                      {rupeesShort(w.actual_expenditure)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {data.project_count > works.length && (
          <div className="border-t border-ink-200 bg-ink-50 px-4 py-2 text-2xs text-ink-500">
            {data.project_count - works.length} further work
            {data.project_count - works.length === 1 ? '' : 's'} recorded against this agency.{' '}
            <Link
              to={`/projects?q=${encodeURIComponent(data.implementing_agency)}`}
              className="link font-semibold"
            >
              See all in the works register →
            </Link>
          </div>
        )}
      </section>

      {/* -------------------------------------------------- peers */}
      {peers.length > 0 && (
        <section className="panel overflow-hidden">
          <div className="panel-header">
            <h3 className="panel-title">Other agencies in the same districts</h3>
            <span className="text-2xs text-ink-500">
              For context only · restricted to {(data.district_list || []).join(', ')}
            </span>
          </div>

          <div className="space-y-2 p-4">
            <PeerBar
              name={`${data.implementing_agency} (this agency)`}
              count={data.project_count}
              score={data.average_risk_score}
              max={maxPeer}
              highlight
            />
            {peers.map((p) => (
              <PeerBar
                key={p.implementing_agency}
                name={p.implementing_agency}
                count={p.project_count}
                score={p.average_risk_score}
                max={maxPeer}
                to={`/agencies/${encodeURIComponent(p.implementing_agency)}`}
              />
            ))}
          </div>

          <p className="border-t border-ink-200 px-4 py-2 text-2xs leading-relaxed text-ink-500">
            A difference between two means computed over a handful of records each is not a
            meaningful ranking of performance and must not be read as one.
          </p>
        </section>
      )}

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">
        Total sanctioned across these works: {rupees(data.total_sanctioned_cost)}. Agency names in
        this dataset are fictitious.
      </p>
    </div>
  )
}

function Stat({ label, value, sub, tone, wide }) {
  return (
    <div className="panel px-4 py-3">
      <div className="label">{label}</div>
      <div
        className={`tnum mt-0.5 font-bold leading-none ${wide ? 'text-[17px]' : 'text-xl'} ${
          tone || 'text-ink-900'
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-1 text-2xs text-ink-500">{sub}</div>}
    </div>
  )
}

function PeerBar({ name, count, score, max, highlight, to }) {
  const style = riskStyle(
    score >= 75 ? 'CRITICAL' : score >= 50 ? 'HIGH' : score >= 25 ? 'MEDIUM' : 'LOW',
  )
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        {to ? (
          <Link to={to} className="link truncate text-[13px] font-semibold">
            {name}
          </Link>
        ) : (
          <span
            className={`truncate text-[13px] ${
              highlight ? 'font-bold text-ink-900' : 'font-semibold text-ink-800'
            }`}
          >
            {name}
          </span>
        )}
        <span className="tnum shrink-0 text-2xs text-ink-500">
          <span className={`text-[13px] font-semibold ${style.text}`}>{score}</span> · {count} work
          {count === 1 ? '' : 's'}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-100">
        <div
          className="h-full rounded-full"
          style={{
            width: `${(score / max) * 100}%`,
            backgroundColor: highlight ? style.hex : '#9ca3af',
          }}
        />
      </div>
    </div>
  )
}
