import { riskStyle } from '../utils/format'

/**
 * The risk score, shown with its band scale so the number has context.
 *
 * A bare "94" means nothing on its own. Showing where 94 sits on the 0–100
 * scale, and which band that is, is what makes it readable at a glance.
 *
 * When an officer has marked signals as checked, this shows the recomputed
 * figure — but never in place of the assessed one. The original score, band and
 * the points withheld stay visible, because the adjusted number is a working
 * view and the assessment remains on the record.
 */
export default function RiskScore({
  score,
  level,
  bands = [],
  compact = false,
  original,
  originalLevel,
  withheld = 0,
  markCount = 0,
  pending = false,
}) {
  const style = riskStyle(level)
  const value = Math.max(0, Math.min(100, Math.round(Number(score) || 0)))
  const adjusted = markCount > 0 && original != null
  const originalValue = original != null ? Math.round(Number(original) || 0) : null

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <span className={`tnum text-lg font-bold ${style.text}`}>{value}</span>
        <span className="text-2xs text-ink-400">/100</span>
      </div>
    )
  }

  return (
    <div className={`rounded-md border p-4 ${style.bg} ${style.border}`}>
      <div className="flex items-baseline justify-between gap-2">
        <div className="label">Composite risk score</div>
        {adjusted && (
          <div className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
            {pending ? 'Recomputing…' : 'Provisional'}
          </div>
        )}
      </div>

      <div className="mt-1 flex items-end gap-2">
        {adjusted && originalValue !== value && (
          <span className="tnum pb-0.5 text-2xl font-bold leading-none text-ink-400 line-through">
            {originalValue}
          </span>
        )}
        <span className={`tnum text-4xl font-bold leading-none ${style.text}`}>{value}</span>
        <span className="pb-0.5 text-sm text-ink-400">/ 100</span>
        <span className={`pb-1 ml-auto text-sm font-bold uppercase tracking-wide ${style.text}`}>
          {String(level || '').toUpperCase()}
        </span>
      </div>

      {/* The scale, with the four bands marked, so the score is placed rather
          than just stated. */}
      <div className="mt-3">
        <div className="relative h-2 overflow-hidden rounded-full bg-white ring-1 ring-inset ring-ink-200">
          {/* The assessed score stays drawn behind the adjusted bar, so the
              withheld span is visible rather than simply gone. */}
          {adjusted && originalValue > value && (
            <div
              aria-hidden
              className="absolute inset-y-0 left-0 rounded-full bg-ink-200"
              style={{ width: `${originalValue}%` }}
            />
          )}
          <div
            className={`relative h-full rounded-full ${style.bar} transition-[width] duration-500`}
            style={{ width: `${value}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-2xs text-ink-400">
          {(bands.length ? bands : DEFAULT_BANDS).map((band) => (
            <span key={band.level} className="tnum">
              {band.min}
              <span className="ml-1 uppercase">{band.level.slice(0, 3)}</span>
            </span>
          ))}
          <span className="tnum">100</span>
        </div>
      </div>

      {adjusted && (
        <p className="mt-2.5 border-t border-white/60 pt-2 text-2xs leading-relaxed text-ink-600">
          Assessed <span className="tnum font-semibold">{originalValue}</span>{' '}
          {String(originalLevel || '').toUpperCase()} ·{' '}
          <span className="tnum font-semibold">{Number(withheld).toFixed(1)}</span> pts withheld
          against {markCount} signal{markCount === 1 ? '' : 's'} marked checked. Provisional view;
          the assessment stays on record.
        </p>
      )}
    </div>
  )
}

const DEFAULT_BANDS = [
  { level: 'LOW', min: 0, max: 24 },
  { level: 'MEDIUM', min: 25, max: 49 },
  { level: 'HIGH', min: 50, max: 74 },
  { level: 'CRITICAL', min: 75, max: 100 },
]
