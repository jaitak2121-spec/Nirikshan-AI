import { Link } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { EmptyState, ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { humanDate, orDash, riskStyle } from '../utils/format'

/**
 * Early warning.
 *
 * Works whose indicators are moving the wrong way but have not reached the
 * level that raises a risk signal — the gap between "nothing detected" and "on
 * the investigation queue". Each entry names the reading, the threshold it has
 * not yet crossed, and the direction it is moving in.
 *
 * Every indicator is straight-line arithmetic over the dates and progress
 * figures already on the record. It is not a forecast: no model is fitted, no
 * accuracy figure is claimed, and no historical series of these works exists to
 * validate one against. Works already assessed CRITICAL are left out, because
 * they are past warning and already on the queue.
 */

const WATCH_STYLES = {
  WATCH: 'bg-amber-50 text-amber-800 border-amber-200',
  MONITOR: 'bg-ink-100 text-ink-700 border-ink-200',
}

function WatchBadge({ level }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded border px-1.5 py-0.5 text-2xs font-bold uppercase tracking-wide ${
        WATCH_STYLES[level] || WATCH_STYLES.MONITOR
      }`}
    >
      {level}
    </span>
  )
}

export default function Watchlist() {
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi((opts) => api.watchlist(opts), [roleKey])

  if (loading) return <LoadingPanel label="Checking indicators against thresholds…" rows={8} />
  if (error) return <ErrorPanel error={error} onRetry={reload} context="GET /api/watchlist" />

  const entries = data.entries || []

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">Early warning watchlist</h2>
        <p className="mt-0.5 max-w-3xl text-[13px] leading-relaxed text-ink-500">
          Works whose indicators are moving the wrong way but have not yet crossed the level that
          raises a risk signal. This is arithmetic over the figures already on each record, not a
          forecast — no accuracy is claimed and nothing here has been detected as irregular.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="panel px-4 py-3">
          <div className="label">On watch</div>
          <div className="tnum mt-0.5 text-xl font-bold leading-none text-amber-700">
            {data.watch_count}
          </div>
          <div className="mt-1 text-2xs text-ink-500">
            Two or more indicators, or one moving sharply
          </div>
        </div>
        <div className="panel px-4 py-3">
          <div className="label">Monitor only</div>
          <div className="tnum mt-0.5 text-xl font-bold leading-none text-ink-700">
            {data.monitor_count}
          </div>
          <div className="mt-1 text-2xs text-ink-500">One indicator, moving slowly</div>
        </div>
        <div className="panel px-4 py-3">
          <div className="label">Assessed as of</div>
          <div className="mt-0.5 text-[15px] font-semibold text-ink-900">
            {humanDate(data.as_of)}
          </div>
          <div className="mt-1 text-2xs text-ink-500">
            Schedule positions recomputed at request time
            {data.scope ? ` · ${data.scope}` : ''}
          </div>
        </div>
      </div>

      {entries.length === 0 ? (
        <section className="panel overflow-hidden">
          <EmptyState
            title="No work is showing early-warning indicators"
            hint="Every in-scope record is either within tolerance on all three indicators, already complete, or already on the investigation queue."
            action={
              <Link to="/investigation-queue" className="btn-secondary">
                Open investigation queue
              </Link>
            }
          />
        </section>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => {
            const style = riskStyle(entry.risk_level)
            return (
              <section key={entry.project_id} className="panel overflow-hidden">
                <div className="flex flex-wrap items-start gap-x-4 gap-y-2 border-b border-ink-200 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/projects/${entry.project_id}`}
                        className="link tnum text-[13px] font-semibold"
                      >
                        {entry.project_id}
                      </Link>
                      <WatchBadge level={entry.watch_level} />
                      <span className="text-2xs text-ink-500">
                        {entry.indicator_count} indicator
                        {entry.indicator_count === 1 ? '' : 's'}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[13px] leading-snug text-ink-800">
                      {orDash(entry.project_name)}
                    </p>
                    <p className="mt-0.5 truncate text-2xs text-ink-400">
                      {orDash(entry.district)} · {orDash(entry.implementing_agency)} ·{' '}
                      {orDash(entry.status)}
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="label">Current score</div>
                      <div className={`tnum text-lg font-bold leading-none ${style.text}`}>
                        {Math.round(entry.risk_score)}
                      </div>
                      <div className="mt-1">
                        <RiskBadge level={entry.risk_level} size="sm" />
                      </div>
                    </div>
                  </div>
                </div>

                <ul className="divide-y divide-ink-100">
                  {(entry.indicators || []).map((indicator) => (
                    <li key={indicator.indicator} className="px-4 py-2.5">
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="text-[13px] font-semibold text-ink-900">
                          {indicator.indicator}
                        </span>
                        <span className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
                          {indicator.direction}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[13px] leading-relaxed text-ink-700">
                        {indicator.reading}
                      </p>
                      <p className="mt-0.5 text-2xs text-ink-500">
                        Not yet a signal — {indicator.threshold}.
                      </p>
                    </li>
                  ))}
                </ul>
              </section>
            )
          })}
        </div>
      )}

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
    </div>
  )
}
