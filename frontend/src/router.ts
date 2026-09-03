import { useEffect, useState } from 'react'

export type Route =
  | { page: 'refunds'; refundId: string | null }
  | { page: 'feature-flags' }
  | { page: 'audit' }

export const DEFAULT_HASH = '#/refunds'

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#/, '')
  const segments = path.split('/').filter(Boolean)
  switch (segments[0]) {
    case 'feature-flags':
      return { page: 'feature-flags' }
    case 'audit':
      return { page: 'audit' }
    case 'refunds':
      return { page: 'refunds', refundId: segments[1] ? decodeURIComponent(segments[1]) : null }
    default:
      return { page: 'refunds', refundId: null }
  }
}

export function refundHash(refundId: string | null): string {
  return refundId ? `#/refunds/${encodeURIComponent(refundId)}` : '#/refunds'
}

export function navigate(hash: string): void {
  if (window.location.hash === hash) return
  window.location.hash = hash
}

/** Tiny hash router: the URL is the single source of truth for page and selected refund. */
export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onChange)
    if (!window.location.hash) window.location.replace(DEFAULT_HASH)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return route
}
