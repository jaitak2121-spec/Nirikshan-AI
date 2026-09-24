/**
 * Synchronous stand-in for hooks/useApi.js, used only by the render test.
 *
 * The real hook fetches in an effect. renderToString does not run effects, so
 * this returns the loaded state directly, letting every page be rendered in its
 * populated state against recorded backend data.
 */
export default function useApi(factory) {
  const result = factory({})
  const data = result && typeof result === 'object' && '__fixture' in result ? result.__fixture : result
  return { data, error: null, loading: false, reload: () => {} }
}
