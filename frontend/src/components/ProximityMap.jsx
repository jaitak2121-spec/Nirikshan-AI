/**
 * Geographic proximity.
 *
 * Two views over the same Haversine figures. "Map" puts the works on an
 * OpenStreetMap basemap, which is what a reviewer wants when the question is
 * "where actually is this?". "Schematic" is a dependency-free SVG scatter that
 * needs no network, and is the automatic fallback if tiles cannot be reached —
 * a demo should never open onto a blank frame.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import GisMap from './GisMap'
import { riskStyle, rupeesShort } from '../utils/format'

const SIZE = 260
const PAD = 26

export default function ProximityMap({ origin, nearby = [], riskLevel }) {
  const [view, setView] = useState('map')
  const [gisAvailable, setGisAvailable] = useState(true)
  const hasCoords = origin?.latitude != null && origin?.longitude != null

  if (!hasCoords) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Geographic context</h3>
        </div>
        <div className="p-4">
          <p className="text-[13px] text-ink-600">
            No coordinates are recorded for this work, so nearby works cannot be located. Missing
            coordinates are themselves flagged under record quality.
          </p>
        </div>
      </section>
    )
  }

  const points = [
    {
      id: origin.project_id,
      name: origin.project_name,
      lat: origin.latitude,
      lon: origin.longitude,
      isOrigin: true,
      level: riskLevel,
      distance: 0,
    },
    ...nearby.map((n) => ({
      id: n.project_id,
      name: n.project_name,
      lat: n.latitude,
      lon: n.longitude,
      isOrigin: false,
      level: n.risk_level,
      distance: n.distance_km,
      score: n.risk_score,
      cost: n.sanctioned_cost,
      workType: n.work_type,
    })),
  ]

  // Scale to the bounding box of the points, with a floor so a tight cluster
  // does not get magnified into a misleading spread.
  const lats = points.map((p) => p.lat)
  const lons = points.map((p) => p.lon)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const spanLat = Math.max(maxLat - minLat, 0.01)
  const spanLon = Math.max(maxLon - minLon, 0.01)
  const span = Math.max(spanLat, spanLon)

  const cLat = (minLat + maxLat) / 2
  const cLon = (minLon + maxLon) / 2

  const project = (lat, lon) => ({
    // Latitude increases northward; SVG y increases downward.
    y: PAD + ((cLat + span / 2 - lat) / span) * (SIZE - 2 * PAD),
    x: PAD + ((lon - (cLon - span / 2)) / span) * (SIZE - 2 * PAD),
  })

  const originXY = project(origin.latitude, origin.longitude)

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Geographic context</h3>
        <div className="flex items-center gap-2">
          <span className="text-2xs text-ink-500">
            {nearby.length} work{nearby.length === 1 ? '' : 's'} within 25 km
          </span>
          {gisAvailable && (
            <div className="flex overflow-hidden rounded border border-ink-200" role="group">
              {['map', 'schematic'].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setView(mode)}
                  aria-pressed={view === mode}
                  className={`px-2 py-0.5 text-2xs capitalize ${
                    view === mode
                      ? 'bg-ink-800 font-semibold text-white'
                      : 'bg-white text-ink-600 hover:bg-ink-50'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-4 p-4">
        <div className={view === 'map' && gisAvailable ? 'min-w-[18rem] flex-1' : 'shrink-0'}>
          {view === 'map' && gisAvailable ? (
            <GisMap
              points={points}
              height={SIZE}
              onUnavailable={() => {
                // Tiles or the library are unreachable: drop to the schematic
                // silently and hide the toggle, since it now has one option.
                setGisAvailable(false)
                setView('schematic')
              }}
            />
          ) : (
            <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            className="rounded border border-ink-200 bg-ink-50"
            role="img"
            aria-label="Relative positions of nearby works"
          >
            {/* Reference grid: orientation only, not a basemap. */}
            {[0.25, 0.5, 0.75].map((f) => (
              <g key={f} stroke="#e2e6ec" strokeWidth="1">
                <line x1={PAD} y1={PAD + f * (SIZE - 2 * PAD)} x2={SIZE - PAD} y2={PAD + f * (SIZE - 2 * PAD)} />
                <line x1={PAD + f * (SIZE - 2 * PAD)} y1={PAD} x2={PAD + f * (SIZE - 2 * PAD)} y2={SIZE - PAD} />
              </g>
            ))}
            <rect
              x={PAD}
              y={PAD}
              width={SIZE - 2 * PAD}
              height={SIZE - 2 * PAD}
              fill="none"
              stroke="#d5dae2"
            />

            {/* Connector lines make the distance readable at a glance. */}
            {points
              .filter((p) => !p.isOrigin)
              .map((p) => {
                const xy = project(p.lat, p.lon)
                return (
                  <line
                    key={`line-${p.id}`}
                    x1={originXY.x}
                    y1={originXY.y}
                    x2={xy.x}
                    y2={xy.y}
                    stroke="#b0b9c7"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                )
              })}

            {points.map((p) => {
              const xy = project(p.lat, p.lon)
              const color = riskStyle(p.level).hex
              return (
                <g key={p.id}>
                  {p.isOrigin && (
                    <circle cx={xy.x} cy={xy.y} r="10" fill={color} fillOpacity="0.18" />
                  )}
                  <circle
                    cx={xy.x}
                    cy={xy.y}
                    r={p.isOrigin ? 6 : 4.5}
                    fill={color}
                    stroke="#ffffff"
                    strokeWidth="1.5"
                  />
                  {/* A single text node: an SVG <title> must not be given
                      multiple children, or the browser renders the markup. */}
                  <title>
                    {`${p.id} — ${p.name} (${p.isOrigin ? 'this work' : `${p.distance} km away`})`}
                  </title>
                </g>
              )
            })}

            <text x={PAD} y={SIZE - 8} fontSize="9" fill="#8492a6">
              N ↑ · relative positions, not to a basemap
            </text>
          </svg>
          )}
        </div>

        <div className="min-w-[15rem] flex-1">
          {nearby.length === 0 ? (
            <p className="text-[13px] text-ink-600">
              No other works in the dataset fall within 25 km of this site.
            </p>
          ) : (
            <ul className="divide-y divide-ink-100">
              {nearby.map((n) => (
                <li key={n.project_id} className="flex items-start gap-2.5 py-2">
                  <span
                    aria-hidden
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: riskStyle(n.risk_level).hex }}
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      to={`/projects/${n.project_id}`}
                      className="tnum text-[13px] font-semibold text-ink-800 hover:underline"
                    >
                      {n.project_id}
                    </Link>
                    <div className="truncate text-[13px] text-ink-700">{n.project_name}</div>
                    <div className="text-2xs text-ink-500">
                      {n.work_type} · {rupeesShort(n.sanctioned_cost)}
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="tnum text-[13px] font-semibold text-ink-800">
                      {n.distance_km} km
                    </div>
                    <div className="tnum text-2xs" style={{ color: riskStyle(n.risk_level).hex }}>
                      risk {Math.round(n.risk_score)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="border-t border-ink-200 bg-ink-50 px-4 py-2 text-2xs text-ink-500">
        Distances are great-circle (Haversine) calculations between recorded coordinates. Coordinates
        in this dataset are synthetic, so basemap features will not correspond to real assets. The
        dashed circle marks the 3 km radius within which two similar works count as co-located.
      </div>
    </section>
  )
}
