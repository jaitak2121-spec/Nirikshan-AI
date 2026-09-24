import { useState } from 'react'
import { humanDate } from '../utils/format'

/**
 * The verification checklist, grouped by the signal each item came from.
 *
 * Every item exists because a specific signal was detected on this work — there
 * is no generic checklist, and nothing is listed for a check the engine did not
 * raise. Each item carries the figure actually recorded in the register, so the
 * officer is verifying a stated number rather than being asked an open question.
 *
 * Completing every item does not establish that a work is sound. It establishes
 * that each recorded figure has been looked at by a person.
 */
export default function VerificationChecklist({
  caseId,
  items,
  summary,
  note,
  canVerify,
  busy,
  onUpdate,
}) {
  const groups = []
  items.forEach((item) => {
    const last = groups[groups.length - 1]
    if (last && last.signal_type === item.signal_type) last.items.push(item)
    else
      groups.push({
        signal_type: item.signal_type,
        signal_title: item.signal_title,
        items: [item],
      })
  })

  const pct = summary?.percent_complete ?? 0

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Verification checklist</h3>
        <span className="tnum text-2xs text-ink-500">
          {summary?.completed ?? 0} of {summary?.total ?? items.length} steps recorded
        </span>
      </div>

      <div className="border-b border-ink-200 px-4 py-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
          <div
            className="h-full rounded-full bg-ink-700 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {(summary?.by_signal || []).map((s) => (
            <span key={s.signal_type} className="text-2xs text-ink-500">
              {s.signal_title}:{' '}
              <span className="tnum font-semibold text-ink-700">
                {s.completed}/{s.total}
              </span>
            </span>
          ))}
        </div>
      </div>

      {items.length === 0 ? (
        <p className="px-4 py-6 text-center text-[13px] text-ink-500">
          No verification steps were generated — no risk signal was detected on this work.
        </p>
      ) : (
        <div className="divide-y divide-ink-200">
          {groups.map((group) => (
            <div key={group.signal_type}>
              <div className="bg-ink-50 px-4 py-2">
                <span className="text-2xs font-bold uppercase tracking-wide text-ink-600">
                  {group.signal_title}
                </span>
              </div>
              <ul className="divide-y divide-ink-100">
                {group.items.map((item) => (
                  <ChecklistRow
                    key={item.key}
                    caseId={caseId}
                    item={item}
                    canVerify={canVerify}
                    busy={busy}
                    onUpdate={onUpdate}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {note && (
        <p className="border-t border-ink-200 px-4 py-3 text-2xs leading-relaxed text-ink-500">
          {note}
        </p>
      )}
    </section>
  )
}

function ChecklistRow({ item, canVerify, busy, onUpdate }) {
  const [open, setOpen] = useState(false)
  const [remark, setRemark] = useState(item.remark || '')
  const [evidence, setEvidence] = useState(item.evidence_ref || '')

  return (
    <li className={`px-4 py-3 ${item.completed ? 'bg-emerald-50/40' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          type="button"
          role="checkbox"
          aria-checked={Boolean(item.completed)}
          aria-label={`${item.completed ? 'Mark pending' : 'Mark complete'}: ${item.label}`}
          disabled={!canVerify || busy}
          onClick={() => onUpdate(item.key, { completed: !item.completed })}
          className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] font-bold transition-colors ${
            item.completed
              ? 'border-emerald-600 bg-emerald-600 text-white'
              : 'border-ink-300 bg-white text-transparent hover:border-ink-500'
          } ${!canVerify || busy ? 'cursor-not-allowed opacity-60' : ''}`}
        >
          ✓
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span
              className={`text-[13px] font-semibold ${
                item.completed ? 'text-ink-500 line-through' : 'text-ink-900'
              }`}
            >
              {item.label}
            </span>
            <span className="text-2xs font-semibold uppercase tracking-wide text-ink-400">
              {item.completed ? 'Completed' : 'Pending'}
            </span>
          </div>

          {item.hint && <p className="mt-0.5 text-2xs leading-relaxed text-ink-500">{item.hint}</p>}

          {item.recorded && (
            <p className="mt-1 text-2xs text-ink-600">
              <span className="font-semibold">Recorded:</span>{' '}
              <span className="tnum">{item.recorded}</span>
            </p>
          )}

          {(item.remark || item.evidence_ref || item.completed_by) && (
            <div className="mt-1.5 rounded border border-ink-200 bg-white px-2.5 py-2">
              {item.remark && (
                <p className="text-[13px] leading-relaxed text-ink-700">{item.remark}</p>
              )}
              <p className="mt-0.5 text-2xs text-ink-400">
                {item.evidence_ref && <>Reference: {item.evidence_ref} · </>}
                {item.completed_by && <>{item.completed_by} · </>}
                {item.completed_at && humanDate(item.completed_at)}
              </p>
            </div>
          )}

          {canVerify && (
            <div className="mt-1.5">
              <button
                type="button"
                className="text-2xs font-semibold text-ink-600 underline hover:text-ink-900"
                onClick={() => setOpen((v) => !v)}
              >
                {open ? 'Cancel' : item.remark ? 'Edit remark / reference' : 'Add remark / reference'}
              </button>

              {open && (
                <div className="mt-2 space-y-2">
                  <textarea
                    className="input"
                    rows={2}
                    placeholder="What was checked, and what was found"
                    value={remark}
                    onChange={(e) => setRemark(e.target.value)}
                  />
                  <input
                    className="input"
                    placeholder="Evidence or file reference (e.g. sanction order number)"
                    value={evidence}
                    onChange={(e) => setEvidence(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy}
                      onClick={() => {
                        onUpdate(item.key, {
                          remark: remark || null,
                          evidence_ref: evidence || null,
                        })
                        setOpen(false)
                      }}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busy}
                      onClick={() => {
                        onUpdate(item.key, {
                          completed: true,
                          remark: remark || null,
                          evidence_ref: evidence || null,
                        })
                        setOpen(false)
                      }}
                    >
                      Save and mark complete
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}
