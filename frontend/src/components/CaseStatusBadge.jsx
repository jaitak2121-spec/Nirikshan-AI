/**
 * Case status and outcome badges.
 *
 * Statuses describe where a case has reached in the workflow. None of them is a
 * finding: a case that has been escalated has been passed upward for a closer
 * look, not established as improper.
 */

export const CASE_STATUS_STYLES = {
  OPEN: { bg: 'bg-ink-100', text: 'text-ink-700', border: 'border-ink-200' },
  ASSIGNED: { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
  'UNDER VERIFICATION': {
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
  },
  'CLARIFICATION REQUESTED': {
    bg: 'bg-purple-50',
    text: 'text-purple-800',
    border: 'border-purple-200',
  },
  ESCALATED: { bg: 'bg-orange-50', text: 'text-orange-800', border: 'border-orange-300' },
  CLOSED: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
}

export function CaseStatusBadge({ status, size = 'sm' }) {
  if (!status) return null
  const style = CASE_STATUS_STYLES[status] || CASE_STATUS_STYLES.OPEN
  const pad = size === 'lg' ? 'px-2.5 py-1 text-[13px]' : 'px-2 py-0.5 text-2xs'
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded border font-semibold uppercase tracking-wide ${style.bg} ${style.text} ${style.border} ${pad}`}
    >
      {status}
    </span>
  )
}

/**
 * The officer's recorded conclusion.
 *
 * Shown in neutral type on purpose. "Valid Risk" means the officer found the
 * signal worth acting on; it is not a finding of wrongdoing, and the styling
 * should not suggest one.
 */
export function CaseOutcomeBadge({ outcome }) {
  if (!outcome) return null
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded border border-ink-300 bg-white px-2 py-0.5 text-2xs font-semibold text-ink-700">
      {outcome}
    </span>
  )
}

export default CaseStatusBadge
