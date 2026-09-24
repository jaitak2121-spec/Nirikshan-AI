import { humanDate } from '../utils/format'

/**
 * The audit trail.
 *
 * Append-only: nothing in the application edits or removes an entry once it is
 * written, which is the only property that makes a trail worth keeping. The
 * first entry on any case is the engine raising the signal — recorded with no
 * actor, because no person raised it.
 */

const EVENT_LABELS = {
  RISK_ALERT_GENERATED: 'Risk signal raised',
  CASE_CREATED: 'Case opened',
  CASE_ASSIGNED: 'Case assigned',
  CASE_OPENED_BY_OFFICER: 'Case opened by officer',
  VERIFICATION_ITEM_UPDATED: 'Verification step updated',
  REMARK_ADDED: 'Remark added',
  EVIDENCE_ADDED: 'Evidence reference added',
  STATUS_CHANGED: 'Status changed',
  CASE_ESCALATED: 'Case escalated',
  OUTCOME_RECORDED: 'Outcome recorded',
  CASE_CLOSED: 'Case closed',
}

export default function AuditTrail({ events, title = 'Audit trail' }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">{title}</h3>
        <span className="tnum text-2xs text-ink-500">
          {events.length} event{events.length === 1 ? '' : 's'} · newest first
        </span>
      </div>

      {events.length === 0 ? (
        <p className="px-4 py-6 text-center text-[13px] text-ink-500">
          No actions recorded yet.
        </p>
      ) : (
        <ol className="divide-y divide-ink-100">
          {events.map((event) => (
            <li key={event.id} className="flex gap-3 px-4 py-2.5">
              <div className="mt-1 flex w-1.5 shrink-0 justify-center">
                <span
                  aria-hidden
                  className={`h-1.5 w-1.5 rounded-full ${
                    event.actor ? 'bg-ink-400' : 'bg-risk-high'
                  }`}
                />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-[13px] font-semibold text-ink-900">
                    {EVENT_LABELS[event.event_type] || event.event_type}
                  </span>
                  <span className="tnum text-2xs text-ink-400">{humanDate(event.created_at)}</span>
                </div>

                <p className="mt-0.5 text-[13px] leading-relaxed text-ink-700">{event.summary}</p>

                {event.remark && (
                  <p className="mt-1 border-l-2 border-ink-200 pl-2 text-[13px] leading-relaxed text-ink-600">
                    {event.remark}
                  </p>
                )}

                <p className="mt-0.5 text-2xs text-ink-400">
                  {event.actor ? (
                    <>
                      {event.actor}
                      {event.actor_role ? ` · ${event.actor_role}` : ''}
                    </>
                  ) : (
                    'Automated — raised by the anomaly engine'
                  )}
                  {event.reference ? ` · Ref: ${event.reference}` : ''}
                  {event.case_id ? ` · ${event.case_id}` : ''}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}

      <p className="border-t border-ink-200 px-4 py-3 text-2xs leading-relaxed text-ink-500">
        Append-only record of actions taken in this system. Nothing here is edited or removed once
        written.
      </p>
    </section>
  )
}
