import { riskStyle } from '../utils/format'

/**
 * The risk band label.
 *
 * Wording is deliberate throughout the interface: a band describes a *signal
 * strength*, not a finding. CRITICAL means "verify this first", not "this is
 * fraudulent".
 */
export default function RiskBadge({ level, score, size = 'md', showScore = false }) {
  const style = riskStyle(level)
  const label = String(level || 'LOW').toUpperCase()

  const sizes = {
    sm: 'px-1.5 py-0.5 text-2xs',
    md: 'px-2 py-0.5 text-[11px]',
    lg: 'px-2.5 py-1 text-xs',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border font-semibold uppercase tracking-wide ${style.bg} ${style.border} ${style.text} ${sizes[size] || sizes.md}`}
      title={`Risk band: ${label}`}
    >
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${style.bar}`} />
      {label}
      {showScore && score !== undefined && score !== null && (
        <span className="tnum font-bold">{Math.round(score)}</span>
      )}
    </span>
  )
}
