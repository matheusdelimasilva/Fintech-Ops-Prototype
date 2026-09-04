import { useEffect, useState } from 'react'
import type { AuditAction, AuditListFilters, EntityType } from './api/types.ts'
import { AUDIT_ACTION_LABELS, ENTITY_TYPE_LABELS } from './shared/format.ts'

export type Route =
  | { page: 'refunds'; refundId: string | null }
  | { page: 'feature-flags'; flagId: string | null }
  | { page: 'audit'; filters: AuditListFilters }

export const DEFAULT_HASH = '#/refunds'

/** Fired by `replaceHash`, which bypasses `hashchange`. */
const ROUTE_REPLACED_EVENT = 'app:route-replaced'

const ENTITY_TYPES = new Set<string>(Object.keys(ENTITY_TYPE_LABELS))
const AUDIT_ACTIONS = new Set<string>(Object.keys(AUDIT_ACTION_LABELS))

/** Query-string order is fixed so equal filters always produce the same hash. */
const AUDIT_FILTER_KEYS = ['entity_type', 'entity_id', 'actor', 'action'] as const

export function parseHash(hash: string): Route {
  const [path = '', query = ''] = hash.replace(/^#/, '').split('?', 2)
  const segments = path.split('/').filter(Boolean)
  switch (segments[0]) {
    case 'feature-flags':
      return { page: 'feature-flags', flagId: segments[1] ? decodeURIComponent(segments[1]) : null }
    case 'audit':
      return { page: 'audit', filters: parseAuditFilters(new URLSearchParams(query)) }
    case 'refunds':
      return { page: 'refunds', refundId: segments[1] ? decodeURIComponent(segments[1]) : null }
    default:
      return { page: 'refunds', refundId: null }
  }
}

/**
 * Enum-valued filters are validated here so a hand-edited URL never leaves a `<select>` blank
 * while the API keeps answering 422; free-text filters pass through untouched (the server still
 * validates them on every call).
 */
function parseAuditFilters(params: URLSearchParams): AuditListFilters {
  const filters: AuditListFilters = {}
  const entityType = params.get('entity_type')
  if (entityType && ENTITY_TYPES.has(entityType)) filters.entity_type = entityType as EntityType
  const entityId = params.get('entity_id')?.trim()
  if (entityId) filters.entity_id = entityId
  const actor = params.get('actor')?.trim()
  if (actor) filters.actor = actor
  const action = params.get('action')
  if (action && AUDIT_ACTIONS.has(action)) filters.action = action as AuditAction
  return filters
}

export function refundHash(refundId: string | null): string {
  return refundId ? `#/refunds/${encodeURIComponent(refundId)}` : '#/refunds'
}

export function featureFlagHash(flagId: string | null): string {
  return flagId ? `#/feature-flags/${encodeURIComponent(flagId)}` : '#/feature-flags'
}

export function auditHash(filters: AuditListFilters = {}): string {
  const params = new URLSearchParams()
  for (const key of AUDIT_FILTER_KEYS) {
    const value = filters[key]
    if (value) params.set(key, value)
  }
  const query = params.toString()
  return query ? `#/audit?${query}` : '#/audit'
}

/** Detail page for an audited entity, or `null` when the UI has no page for that type. */
export function entityHash(entityType: string, entityId: string): string | null {
  switch (entityType) {
    case 'refund':
      return refundHash(entityId)
    case 'feature_flag':
      return featureFlagHash(entityId)
    default:
      return null
  }
}

export function navigate(hash: string): void {
  if (window.location.hash === hash) return
  window.location.hash = hash
}

/** Like `navigate` but without a history entry — for filter edits, so Back is not per keystroke. */
export function replaceHash(hash: string): void {
  if (window.location.hash === hash) return
  window.history.replaceState(window.history.state, '', hash)
  window.dispatchEvent(new Event(ROUTE_REPLACED_EVENT))
}

/** Tiny hash router: the URL is the single source of truth for page, selected record, and filters. */
export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onChange)
    window.addEventListener(ROUTE_REPLACED_EVENT, onChange)
    if (!window.location.hash) window.location.replace(DEFAULT_HASH)
    return () => {
      window.removeEventListener('hashchange', onChange)
      window.removeEventListener(ROUTE_REPLACED_EVENT, onChange)
    }
  }, [])

  return route
}
