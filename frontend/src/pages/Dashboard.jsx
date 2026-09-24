import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import DashboardCard from '../components/DashboardCard'
import ProjectTable from '../components/ProjectTable'
import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { rupeesShort } from '../utils/format'

/**
 * Portfolio overview.
 *
 * Two charts only. Every figure here is recomputed by the engine on each load,
 * so the dashboard and a project's own page can never disagree.
 */
export default function Dashboard() {
  const { data, error, loading, reload } = useApi((opts) => api.dashboardStats(opts), [])

  if (loading) {
    return (
      <div className="space-y-4">
        <PageTitle />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <DashboardCard key={i} label="Loading" value="" loading />
          ))}
        </div>
        <LoadingPanel label="Running risk analysis across the works register…" rows={6} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle />
        <ErrorPanel error={error} onRetry={reload} context="GET /api/dashboard/stats" />
      </div>
    )
  }

  const distribution = data.risk_distribution || []
  const anomalies = (data.anomaly_breakdown || []).filter((a) => a.count > 0)
  const maxAnomaly = Math.max(1, ...anomalies.map((a) => a.count))

  return (
    <div className="space-y-4">
      <PageTitle />

      {/* Headline counts ------------------------------------------------- */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <DashboardCard
          label="Total works"
          value={data.total_projects}
          sub={`${rupeesShort(data.total_sanctioned_cost)} sanctioned`}
          to="/projects"
        />
        <DashboardCard
          label="High risk"
          value={data.high_risk_projects}
          sub="Risk score 50 and above"
          accent="high"
          to="/projects?risk=HIGH"
        />
        <DashboardCard
          label="Critical"
          value={data.critical_projects}
          sub="Risk score 75 and above"
          accent="critical"
          to="/projects?risk=CRITICAL"
        />
        <DashboardCard
          label="Risk signals detected"
          value={data.total_anomalies}
          sub={`Across ${data.projects_analyzed} analysed works`}
          to="/investigation-queue"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Risk distribution -------------------------------------------- */}
        <section className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Risk distribution</h2>
            <span className="tnum text-2xs text-ink-500">
              Mean score {data.average_risk_score}
            </span>
          </div>

          <div className="p-4">
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distribution} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="level"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={{ stroke: '#d5dae2' }}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(value) => [`${value} works`, 'Count']}
                    contentStyle={TOOLTIP_STYLE}
                  />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]} maxBarSize={64}>
                    {distribution.map((entry) => (
                      <Cell key={entry.level} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-3 grid grid-cols-4 gap-2 border-t border-ink-100 pt-3">
              {distribution.map((band) => (
                <Link
                  key={band.level}
                  to={`/projects?risk=${band.level}`}
                  className="rounded px-1 py-1 text-center transition-colors hover:bg-ink-50"
                >
                  <div className="tnum text-lg font-bold" style={{ color: band.color }}>
                    {band.count}
                  </div>
                  <div className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
                    {band.level}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Signal families --------------------------------------------- */}
        <section className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Signals by type</h2>
            <span className="text-2xs text-ink-500">Works may raise more than one</span>
          </div>

          <div className="p-4">
            {anomalies.length === 0 ? (
              <p className="py-8 text-center text-[13px] text-ink-500">
                No risk signals detected across the register.
              </p>
            ) : (
              <ul className="space-y-3">
                {anomalies.map((item) => (
                  <li key={item.type}>
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="text-[13px] text-ink-700">{item.title}</span>
                      <span className="tnum text-[13px] font-semibold text-ink-900">
                        {item.count}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-ink-100">
                      <div
                        className="h-full rounded-full bg-ink-600"
                        style={{ width: `${(item.count / maxAnomaly) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      {/* Highest-risk works --------------------------------------------- */}
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <h2 className="panel-title">Highest-risk works</h2>
          <Link to="/investigation-queue" className="link text-2xs">
            Open investigation queue →
          </Link>
        </div>
        <ProjectTable
          projects={data.top_risk_projects || []}
          highlightId={(data.top_risk_projects || [])[0]?.project_id}
        />
        <div className="border-t border-ink-200 bg-ink-50 px-4 py-2 text-2xs text-ink-500">
          Risk scores are computed by the anomaly engine at request time from the recorded field
          values. They are prioritisation signals, not findings.
        </div>
      </section>
    </div>
  )
}

const TOOLTIP_STYLE = {
  fontSize: 12,
  borderRadius: 4,
  border: '1px solid #d5dae2',
  boxShadow: '0 1px 3px rgb(15 23 42 / 0.08)',
}

function PageTitle() {
  return (
    <div>
      <h2 className="text-lg font-bold tracking-tight text-ink-900">Portfolio overview</h2>
      <p className="mt-0.5 text-[13px] text-ink-500">
        Risk posture across the works register, recomputed on every load.
      </p>
    </div>
  )
}
