import { useState } from 'react'
import EvidenceCard from './EvidenceCard'
import { severityStyle } from '../utils/format'

/**
 * One detected risk signal, with its explanation and evidence.
 *
 * The layout follows the order a reviewer needs: what was observed, then the
 * numbers it was observed from, then why it is worth a look, then how many
 * points it contributed to the score and why that many.
 *
 * The signal also carries its own verification control. An officer who has
 * checked this finding and found it explained marks it here, on the finding —
 * the score above is then recomputed with this signal withheld. Marking is not
 * a deletion: the detected values and the full weight stay on the record.
 */
export default function AnomalyCard({
  anomaly,
  explanation,
  defaultOpen = false,
  cleared = false,
  onToggleCleared,
}) {
  const [open, setOpen] = useState(defaultOpen)
  const style = severityStyle(anomaly.severity)

  const points = anomaly.contribution ?? explanation?.points_contributed ?? 0
  const maxPoints = anomaly.weight ?? explanation?.max_points ?? 0
  const actions = anomaly.recommended_actions ?? explanation?.recommended_actions ?? []

  return (
    <div
      className={`overflow-hidden rounded-md border ${
        cleared ? 'border-ink-200 bg-ink-50' : `${style.border} bg-white`
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors ${
          cleared ? 'bg-ink-50' : style.bg
        } hover:brightness-[0.98]`}
      >
        <span
          aria-hidden
          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${cleared ? 'bg-ink-300' : style.bar}`}
        />

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span
              className={`text-[13px] font-semibold ${cleared ? 'text-ink-500' : 'text-ink-900'}`}
            >
              {anomaly.title}
            </span>
            <span
              className={`rounded border px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide bg-white ${
                cleared ? 'border-ink-200 text-ink-400' : `${style.border} ${style.text}`
              }`}
            >
              {anomaly.severity}
            </span>
            {cleared && (
              <span className="rounded border border-ink-300 bg-white px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide text-ink-600">
                Checked
              </span>
            )}
          </span>
          <span className={`mt-1 block text-[13px] ${cleared ? 'text-ink-500' : 'text-ink-700'}`}>
            {anomaly.headline}
          </span>
        </span>

        <span className="shrink-0 text-right">
          {cleared ? (
            <>
              <span className="tnum block text-[15px] font-bold text-ink-500">
                <span className="font-normal text-ink-400 line-through">
                  +{Number(points).toFixed(points % 1 ? 1 : 0)}
                </span>
                <span aria-hidden> → </span>0
              </span>
              <span className="block text-2xs text-ink-500">withheld</span>
            </>
          ) : (
            <>
              <span className={`tnum block text-[15px] font-bold ${style.text}`}>
                +{Number(points).toFixed(points % 1 ? 1 : 0)}
              </span>
              <span className="block text-2xs text-ink-500">of {maxPoints} pts</span>
            </>
          )}
        </span>

        <span aria-hidden className={`mt-1 shrink-0 text-ink-400 transition-transform ${open ? 'rotate-90' : ''}`}>
          ▶
        </span>
      </button>

      {/* Verification control for this signal. Outside the header button
          because a checkbox may not be nested inside a button, and always
          visible so the signal can be marked without expanding it. */}
      {onToggleCleared && (
        <div
          className={`flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2 ${
            cleared ? 'border-ink-200 bg-ink-100' : 'border-ink-100 bg-white'
          }`}
        >
          <label className="flex cursor-pointer items-center gap-2 text-[13px]">
            <input
              type="checkbox"
              checked={cleared}
              onChange={() => onToggleCleared(anomaly.type)}
              className="h-4 w-4 cursor-pointer accent-slate-700"
              aria-label={`Mark ${anomaly.title} as checked and explained`}
            />
            <span className={cleared ? 'font-semibold text-ink-700' : 'text-ink-700'}>
              I have checked this signal and it is explained
            </span>
          </label>

          <span className="tnum ml-auto text-2xs text-ink-500">
            {cleared
              ? `${Number(points).toFixed(1)} pts withheld from the composite score`
              : `counting ${Number(points).toFixed(1)} pts toward the composite score`}
          </span>
        </div>
      )}

      {open && (
        <div className="space-y-3 border-t border-ink-200 px-4 py-3">
          {/* The §9 comparison triple, always in the same order so a reviewer
              reads the same three lines for every family of signal. */}
          <dl className="divide-y divide-ink-100 rounded border border-ink-200">
            {[
              ['Actual', anomaly.actual_value ?? explanation?.actual_value, 'bad'],
              ['Expected', anomaly.expected_value ?? explanation?.expected_value, 'neutral'],
              ['Difference', anomaly.difference ?? explanation?.difference, 'bad'],
            ]
              .filter(([, value]) => value)
              .map(([label, value, tone]) => (
                <div key={label} className="flex flex-wrap gap-x-3 gap-y-0.5 px-3 py-1.5">
                  <dt className="label w-20 shrink-0 pt-0.5">{label}</dt>
                  <dd
                    className={`min-w-0 flex-1 text-[13px] ${
                      tone === 'bad' ? `font-semibold ${style.text}` : 'text-ink-700'
                    }`}
                  >
                    {value}
                  </dd>
                </div>
              ))}
          </dl>

          <div>
            <div className="label mb-1">Why this matters</div>
            <p className="text-[13px] leading-relaxed text-ink-700">{anomaly.reason}</p>
          </div>

          <EvidenceCard title="Evidence" rows={anomaly.evidence || []} />

          {actions.length > 0 && (
            <div className="rounded border border-ink-200 bg-white px-3 py-2">
              <div className="label mb-1.5">Recommended verification for this signal</div>
              <ul className="space-y-1">
                {actions.map((action) => (
                  <li key={action} className="flex gap-2 text-[13px] leading-snug text-ink-700">
                    <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ink-400" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded border border-ink-200 bg-white px-3 py-2">
            <div className="label mb-1">Contribution to the score</div>
            <p className="text-[13px] text-ink-700">
              {explanation?.scoring_note || (
                <>
                  This signal carries a maximum weight of {maxPoints} points. Assessed severity of{' '}
                  <span className="tnum font-semibold">
                    {((anomaly.severity_factor ?? 0) * 100).toFixed(0)}%
                  </span>{' '}
                  contributes <span className="tnum font-semibold">{Number(points).toFixed(1)}</span>{' '}
                  points.
                </>
              )}
            </p>
            {cleared && (
              <p className="mt-1.5 text-[13px] text-ink-600">
                Marked as checked, so those{' '}
                <span className="tnum font-semibold">{Number(points).toFixed(1)}</span> points are
                withheld from the composite score above. The detected values and the full weight
                remain on the record — nothing has been removed.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
