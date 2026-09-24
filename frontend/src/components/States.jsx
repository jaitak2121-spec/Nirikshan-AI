/**
 * Loading, error and empty states.
 *
 * Grouped in one file so that no screen has an excuse to render a blank area
 * while it waits, or to swallow a failure silently.
 */

import { Link } from 'react-router-dom'

export function Skeleton({ className = '', style }) {
  return <div className={`animate-pulse rounded bg-ink-100 ${className}`} style={style} />
}

export function LoadingPanel({ label = 'Loading…', rows = 4 }) {
  return (
    <div className="panel p-4" role="status" aria-live="polite">
      <div className="mb-3 text-[13px] text-ink-500">{label}</div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4" style={{ width: `${90 - i * 8}%` }} />
        ))}
      </div>
    </div>
  )
}

export function LoadingInline({ label = 'Loading…' }) {
  return (
    <span className="inline-flex items-center gap-2 text-[13px] text-ink-500" role="status">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-ink-300 border-t-ink-600" />
      {label}
    </span>
  )
}

/**
 * The error state does the work of telling the user what to actually do. A
 * "something went wrong" message would be useless when the usual cause is that
 * the backend simply is not running yet.
 */
export function ErrorPanel({ error, onRetry, context }) {
  const isOffline = !error?.status
  const message = error?.message || 'An unexpected error occurred.'

  return (
    <div className="panel border-risk-criticalBorder bg-risk-criticalBg p-4" role="alert">
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-risk-critical text-[11px] font-bold text-white"
        >
          !
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-semibold text-risk-critical">
            {isOffline ? 'Analysis service unavailable' : `Request failed (${error.status})`}
          </div>
          {context && <div className="mt-0.5 text-2xs text-ink-500">{context}</div>}
          <p className="mt-1.5 break-words text-[13px] text-ink-700">{message}</p>

          {isOffline && (
            <pre className="mt-2 overflow-x-auto rounded border border-ink-200 bg-white px-2.5 py-2 text-2xs text-ink-700">
              uvicorn backend.main:app --reload --port 8000
            </pre>
          )}

          {onRetry && (
            <button type="button" className="btn-secondary mt-3" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="px-4 py-10 text-center">
      <div className="text-[13px] font-semibold text-ink-700">{title}</div>
      {hint && <p className="mx-auto mt-1 max-w-md text-[13px] text-ink-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function NotFoundPanel({ what = 'record', backTo = '/projects', backLabel = 'Back to projects' }) {
  return (
    <div className="panel p-8 text-center">
      <div className="text-[13px] font-semibold text-ink-800">No such {what}</div>
      <p className="mx-auto mt-1 max-w-md text-[13px] text-ink-500">
        The identifier in the address does not match any record in the synthetic dataset.
      </p>
      <Link to={backTo} className="btn-secondary mt-4">
        {backLabel}
      </Link>
    </div>
  )
}
