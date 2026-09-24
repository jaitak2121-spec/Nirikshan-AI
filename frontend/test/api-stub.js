/**
 * Synchronous stand-in for services/api.js, used only by the render test.
 *
 * Each method returns the recorded response for that endpoint immediately
 * instead of a promise, so pages can be rendered with renderToString — which
 * never runs effects — while still receiving real backend payloads.
 *
 * The identity functions are real exports of the module this file replaces, so
 * they are re-exported here as no-ops: the render test has no live server to
 * send a role header to, and the recorded payloads are already the ministry
 * officer's view.
 */
import fixtures from '../src/__fixtures__/api.json' with { type: 'json' }

function lookup(path, params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') search.set(k, v)
  })
  const sorted = [...search.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  const qs = new URLSearchParams(sorted).toString()
  const key = `/api${path}${qs ? `?${qs}` : ''}`

  if (!(key in fixtures)) {
    throw new Error(`No fixture recorded for ${key}. Re-run tools/dump_fixtures.py.`)
  }
  return { __fixture: fixtures[key] }
}

export function setActiveUser() {}
export function getActiveUser() {
  return null
}

export const api = {
  health: () => lookup('/health'),
  dashboardStats: () => lookup('/dashboard/stats'),
  projects: (params) => lookup('/projects', params),
  project: (id) => lookup(`/projects/${id}`),
  analyze: (id) => lookup(`/projects/${id}/analyze`),
  anomalies: (id) => lookup(`/projects/${id}/anomalies`),
  similar: (id, params) => lookup(`/projects/${id}/similar`, params),
  nearby: (id, params) => lookup(`/projects/${id}/nearby`, params),
  investigationQueue: () => lookup('/investigation-queue'),
  agencies: () => lookup('/agencies'),
  methodology: () => lookup('/methodology'),

  // --- roles and the case workflow
  roles: () => lookup('/roles'),
  me: () => lookup('/me'),
  cases: (params) => lookup('/cases', params),
  case: (caseId) => lookup(`/cases/${caseId}`),
  audit: (params) => lookup('/audit', params),

  // --- derived intelligence
  compliance: () => lookup('/compliance'),
  trends: () => lookup('/trends'),
  watchlist: () => lookup('/watchlist'),
  network: (id, params) => lookup(`/projects/${id}/network`, params),
  whatIf: (id) => lookup(`/projects/${id}/what-if`),
  // Encoded exactly as services/api.js encodes it, so the key matches.
  agency: (name) => lookup(`/agencies/${encodeURIComponent(name)}`),
}

export class ApiError extends Error {}

export default api
