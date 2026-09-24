/**
 * Evidence rows.
 *
 * The point of this component is that no claim appears without the numbers
 * behind it. Each row shows a labelled value, and `tone` only affects colour —
 * it never changes what the row says.
 */
export default function EvidenceCard({ title, rows = [], note, dense = false }) {
  if (!rows.length) return null

  const toneClass = {
    bad: 'text-risk-critical',
    warn: 'text-risk-high',
    good: 'text-risk-low',
    neutral: 'text-ink-800',
  }

  return (
    <div className="rounded border border-ink-200 bg-ink-50/60">
      {title && (
        <div className="border-b border-ink-200 px-3 py-2">
          <span className="label">{title}</span>
        </div>
      )}
      <dl className={dense ? 'divide-y divide-ink-100' : 'divide-y divide-ink-100'}>
        {rows.map((row, i) => (
          <div
            key={`${row.label}-${i}`}
            className="flex items-baseline justify-between gap-4 px-3 py-1.5"
          >
            <dt className="text-[13px] text-ink-600">{row.label}</dt>
            <dd
              className={`tnum shrink-0 text-right text-[13px] font-semibold ${
                toneClass[row.tone] || toneClass.neutral
              }`}
            >
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
      {note && <div className="border-t border-ink-200 px-3 py-2 text-2xs text-ink-500">{note}</div>}
    </div>
  )
}
