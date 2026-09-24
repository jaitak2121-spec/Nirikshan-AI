/**
 * A small data-fetching hook.
 *
 * Deliberately hand-rolled rather than pulling in a query library: the app has
 * a handful of screens, and every one of them needs exactly the same three
 * states — loading, error, data. Keeping that in one place means no screen can
 * forget to handle one of them.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

export function useApi(fetcher, deps = [], { enabled = true } = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(enabled)
  const [reloadToken, setReloadToken] = useState(0)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return undefined
    }

    const controller = new AbortController()
    setLoading(true)
    setError(null)

    fetcher({ signal: controller.signal })
      .then((result) => {
        if (!mounted.current || controller.signal.aborted) return
        setData(result)
        setError(null)
      })
      .catch((err) => {
        if (!mounted.current || err?.name === 'AbortError') return
        setError(err)
      })
      .finally(() => {
        if (!mounted.current || controller.signal.aborted) return
        setLoading(false)
      })

    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, reloadToken])

  const reload = useCallback(() => setReloadToken((n) => n + 1), [])

  return { data, error, loading, reload }
}

export default useApi
