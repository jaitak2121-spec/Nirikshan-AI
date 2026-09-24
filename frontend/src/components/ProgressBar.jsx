/**
 * Progress bars for physical and financial progress.
 *
 * These two figures are shown together wherever possible, because the *gap*
 * between them is itself a risk signal — money moving faster than work is one
 * of the things this system looks for.
 */
export default function ProgressBar({ label, value, tone = 'neutral', showValue = true }) {
  const raw = Number(value)
  const known = Number.isFinite(raw)
  const clamped = known ? Math.max(0, Math.min(100, raw)) : 0

  const tones = {
    neutral: 'bg-ink-500',
    physical: 'bg-ink-600',
    financial: 'bg-ink-400',
    warn: 'bg-risk-high',
  }

  return (
    <div>
      {(label || showValue) && (
        <div className="mb-1 flex items-baseline justify-between gap-2">
          {label && <span className="label">{label}</span>}
          {showValue && (
            <span className="tnum text-[13px] font-semibold text-ink-800">
              {known ? `${raw}%` : 'Not recorded'}
              {/* An out-of-range figure is shown as recorded, flagged rather
                  than silently corrected — the bad value is the evidence. */}
              {known && (raw < 0 || raw > 100) && (
                <span className="ml-1.5 text-2xs font-semibold text-risk-critical">out of range</span>
              )}
            </span>
          )}
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-ink-100">
        <div
          className={`h-full rounded-full ${tones[tone] || tones.neutral} transition-[width] duration-500`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}

/** Physical vs financial together, with the gap called out when it is material. */
export function ProgressPair({ physical, financial, gapThreshold = 10 }) {
  const p = Number(physical)
  const f = Number(financial)
  const gap = Number.isFinite(p) && Number.isFinite(f) ? f - p : null
  const material = gap !== null && gap > gapThreshold

  return (
    <div className="space-y-3">
      <ProgressBar label="Physical progress" value={physical} tone="physical" />
      <ProgressBar label="Financial progress" value={financial} tone={material ? 'warn' : 'financial'} />
      {gap !== null && (
        <div className="flex items-baseline justify-between border-t border-ink-100 pt-2">
          <span className="label">Gap (financial − physical)</span>
          <span
            className={`tnum text-[13px] font-semibold ${material ? 'text-risk-high' : 'text-ink-600'}`}
          >
            {gap > 0 ? '+' : ''}
            {gap.toFixed(0)} pp
          </span>
        </div>
      )}
    </div>
  )
}
