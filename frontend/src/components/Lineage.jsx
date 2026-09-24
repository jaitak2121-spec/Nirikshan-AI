/**
 * Data lineage.
 *
 * Shows where the record came from and what transformed it before a score was
 * attached to it. A risk figure without a traceable path is not something an
 * officer should be asked to act on.
 */
export default function Lineage({ lineage }) {
  if (!lineage) return null

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Data lineage</h3>
        <span className="rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-2xs font-semibold text-amber-800">
          Source: {lineage.source}
        </span>
      </div>

      <div className="p-4">
        <ol className="space-y-0">
          {lineage.stages.map((stage, i) => (
            <li key={stage.stage} className="flex gap-3">
              {/* Rail */}
              <div className="flex w-4 shrink-0 flex-col items-center">
                <span className="h-3.5 w-3.5 shrink-0 rounded-full border-2 border-ink-600 bg-white" />
                {i < lineage.stages.length - 1 && <span className="w-px flex-1 bg-ink-200" />}
              </div>

              <div className={i < lineage.stages.length - 1 ? 'min-w-0 pb-4' : 'min-w-0'}>
                <div className="text-[13px] font-semibold leading-none text-ink-800">
                  {stage.stage}
                </div>
                <div className="mt-1 text-[13px] leading-snug text-ink-600">{stage.detail}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="border-t border-ink-200 bg-ink-50 px-4 py-2 text-2xs text-ink-500">
        Record {lineage.record_id} · {lineage.dataset}
      </div>
    </section>
  )
}
