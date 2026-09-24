import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ProjectTable from '../components/ProjectTable'
import { ErrorPanel, LoadingPanel } from '../components/States'
import api from '../services/api'
import useApi from '../hooks/useApi'

const RISK_FILTERS = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

/**
 * The works register.
 *
 * Search and filtering are applied server-side, because risk level only exists
 * after the engine has run — filtering in the browser would mean the client
 * deciding what "HIGH" means, which is precisely the thing that should live in
 * one place.
 */
export default function Projects() {
  const [searchParams, setSearchParams] = useSearchParams()
  const riskParam = (searchParams.get('risk') || 'ALL').toUpperCase()
  const risk = RISK_FILTERS.includes(riskParam) ? riskParam : 'ALL'

  const [search, setSearch] = useState(searchParams.get('q') || '')
  const [debounced, setDebounced] = useState(search)
  const [sort, setSort] = useState('risk_desc')

  // Debounce so typing does not fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 220)
    return () => clearTimeout(timer)
  }, [search])

  const { data, error, loading, reload } = useApi(
    (opts) => api.projects({ search: debounced, risk_level: risk, sort }, opts),
    [debounced, risk, sort],
  )

  const setRisk = (value) => {
    const next = new URLSearchParams(searchParams)
    if (value === 'ALL') next.delete('risk')
    else next.set('risk', value)
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink-900">Works register</h2>
        <p className="mt-0.5 text-[13px] text-ink-500">
          All sanctioned works in the synthetic dataset, with risk scores computed on load.
        </p>
      </div>

      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b border-ink-200 px-4 py-3">
          <div className="min-w-[16rem] flex-1">
            <label htmlFor="project-search" className="sr-only">
              Search works
            </label>
            <input
              id="project-search"
              type="search"
              className="input"
              placeholder="Search by project ID, name, district, village or agency…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-1" role="group" aria-label="Filter by risk band">
            {RISK_FILTERS.map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => setRisk(level)}
                aria-pressed={risk === level}
                className={`rounded border px-2.5 py-1.5 text-2xs font-semibold uppercase tracking-wide transition-colors ${
                  risk === level
                    ? 'border-ink-800 bg-ink-800 text-white'
                    : 'border-ink-300 bg-white text-ink-600 hover:bg-ink-50'
                }`}
              >
                {level}
              </button>
            ))}
          </div>

          <div>
            <label htmlFor="project-sort" className="sr-only">
              Sort
            </label>
            <select
              id="project-sort"
              className="input py-1.5 text-[13px]"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="risk_desc">Risk: high to low</option>
              <option value="risk_asc">Risk: low to high</option>
              <option value="cost_desc">Sanctioned cost: high to low</option>
              <option value="name_asc">Project name: A–Z</option>
            </select>
          </div>
        </div>

        {loading && <LoadingPanel label="Analysing works…" rows={8} />}

        {error && !loading && (
          <div className="p-4">
            <ErrorPanel error={error} onRetry={reload} context="GET /api/projects" />
          </div>
        )}

        {data && !loading && !error && (
          <>
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-ink-100 bg-ink-50 px-4 py-2">
              <span className="tnum text-2xs text-ink-600">
                Showing {data.returned} of {data.total} works
                {risk !== 'ALL' && ` · risk band ${risk}`}
                {debounced && ` · matching “${debounced}”`}
              </span>
              {(risk !== 'ALL' || debounced) && (
                <button
                  type="button"
                  className="link text-2xs"
                  onClick={() => {
                    setSearch('')
                    setRisk('ALL')
                  }}
                >
                  Clear filters
                </button>
              )}
            </div>

            <ProjectTable
              projects={data.projects}
              highlightId={data.projects?.[0]?.risk_level === 'CRITICAL' ? data.projects[0].project_id : null}
            />
          </>
        )}
      </section>
    </div>
  )
}
