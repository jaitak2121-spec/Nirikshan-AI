import { useState } from 'react'
import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'
import { ErrorPanel, LoadingInline } from './States'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { orDash, riskStyle, rupeesShort } from '../utils/format'

/**
 * Related records around one work.
 *
 * Every line drawn here is a relationship the register itself states or that the
 * existing similarity and distance measures compute: the same implementing
 * agency, the same district, a description that scores above the similarity
 * threshold, a site within the proximity radius. Each edge carries the basis it
 * was derived from, so the diagram can be read as "these records are related in
 * this specific way" and nothing more.
 *
 * It is deliberately not a model output. No link prediction is performed, no
 * network is learned, and a cluster of related records is not evidence of
 * coordination between the people or bodies named on them — several works by one
 * agency in one district is the normal shape of this programme, not a finding.
 */

/** Neutral edge colours: these encode relationship kind, never severity. */
const EDGE_STYLES = {
  SAME_AGENCY: { stroke: '#64748b', dash: '', label: 'text-ink-700' },
  SAME_DISTRICT: { stroke: '#94a3b8', dash: '4 3', label: 'text-ink-600' },
  TEXT_SIMILARITY: { stroke: '#475569', dash: '', label: 'text-ink-800' },
  GEOGRAPHIC_PROXIMITY: { stroke: '#94a3b8', dash: '2 3', label: 'text-ink-600' },
}

function edgeStyle(type) {
  return EDGE_STYLES[type] || { stroke: '#94a3b8', dash: '', label: 'text-ink-600' }
}

const VIEW = { width: 520, height: 300, cx: 260, cy: 150, radius: 108 }

/** Fixed positions on a circle around the origin. No physics, no randomness. */
function layout(nodes) {
  const origin = nodes.find((n) => n.is_origin)
  const others = nodes.filter((n) => !n.is_origin)
  const positions = new Map()

  if (origin) positions.set(origin.project_id, { x: VIEW.cx, y: VIEW.cy })

  const count = others.length || 1
  others.forEach((node, i) => {
    const angle = ((i / count) * 2 * Math.PI) - Math.PI / 2
    positions.set(node.project_id, {
      x: VIEW.cx + VIEW.radius * Math.cos(angle) * 1.55,
      y: VIEW.cy + VIEW.radius * Math.sin(angle),
    })
  })

  return positions
}

/**
 * Curve edges that share a pair of records.
 *
 * Two records are often related in more than one way at once — the same agency
 * *and* the same district *and* a similar description. Drawn as straight lines
 * those land on top of each other and the diagram shows one relationship where
 * there are three. Fanning them into separate arcs keeps every reason visible,
 * which is the whole point of showing this at all.
 */
function arcPath(a, b, offset) {
  if (!offset) return `M ${a.x} ${a.y} L ${b.x} ${b.y}`
  const dx = b.x - a.x
  const dy = b.y - a.y
  const length = Math.hypot(dx, dy)
  if (!length) return `M ${a.x} ${a.y} L ${b.x} ${b.y}`
  // A quadratic curve peaks at half its control offset, hence the doubling.
  const cx = (a.x + b.x) / 2 + (-dy / length) * offset * 2
  const cy = (a.y + b.y) / 2 + (dx / length) * offset * 2
  return `M ${a.x} ${a.y} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${b.x} ${b.y}`
}

/** Offset per edge, so edges sharing a pair fan out symmetrically. */
function fanOffsets(edges) {
  const groups = new Map()
  edges.forEach((edge) => {
    const key = [edge.source, edge.target].sort().join('~')
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(edge)
  })

  const offsets = new Map()
  groups.forEach((group) => {
    group.forEach((edge, i) => {
      offsets.set(
        `${edge.type}-${edge.source}-${edge.target}`,
        (i - (group.length - 1) / 2) * 16,
      )
    })
  })
  return offsets
}

/**
 * Fit the drawing to the nodes actually placed.
 *
 * The circle layout is sized for a full ring of neighbours, so a work with one
 * or two related records would otherwise sit in a mostly empty frame. The box is
 * padded for the two lines of label that hang below each node.
 */
function viewBoxFor(positions) {
  const points = [...positions.values()]
  if (!points.length) return `0 0 ${VIEW.width} ${VIEW.height}`

  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const minX = Math.min(...xs) - 70
  const maxX = Math.max(...xs) + 70
  const minY = Math.min(...ys) - 28
  const maxY = Math.max(...ys) + 40

  return `${minX.toFixed(0)} ${minY.toFixed(0)} ${(maxX - minX).toFixed(0)} ${(maxY - minY).toFixed(0)}`
}

export default function InvestigationNetwork({ projectId }) {
  const { data, error, loading, reload } = useApi(
    (opts) => api.network(projectId, opts),
    [projectId],
  )
  const [selected, setSelected] = useState(null)

  if (loading) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Related records</h3>
        </div>
        <div className="p-4">
          <LoadingInline label="Mapping relationships…" />
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <ErrorPanel
        error={error}
        onRetry={reload}
        context={`GET /api/projects/${projectId}/network`}
      />
    )
  }

  const nodes = data.nodes || []
  const edges = data.edges || []
  const positions = layout(nodes)
  const byId = new Map(nodes.map((n) => [n.project_id, n]))

  const visible = selected ? edges.filter((e) => e.type === selected) : edges
  const offsets = fanOffsets(visible)
  const focusIds = new Set()
  if (selected) {
    visible.forEach((e) => {
      focusIds.add(e.source)
      focusIds.add(e.target)
    })
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Related records</h3>
        <span className="text-2xs text-ink-500">
          {data.neighbour_count} related · within {data.radius_km} km
        </span>
      </div>

      <div className="space-y-3 p-4">
        <p className="max-w-3xl text-[13px] leading-relaxed text-ink-600">
          Records connected to this work by a relationship the register states or that the similarity
          and distance measures compute. A relationship is a reason to compare two records side by
          side. It is not evidence of coordination between the bodies named on them — several works
          by one agency in one district is the ordinary shape of this programme.
        </p>

        {nodes.length <= 1 ? (
          <p className="rounded border border-ink-200 bg-ink-50 px-3 py-2 text-[13px] text-ink-600">
            No other record in scope shares an agency, a district, a comparable description or a site
            within {data.radius_km} km of this work.
          </p>
        ) : (
          <>
            {/* Relationship kinds: selecting one isolates it in the diagram. */}
            <div className="flex flex-wrap gap-1.5">
              {(data.edge_types || [])
                .filter((t) => t.count > 0)
                .map((t) => {
                  const on = selected === t.type
                  const style = edgeStyle(t.type)
                  return (
                    <button
                      type="button"
                      key={t.type}
                      onClick={() => setSelected(on ? null : t.type)}
                      className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-2xs font-semibold transition-colors ${
                        on
                          ? 'border-ink-400 bg-ink-100 text-ink-900'
                          : 'border-ink-200 bg-white text-ink-600 hover:bg-ink-50'
                      }`}
                    >
                      <span
                        aria-hidden
                        className="inline-block h-0.5 w-4"
                        style={{ backgroundColor: style.stroke }}
                      />
                      {t.label}
                      <span className="tnum text-ink-500">{t.count}</span>
                    </button>
                  )
                })}
              {selected && (
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="rounded px-2 py-1 text-2xs font-semibold text-ink-500 underline hover:text-ink-800"
                >
                  Show all relationships
                </button>
              )}
            </div>

            {/* Diagram: fixed hub-and-spoke placement, no layout algorithm. */}
            <div className="overflow-x-auto rounded border border-ink-200 bg-white">
              <svg
                viewBox={viewBoxFor(positions)}
                className="mx-auto h-auto w-full max-w-2xl"
                role="img"
                aria-label={`Relationship diagram: ${data.neighbour_count} records related to ${projectId}`}
              >
                {visible.map((edge) => {
                  const a = positions.get(edge.source)
                  const b = positions.get(edge.target)
                  if (!a || !b) return null
                  const style = edgeStyle(edge.type)
                  const key = `${edge.type}-${edge.source}-${edge.target}`
                  return (
                    <path
                      key={key}
                      d={arcPath(a, b, offsets.get(key) || 0)}
                      fill="none"
                      stroke={style.stroke}
                      strokeWidth={1 + Number(edge.strength || 0) * 2}
                      strokeDasharray={style.dash || undefined}
                      opacity={0.8}
                    />
                  )
                })}

                {nodes.map((node) => {
                  const p = positions.get(node.project_id)
                  if (!p) return null
                  const dim = selected && !focusIds.has(node.project_id)
                  // A work outside the officer's area is drawn in neutral grey:
                  // its band was withheld, and painting it in a risk colour
                  // would assert a band nobody on this screen was shown.
                  const fill = node.out_of_scope ? '#cbd5e1' : riskStyle(node.risk_level).hex
                  const r = node.is_origin ? 13 : 9
                  return (
                    <g key={node.project_id} opacity={dim ? 0.25 : 1}>
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={r}
                        fill={fill}
                        stroke={node.is_origin ? '#0f172a' : '#ffffff'}
                        strokeWidth={node.is_origin ? 2.5 : 1.5}
                      />
                      <text
                        x={p.x}
                        y={p.y + r + 11}
                        textAnchor="middle"
                        className="tnum"
                        fontSize="9"
                        fontWeight={node.is_origin ? 700 : 500}
                        fill="#334155"
                      >
                        {node.project_id}
                      </text>
                      <text
                        x={p.x}
                        y={p.y + r + 21}
                        textAnchor="middle"
                        fontSize="8"
                        fill="#64748b"
                      >
                        {node.out_of_scope
                          ? 'Outside your area'
                          : `${Math.round(node.risk_score)} · ${node.risk_level}`}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>

            {/* Every edge in words, with the basis it was derived from. */}
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <th className="th">Related record</th>
                    <th className="th">Relationship</th>
                    <th className="th">Derived from</th>
                    <th className="th text-right">Risk score</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((edge) => {
                    const otherId = edge.source === projectId ? edge.target : edge.source
                    const node = byId.get(otherId)
                    const style = riskStyle(node?.risk_level)
                    return (
                      <tr
                        key={`${edge.type}-${edge.source}-${edge.target}-row`}
                        className="transition-colors hover:bg-ink-50"
                      >
                        <td className="td max-w-[18rem]">
                          <Link
                            to={`/projects/${otherId}`}
                            className="link tnum block text-[13px] font-semibold"
                          >
                            {otherId}
                          </Link>
                          <span className="mt-0.5 line-clamp-1 block text-[13px] text-ink-700">
                            {orDash(node?.project_name)}
                          </span>
                          <span className="mt-0.5 block text-2xs text-ink-400">
                            {orDash(node?.district)} · {orDash(node?.implementing_agency)}
                            {node?.sanctioned_cost != null
                              ? ` · ${rupeesShort(node.sanctioned_cost)}`
                              : ''}
                          </span>
                        </td>
                        <td className="td text-[13px] text-ink-800">{edge.label}</td>
                        <td className="td max-w-[16rem] text-2xs leading-relaxed text-ink-500">
                          {edge.basis}
                        </td>
                        <td className="td whitespace-nowrap text-right">
                          {node?.out_of_scope ? (
                            <span className="text-2xs text-ink-500">
                              Withheld — outside your area
                            </span>
                          ) : (
                            <>
                              <span className={`tnum text-[13px] font-bold ${style.text}`}>
                                {node?.risk_score != null ? Math.round(node.risk_score) : '—'}
                              </span>
                              <span className="ml-1.5 align-middle">
                                <RiskBadge level={node?.risk_level} size="sm" />
                              </span>
                            </>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {data.withheld_nodes > 0 && (
          <p className="text-2xs leading-relaxed text-ink-500">
            {data.withheld_nodes} related record
            {data.withheld_nodes === 1 ? '' : 's'} lie outside your area. The relationship is still
            shown — it is what makes this work worth looking at — but the score and cost on those
            records belong to another officer&rsquo;s jurisdiction and are withheld. {data.scope}
          </p>
        )}

        <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
      </div>
    </section>
  )
}
