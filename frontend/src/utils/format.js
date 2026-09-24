/**
 * Display formatting.
 *
 * Amounts use the Indian digit grouping convention (₹33,00,000) and a
 * lakh/crore short form, because that is how these figures appear in the source
 * domain and how a reviewer expects to read them.
 */

export function rupees(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Math.round(Number(value))
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)}`
}

export function rupeesShort(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  const abs = Math.abs(n)
  if (abs >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(2)} cr`
  if (abs >= 1_00_000) return `₹${(n / 1_00_000).toFixed(2)} lakh`
  return rupees(n)
}

export function pct(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(digits)}%`
}

export function signedPct(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function humanDate(value) {
  if (!value) return 'Not recorded'
  const parts = String(value).slice(0, 10).split('-')
  if (parts.length !== 3) return String(value)
  const [y, m, d] = parts
  const month = MONTHS[Number(m) - 1]
  if (!month) return String(value)
  return `${d} ${month} ${y}`
}

export function orDash(value) {
  if (value === null || value === undefined || value === '') return 'Not recorded'
  return value
}

/** Tailwind class sets per risk band. One colour per band, used everywhere. */
export const RISK_STYLES = {
  LOW: {
    text: 'text-risk-low',
    bg: 'bg-risk-lowBg',
    border: 'border-risk-lowBorder',
    bar: 'bg-risk-low',
    hex: '#15803d',
  },
  MEDIUM: {
    text: 'text-risk-medium',
    bg: 'bg-risk-mediumBg',
    border: 'border-risk-mediumBorder',
    bar: 'bg-risk-medium',
    hex: '#b45309',
  },
  HIGH: {
    text: 'text-risk-high',
    bg: 'bg-risk-highBg',
    border: 'border-risk-highBorder',
    bar: 'bg-risk-high',
    hex: '#c2410c',
  },
  CRITICAL: {
    text: 'text-risk-critical',
    bg: 'bg-risk-criticalBg',
    border: 'border-risk-criticalBorder',
    bar: 'bg-risk-critical',
    hex: '#b91c1c',
  },
}

export function riskStyle(level) {
  return RISK_STYLES[String(level || '').toUpperCase()] || RISK_STYLES.LOW
}

/** Severity chips reuse the risk palette so a severity reads the same way. */
export function severityStyle(severity) {
  return riskStyle(severity)
}
