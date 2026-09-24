import { Link } from 'react-router-dom'

/**
 * A single statistic.
 *
 * `accent` is used only for the two cards that count risk — a plain figure gets
 * no colour, so colour on this row always means the same thing.
 */
export default function DashboardCard({
  label,
  value,
  sub,
  accent = 'neutral',
  to,
  loading = false,
}) {
  const accents = {
    neutral: 'text-ink-900',
    high: 'text-risk-high',
    critical: 'text-risk-critical',
  }

  const body = (
    <>
      <div className="label">{label}</div>
      {loading ? (
        <div className="mt-2 h-8 w-16 animate-pulse rounded bg-ink-100" />
      ) : (
        <div className={`tnum mt-1 text-3xl font-bold leading-tight ${accents[accent] || accents.neutral}`}>
          {value}
        </div>
      )}
      {sub && <div className="mt-1 text-2xs text-ink-500">{sub}</div>}
    </>
  )

  const className =
    'panel px-4 py-3.5 block' + (to ? ' transition-colors hover:border-ink-300 hover:bg-ink-50/50' : '')

  return to ? (
    <Link to={to} className={className}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  )
}
