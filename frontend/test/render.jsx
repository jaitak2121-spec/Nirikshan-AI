/**
 * Renders every page in its loaded state and checks the resulting HTML.
 *
 * Compiling proves the imports resolve; this proves the components actually
 * work against the payloads the backend really returns. It catches the class of
 * bug a build cannot see — a renamed response field rendering as "undefined", a
 * number formatter fed a null and printing "NaN", a chart handed the wrong key.
 *
 * It also re-runs the legal-language rule over the rendered text, which is the
 * only place the user-visible wording can be checked as a whole.
 *
 * Data comes from test/api-stub.js and effects are bypassed by
 * test/useApi-stub.js; both are aliased in at build time only.
 */
import { renderToString } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom/server'
import App from '../src/App'

const ROUTES = [
  { path: '/', name: 'Dashboard' },
  { path: '/projects', name: 'Works register' },
  { path: '/projects?risk=CRITICAL', name: 'Works register (CRITICAL filter)' },
  { path: '/projects/MPLAD-2026-024', name: 'Hero project details' },
  { path: '/projects/MPLAD-2026-001', name: 'Clean project details' },
  { path: '/projects/MPLAD-2026-017', name: 'Malformed record details' },
  { path: '/investigation-queue', name: 'Investigation queue' },
  { path: '/cases/CASE-0001', name: 'Case detail' },
  { path: '/watchlist', name: 'Early warning watchlist' },
  { path: '/compliance', name: 'Compliance monitor' },
  { path: '/trends', name: 'Risk composition by period' },
  { path: '/agencies', name: 'Agency list' },
  // Percent-encoded, because an agency name carries spaces and commas. The
  // route is a wildcard for exactly this reason, and this case is a regression
  // guard: the encoded form once reached the API undecoded and 404'd.
  { path: '/agencies/Zilla%20Parishad%2C%20Nagpur', name: 'Agency risk profile' },
  { path: '/about', name: 'About prototype' },
]

// Content each page must actually contain, to catch a page that renders an
// empty shell without erroring.
const MUST_CONTAIN = {
  '/': ['NIRIKSHAN AI', 'Prototype / Synthetic Demonstration Data', 'Risk distribution'],
  '/projects': ['MPLAD-2026-024', 'Works register', 'Risk score'],
  '/projects?risk=CRITICAL': ['MPLAD-2026-024', 'Showing 1 of 26'],
  '/projects/MPLAD-2026-024': [
    'Community Hall',
    'Analyze Risk',
    'Why flagged',
    'Priority verification recommended',
    'Data lineage',
    'Synthetic Demonstration Record',
    '94',
    'CRITICAL',
    // The contribution table must open out into the figures behind each line.
    'How the score was reached',
    'Select a contribution to see its evidence',
    // What the score rests on is recomputed, not predicted.
    'What the score rests on',
    'Composite recomputed with one signal withheld',
    // Relationships are shown with the basis each was derived from.
    'Related records',
    'Derived from',
  ],
  '/projects/MPLAD-2026-001': ['MPLAD-2026-001'],
  '/projects/MPLAD-2026-017': ['MPLAD-2026-017'],
  '/investigation-queue': ['Investigation queue', 'MPLAD-2026-024', 'Priority'],
  '/cases/CASE-0001': [
    'CASE-0001',
    'MPLAD-2026-024',
    'Verification checklist',
    'Audit trail',
    'Case actions',
    // The generated checklist must come from the signals actually detected.
    'Cost Anomaly',
    // The trail must start with the engine raising the signal, not a person.
    'Automated — raised by the anomaly engine',
  ],
  '/watchlist': ['Early warning watchlist', 'Assessed as of', 'not a forecast'],
  '/compliance': [
    'Compliance monitor',
    'Checks across the register',
    'Grade by work',
    'REQUIRES REVIEW',
  ],
  '/trends': [
    'Risk composition by sanction period',
    'Signal mix per period',
    // The page must not present itself as a risk trend over time.
    'not as risk rising or falling',
  ],
  '/agencies': ['Agency risk profile'],
  '/agencies/Zilla%20Parishad%2C%20Nagpur': [
    'Zilla Parishad, Nagpur',
    'Risk signal distribution',
    'Highest-risk works',
    'Active investigations',
  ],
  '/about': [
    'About this prototype',
    'Future scope',
    'Phase 1',
    // The limitations must stay honest about what is and is not implemented.
    'No trained machine-learning model is used anywhere',
    'do not survive a cold start',
  ],
}

// Same rule as tools/acceptance_test.py, applied to rendered output.
const BANNED = [
  /\bis fraudulent\b/i,
  /\bis corrupt\b/i,
  /\bconfirmed fraud\b/i,
  /\bproven fraud\b/i,
  /\bfraud detected\b/i,
  /\bfraudulent project\b/i,
  /\bembezzl/i,
  /\bguilty\b/i,
  /\bcriminal\b/i,
]

let checks = 0
const failures = []

function check(label, ok, detail = '') {
  checks += 1
  if (ok) {
    console.log(`  PASS  ${label}${detail ? `  (${detail})` : ''}`)
  } else {
    failures.push(`${label}${detail ? ` — ${detail}` : ''}`)
    console.log(`  FAIL  ${label}${detail ? `  (${detail})` : ''}`)
  }
}

/** Strip tags so text assertions do not accidentally match markup. */
function textOf(html) {
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/\s+/g, ' ')
}

// React reports invalid markup and bad props through console.error/warn rather
// than by throwing, so they are captured and treated as failures. Anything
// inherent to rendering a client-side router statically is allowed through.
const ALLOWED_WARNINGS = [
  '<Navigate> must not be used on the initial render in a <StaticRouter>',
  'useLayoutEffect does nothing on the server',
]

const warnings = []
const realError = console.error
const realWarn = console.warn
const capture = (...args) => {
  const message = args.map((a) => (typeof a === 'string' ? a : String(a?.message ?? a))).join(' ')
  if (!ALLOWED_WARNINGS.some((allowed) => message.includes(allowed))) {
    warnings.push(message.split('\n')[0].slice(0, 160))
  }
}
console.error = capture
console.warn = capture

function drainWarnings(label) {
  const found = [...new Set(warnings)]
  warnings.length = 0
  check(`${label} raises no React warnings`, found.length === 0, found.slice(0, 2).join(' | '))
}

console.log('\nPage render (server-side, against recorded backend payloads)')
console.log('-'.repeat(60))

for (const route of ROUTES) {
  let html = ''
  let threw = null
  try {
    html = renderToString(
      <StaticRouter location={route.path}>
        <App />
      </StaticRouter>,
    )
  } catch (err) {
    threw = err
  }

  if (threw) {
    check(`${route.name} renders`, false, `${threw.message.split('\n')[0]}`)
    continue
  }

  check(`${route.name} renders`, html.length > 500, `${html.length} bytes`)

  const text = textOf(html)

  check(`${route.name} has no "undefined" in output`, !/\bundefined\b/.test(text))
  check(`${route.name} has no "NaN" in output`, !/\bNaN\b/.test(text))
  check(`${route.name} has no "[object Object]" in output`, !text.includes('[object Object]'))

  const missing = (MUST_CONTAIN[route.path] || []).filter((needle) => !text.includes(needle))
  check(`${route.name} shows its expected content`, missing.length === 0, missing.join(', '))

  const banned = BANNED.filter((re) => re.test(text)).map((re) => String(re))
  check(`${route.name} uses no accusatory language`, banned.length === 0, banned.join(', '))

  check(
    `${route.name} carries the synthetic-data notice`,
    text.includes('Synthetic Demonstration Data') || route.path.startsWith('/projects/'),
  )

  drainWarnings(route.name)
}

// The unknown-route case must land somewhere sensible rather than blank.
try {
  const html = renderToString(
    <StaticRouter location="/no-such-page">
      <App />
    </StaticRouter>,
  )
  check('unknown route does not render a blank screen', textOf(html).length > 200, `${html.length} bytes`)
} catch (err) {
  check('unknown route does not render a blank screen', false, err.message.split('\n')[0])
}

console.log('\nResult')
console.log('-'.repeat(6))
console.log(`  ${checks - failures.length}/${checks} checks passed`)
if (failures.length) {
  console.log('\n  Failures:')
  failures.forEach((f) => console.log(`    - ${f}`))
  process.exit(1)
}
console.log('  All checks passed.')