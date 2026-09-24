/**
 * API client.
 *
 * Every risk figure the interface displays comes from these calls. Nothing is
 * computed in the browser — the frontend renders what the analysis engine
 * returns, which is what makes the numbers on screen auditable.
 */

const BASE = '/api'

/**
 * The demonstration identity the API should act as.
 *
 * Held here rather than passed through every call site so that switching role
 * changes what the whole interface sees at once. This is a demonstration
 * selector, not a login: there is no password, session or token anywhere in the
 * prototype, and the API enforces the scope and permissions on its side.
 */
let activeUser = null

export function setActiveUser(username) {
  activeUser = username || null
}

export function getActiveUser() {
  return activeUser
}

/** Thrown for any non-2xx response, carrying a message worth showing a user. */
export class ApiError extends Error {
  constructor(message, { status = 0, path = '' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  const url = `${BASE}${path}`
  let response

  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (activeUser) headers['X-Nirikshan-User'] = activeUser

  try {
    response = await fetch(url, {
      method,
      signal,
      headers: Object.keys(headers).length ? headers : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    // A failed fetch here almost always means the backend is not running.
    throw new ApiError(
      'Cannot reach the analysis service. Start the backend with: uvicorn backend.main:app --reload --port 8000',
      { path: url },
    )
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`
    try {
      const payload = await response.json()
      if (payload?.detail) detail = payload.detail
    } catch {
      /* response had no JSON body; keep the status message */
    }
    throw new ApiError(detail, { status: response.status, path: url })
  }

  return response.json()
}

function query(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  health: (opts) => request('/health', opts),
  dashboardStats: (opts) => request('/dashboard/stats', opts),
  projects: (params, opts) => request(`/projects${query(params)}`, opts),
  project: (id, opts) => request(`/projects/${encodeURIComponent(id)}`, opts),
  analyze: (id, opts) =>
    request(`/projects/${encodeURIComponent(id)}/analyze`, { ...opts, method: 'POST' }),
  anomalies: (id, opts) => request(`/projects/${encodeURIComponent(id)}/anomalies`, opts),
  verify: (id, cleared, opts) =>
    request(`/projects/${encodeURIComponent(id)}/verify`, {
      ...opts,
      method: 'POST',
      body: { cleared },
    }),
  similar: (id, params, opts) =>
    request(`/projects/${encodeURIComponent(id)}/similar${query(params)}`, opts),
  nearby: (id, params, opts) =>
    request(`/projects/${encodeURIComponent(id)}/nearby${query(params)}`, opts),
  investigationQueue: (opts) => request('/investigation-queue', opts),
  agencies: (opts) => request('/agencies', opts),
  methodology: (opts) => request('/methodology', opts),

  // Identity and roles
  roles: (opts) => request('/roles', opts),
  me: (opts) => request('/me', opts),

  // Investigation cases
  cases: (params, opts) => request(`/cases${query(params)}`, opts),
  case: (caseId, opts) => request(`/cases/${encodeURIComponent(caseId)}`, opts),
  openCase: (body, opts) => request('/cases', { ...opts, method: 'POST', body }),
  assignCase: (caseId, assignTo, opts) =>
    request(`/cases/${encodeURIComponent(caseId)}/assign`, {
      ...opts,
      method: 'POST',
      body: { assign_to: assignTo },
    }),
  setCaseStatus: (caseId, status, remark, opts) =>
    request(`/cases/${encodeURIComponent(caseId)}/status`, {
      ...opts,
      method: 'POST',
      body: { status, remark },
    }),
  setCaseOutcome: (caseId, outcome, remark, opts) =>
    request(`/cases/${encodeURIComponent(caseId)}/outcome`, {
      ...opts,
      method: 'POST',
      body: { outcome, remark },
    }),
  addCaseRemark: (caseId, remark, reference, opts) =>
    request(`/cases/${encodeURIComponent(caseId)}/remarks`, {
      ...opts,
      method: 'POST',
      body: { remark, reference },
    }),
  updateChecklistItem: (caseId, itemKey, body, opts) =>
    request(
      `/cases/${encodeURIComponent(caseId)}/checklist/${itemKey
        .split('/')
        .map(encodeURIComponent)
        .join('/')}`,
      { ...opts, method: 'PATCH', body },
    ),
  audit: (params, opts) => request(`/audit${query(params)}`, opts),

  // Derived intelligence
  compliance: (opts) => request('/compliance', opts),
  trends: (opts) => request('/trends', opts),
  watchlist: (opts) => request('/watchlist', opts),
  network: (id, params, opts) =>
    request(`/projects/${encodeURIComponent(id)}/network${query(params)}`, opts),
  whatIf: (id, opts) => request(`/projects/${encodeURIComponent(id)}/what-if`, opts),
  agency: (name, opts) => request(`/agencies/${encodeURIComponent(name)}`, opts),
}

export default api
