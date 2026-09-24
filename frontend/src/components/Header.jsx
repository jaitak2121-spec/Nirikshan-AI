import { useEffect, useState } from 'react'
import DataNotice from './DataNotice'
import RoleSwitcher from './RoleSwitcher'
import api from '../services/api'

/**
 * The application header.
 *
 * The service indicator is a live health check rather than decoration: during a
 * demo the single most useful thing to know is whether the analysis backend is
 * answering, and the header is where a user will look.
 */
export default function Header() {
  const [health, setHealth] = useState({ state: 'checking' })

  useEffect(() => {
    let cancelled = false

    const check = () =>
      api
        .health()
        .then((data) => !cancelled && setHealth({ state: 'ok', data }))
        .catch(() => !cancelled && setHealth({ state: 'down' }))

    check()
    const timer = setInterval(check, 20000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  const indicator = {
    checking: { dot: 'bg-ink-300', text: 'text-ink-500', label: 'Checking service…' },
    ok: { dot: 'bg-risk-low', text: 'text-ink-600', label: 'Analysis engine online' },
    down: { dot: 'bg-risk-critical', text: 'text-risk-critical', label: 'Analysis engine offline' },
  }[health.state]

  return (
    <header className="border-b border-ink-200 bg-white">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
        <div className="min-w-0">
          <h1 className="truncate text-[15px] font-bold tracking-tight text-ink-900">NIRIKSHAN AI</h1>
          <p className="truncate text-2xs text-ink-500">
            MPLADS Risk Intelligence &amp; Investigation Network
          </p>
        </div>

        <DataNotice className="ml-auto" />

        <RoleSwitcher />

        <div className="flex items-center gap-1.5" title={health.data?.engine || indicator.label}>
          <span aria-hidden className={`h-2 w-2 rounded-full ${indicator.dot}`} />
          <span className={`text-2xs font-semibold ${indicator.text}`}>{indicator.label}</span>
          {health.state === 'ok' && (
            <span className="tnum text-2xs text-ink-400">
              · {health.data.projects_in_database} records
            </span>
          )}
        </div>
      </div>
    </header>
  )
}
