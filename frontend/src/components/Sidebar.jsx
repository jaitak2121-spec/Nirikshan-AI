import { NavLink } from 'react-router-dom'

/**
 * Navigation.
 *
 * Every item here routes to a screen that is actually implemented. There are no
 * placeholder destinations — a nav item that leads nowhere is worse than a
 * shorter menu.
 */
const NAV = [
  { to: '/', label: 'Dashboard', end: true, hint: 'Portfolio overview' },
  { to: '/projects', label: 'Projects', hint: 'Works register' },
  { to: '/investigation-queue', label: 'Investigation Queue', hint: 'Prioritised worklist' },
  { to: '/watchlist', label: 'Early Warning', hint: 'Indicators below threshold' },
  { to: '/compliance', label: 'Compliance Monitor', hint: 'Record-level checks' },
  { to: '/trends', label: 'Risk Composition', hint: 'Grouped by sanction period' },
  { to: '/agencies', label: 'Agencies', hint: 'Risk by implementing agency' },
  { to: '/about', label: 'About Prototype', hint: 'Method, scope and future work' },
]

export default function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-ink-200 bg-white">
      <div className="border-b border-ink-200 px-4 py-4">
        <div className="text-base font-bold tracking-tight text-ink-900">NIRIKSHAN AI</div>
        <div className="mt-0.5 text-2xs leading-snug text-ink-500">
          MPLADS Risk Intelligence &amp;<br />
          Investigation Network
        </div>
      </div>

      <nav className="flex-1 p-2" aria-label="Main">
        <ul className="space-y-0.5">
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `block rounded px-3 py-2 transition-colors ${
                    isActive
                      ? 'bg-ink-800 text-white'
                      : 'text-ink-700 hover:bg-ink-50 hover:text-ink-900'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="block text-[13px] font-semibold">{item.label}</span>
                    <span className={`block text-2xs ${isActive ? 'text-ink-300' : 'text-ink-400'}`}>
                      {item.hint}
                    </span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-ink-200 px-4 py-3">
        <div className="text-2xs leading-relaxed text-ink-400">
          Prototype v0.1 · Decision support only. Determinations rest with the authorised officer.
        </div>
      </div>
    </aside>
  )
}
