import { useState } from 'react'
import { useRole } from '../hooks/useRole'

/**
 * The demonstration role selector.
 *
 * Presented as a selector and labelled as one. It would be easy — and dishonest
 * — to dress this up as a sign-in; what it actually does is tell the API which
 * demonstration identity to answer as. The scope and the permissions that follow
 * from that choice are enforced by the server.
 */
export default function RoleSwitcher() {
  const { username, setUsername, users, user, notice } = useRole()
  const [open, setOpen] = useState(false)

  if (!users.length) return null

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded border border-ink-200 bg-white px-2.5 py-1.5 text-left transition-colors hover:border-ink-300 hover:bg-ink-50"
        aria-expanded={open}
        aria-haspopup="true"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink-800 text-2xs font-bold text-white">
          {(user?.display_name || '?').charAt(0)}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-2xs font-semibold leading-tight text-ink-900">
            {user?.display_name || 'Select role'}
          </span>
          <span className="block truncate text-2xs leading-tight text-ink-500">
            {user?.role_title || user?.role} · {user?.scope_label}
          </span>
        </span>
        <span aria-hidden className="text-2xs text-ink-400">
          ▾
        </span>
      </button>

      {open && (
        <>
          {/* Click anywhere else to dismiss, without trapping focus. */}
          <button
            type="button"
            aria-label="Close role selector"
            className="fixed inset-0 z-10 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-1 w-80 rounded border border-ink-200 bg-white shadow-lg">
            <div className="border-b border-ink-200 px-3 py-2">
              <div className="text-2xs font-bold uppercase tracking-wide text-ink-500">
                Demonstration role
              </div>
            </div>

            <ul className="max-h-80 overflow-y-auto py-1">
              {users.map((u) => {
                const active = u.username === username
                return (
                  <li key={u.username}>
                    <button
                      type="button"
                      onClick={() => {
                        setUsername(u.username)
                        setOpen(false)
                      }}
                      className={`block w-full px-3 py-2 text-left transition-colors ${
                        active ? 'bg-ink-50' : 'hover:bg-ink-50'
                      }`}
                    >
                      <span className="flex items-baseline gap-2">
                        <span className="text-[13px] font-semibold text-ink-900">
                          {u.display_name}
                        </span>
                        {active && (
                          <span className="text-2xs font-semibold text-risk-low">● active</span>
                        )}
                      </span>
                      <span className="block text-2xs text-ink-600">{u.designation}</span>
                      <span className="block text-2xs text-ink-400">
                        Sees: {u.scope_label} · {u.capabilities?.length || 0} permissions
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>

            {notice && (
              <p className="border-t border-ink-200 px-3 py-2 text-2xs leading-relaxed text-ink-500">
                {notice}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
