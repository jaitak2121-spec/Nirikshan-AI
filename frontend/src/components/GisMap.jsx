/**
 * GIS basemap layer.
 *
 * Leaflet and OpenStreetMap tiles are loaded lazily from a CDN rather than
 * added as an npm dependency: the schematic view in ProximityMap remains the
 * offline-safe default path, and this layer is additive. If the library or the
 * tiles cannot be reached — an air-gapped venue, a blocked CDN — `onUnavailable`
 * fires and the caller falls back to the schematic rather than showing a blank
 * frame.
 *
 * Distances and the co-location radius drawn here are the same Haversine
 * figures the duplicate detector uses; the basemap only gives them context.
 */
import { useEffect, useRef, useState } from 'react'
import { riskStyle } from '../utils/format'

const LEAFLET_VERSION = '1.9.4'
const CSS_URL = `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.css`
const JS_URL = `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.js`
const LOAD_TIMEOUT_MS = 6000

/** Co-location radius used by the duplicate detector (config.DUPLICATE_DISTANCE_KM). */
const DUPLICATE_RADIUS_M = 3000

let leafletPromise = null

/** Load Leaflet once per page, whichever component asks for it first. */
function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L)
  if (leafletPromise) return leafletPromise

  leafletPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Leaflet load timed out')), LOAD_TIMEOUT_MS)

    if (!document.querySelector(`link[href="${CSS_URL}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = CSS_URL
      document.head.appendChild(link)
    }

    const script = document.createElement('script')
    script.src = JS_URL
    script.async = true
    script.onload = () => {
      clearTimeout(timer)
      window.L ? resolve(window.L) : reject(new Error('Leaflet did not initialise'))
    }
    script.onerror = () => {
      clearTimeout(timer)
      reject(new Error('Leaflet could not be fetched'))
    }
    document.head.appendChild(script)
  }).catch((err) => {
    // Allow a later mount to retry rather than caching the failure forever.
    leafletPromise = null
    throw err
  })

  return leafletPromise
}

export default function GisMap({ points = [], height = 300, onUnavailable }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    loadLeaflet()
      .then((L) => {
        if (cancelled || !containerRef.current || mapRef.current) return

        const origin = points.find((p) => p.isOrigin) || points[0]
        if (!origin) return

        const map = L.map(containerRef.current, {
          scrollWheelZoom: false,
          attributionControl: true,
        })
        mapRef.current = map

        L.tileLayer(`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`, {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        L.control.scale({ imperial: false }).addTo(map)

        // The radius within which two similar works count as co-located.
        L.circle([origin.lat, origin.lon], {
          radius: DUPLICATE_RADIUS_M,
          color: '#64748b',
          weight: 1,
          dashArray: '4 4',
          fillColor: '#94a3b8',
          fillOpacity: 0.06,
        })
          .addTo(map)
          .bindTooltip('3 km co-location radius used by duplicate detection')

        points.forEach((p) => {
          const colour = riskStyle(p.level).hex

          if (!p.isOrigin) {
            L.polyline(
              [
                [origin.lat, origin.lon],
                [p.lat, p.lon],
              ],
              { color: '#94a3b8', weight: 1, dashArray: '3 4' },
            ).addTo(map)
          }

          L.circleMarker([p.lat, p.lon], {
            radius: p.isOrigin ? 9 : 6,
            color: '#ffffff',
            weight: 2,
            fillColor: colour,
            fillOpacity: 1,
          })
            .addTo(map)
            .bindPopup(
              `<strong>${p.id}</strong><br/>${p.name}<br/>` +
                (p.isOrigin
                  ? '<em>This work</em>'
                  : `${p.distance} km away · risk ${Math.round(p.score ?? 0)} (${p.level})`),
            )
        })

        const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon]))
        map.fitBounds(bounds.pad(0.35), { maxZoom: 14 })
        // A lone point yields a degenerate bounding box, so set a sane zoom.
        if (points.length === 1) map.setView([origin.lat, origin.lon], 13)

        // The container is sized by CSS after mount; Leaflet needs telling.
        setTimeout(() => map.invalidateSize(), 0)
      })
      .catch(() => {
        if (cancelled) return
        setFailed(true)
        onUnavailable?.()
      })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
    // Points are derived from an immutable analysis payload for this work.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (failed) return null

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full rounded border border-ink-200 bg-ink-50"
      role="img"
      aria-label="Basemap showing this work and nearby works"
    />
  )
}
