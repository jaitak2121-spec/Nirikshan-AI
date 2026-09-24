/**
 * Officer verification state for one work.
 *
 * A reviewer marks each risk signal they have checked and found explained,
 * directly on that signal. The adjusted score is recomputed by the engine
 * (POST /verify) rather than subtracted in the browser, so the figure on screen
 * comes from the same arithmetic that produced the original and can still be
 * reconstructed by hand from the breakdown.
 *
 * The state deliberately lives here — above every component on the page that
 * shows a score — so that ticking a signal moves the headline number, the band,
 * and the arithmetic table together. There is only ever one score on screen.
 *
 * Nothing is persisted and no finding is removed from the record. The adjusted
 * figure is a provisional working view; the determination rests with the
 * authorised officer.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function useVerification({
  projectId,
  anomalies = [],
  baseScore,
  baseLevel,
  baseRisk,
}) {
  // A stable key for "which signals are currently on the record". Re-running
  // the analysis can change that set, at which point old marks are meaningless.
  const signature = useMemo(
    () => anomalies.map((a) => a.type).filter(Boolean).join('|'),
    [anomalies],
  )

  const [cleared, setCleared] = useState(() => new Set())
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const toggle = useCallback((type) => {
    setCleared((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  const reset = useCallback(() => {
    setCleared((prev) => (prev.size ? new Set() : prev))
  }, [])

  // Drop marks that no longer refer to a detected signal. Guarded so a fresh
  // mount does not replace an already-empty Set and retrigger the fetch below.
  useEffect(() => {
    setCleared((prev) => (prev.size ? new Set() : prev))
    setResult(null)
    setError(null)
  }, [projectId, signature])

  // Recompute on every tick. With nothing marked there is nothing to ask the
  // server — the stored assessment already is the answer. The controller aborts
  // an in-flight request so a fast sequence of clicks cannot land out of order.
  useEffect(() => {
    if (!projectId || cleared.size === 0) {
      setBusy(false)
      return undefined
    }

    const controller = new AbortController()
    setBusy(true)
    setError(null)

    api
      .verify(projectId, [...cleared], { signal: controller.signal })
      .then((data) => {
        setResult(data)
        setBusy(false)
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError(err.message || 'Could not recompute the adjusted score.')
        setBusy(false)
      })

    return () => controller.abort()
  }, [projectId, cleared])

  // Show the adjusted figure only once the server has returned one, so the page
  // never displays a score the engine did not produce.
  const active = cleared.size > 0 && result != null && !error

  const risk = active
    ? {
        ...baseRisk,
        breakdown: result.breakdown,
        risk_score: result.adjusted_risk_score,
        raw_total: result.adjusted_raw_total,
        was_clamped: result.was_clamped,
      }
    : baseRisk

  return {
    cleared,
    toggle,
    reset,
    isCleared: (type) => cleared.has(type),
    active,
    busy,
    error,
    markCount: cleared.size,
    score: active ? result.adjusted_risk_score : baseScore,
    level: active ? result.adjusted_risk_level : baseLevel,
    withheld: active ? result.points_withheld : 0,
    bandChanged: active ? result.band_changed : false,
    risk,
    note: result?.note,
  }
}
