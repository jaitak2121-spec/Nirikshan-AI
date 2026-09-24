/**
 * The synthetic-data notice.
 *
 * This appears in the header on every screen, not tucked away on an About page.
 * A risk-scoring interface that looks official could be mistaken for one, and
 * the cost of that mistake is high enough that the notice should be impossible
 * to miss.
 */
export default function DataNotice({ variant = 'badge', className = '' }) {
  if (variant === 'badge') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-2xs font-semibold uppercase tracking-wide text-amber-800 ${className}`}
      >
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        Prototype / Synthetic Demonstration Data
      </span>
    )
  }

  return (
    <div
      className={`rounded border border-amber-300 bg-amber-50 px-3 py-2 text-[13px] text-amber-900 ${className}`}
      role="note"
    >
      <span className="font-semibold">Prototype / Synthetic Demonstration Data.</span>{' '}
      Every record shown is generated for demonstration purposes. This prototype does not use, mirror
      or represent official government records, and the names, amounts and dates in it are fictitious.
    </div>
  )
}

/**
 * The standing legal position of the tool, restated wherever a risk figure is
 * presented as a conclusion might be.
 */
export function Disclaimer({ text, className = '' }) {
  return (
    <div className={`rounded border border-ink-200 bg-ink-50 px-3 py-2 ${className}`} role="note">
      <div className="label mb-1">Scope of this assessment</div>
      <p className="text-[13px] leading-relaxed text-ink-600">
        {text ||
          'NIRIKSHAN AI is a decision-support system. It reports rule-based risk signals for prioritisation only. It does not establish irregularity, misappropriation or wrongdoing of any kind. All signals require verification against source records, and the determination rests with the authorised officer.'}
      </p>
    </div>
  )
}
