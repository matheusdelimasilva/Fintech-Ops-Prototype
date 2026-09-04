import { useEffect, useState } from 'react'
import type { AuditAction, AuditEvent, AuditListFilters, EntityType } from '../api/types.ts'
import { useApiClient, useIdentity } from '../identity/context.ts'
import { auditHash, replaceHash } from '../router.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { AUDIT_ACTION_LABELS, ENTITY_TYPE_LABELS } from '../shared/format.ts'
import { EmptyState, LoadingState } from '../shared/States.tsx'
import { useQuery } from '../shared/useQuery.ts'
import { AuditEventList } from './AuditEventList.tsx'

interface Props {
  /** Parsed from the hash by the router, which already dropped invalid enum values. */
  filters: AuditListFilters
}

const ENTITY_ID_DEBOUNCE_MS = 300
const ENTITY_TYPES = Object.keys(ENTITY_TYPE_LABELS) as EntityType[]
const AUDIT_ACTIONS = Object.keys(AUDIT_ACTION_LABELS) as AuditAction[]
const isEmptyList = (events: AuditEvent[]) => events.length === 0

/** Filter edits replace the current history entry so Back never walks through keystrokes. */
function applyFilters(next: AuditListFilters) {
  replaceHash(auditHash(next))
}

function hasAnyFilter(filters: AuditListFilters): boolean {
  return Boolean(filters.entity_type || filters.entity_id || filters.actor || filters.action)
}

function AuditFilters({ filters }: Props) {
  const { session } = useIdentity()
  const roster = session.data?.available_users ?? []
  const actorInRoster = filters.actor === undefined || roster.some((u) => u.id === filters.actor)

  const [entityIdText, setEntityIdText] = useState(filters.entity_id ?? '')
  const [seenEntityId, setSeenEntityId] = useState(filters.entity_id)

  // Adjust the draft when the filter changes from outside the input (Clear, a link, Back).
  if (filters.entity_id !== seenEntityId) {
    setSeenEntityId(filters.entity_id)
    const committed = filters.entity_id ?? ''
    if (entityIdText.trim() !== committed) setEntityIdText(committed)
  }

  useEffect(() => {
    const trimmed = entityIdText.trim()
    if (trimmed === (filters.entity_id ?? '')) return
    const handle = window.setTimeout(
      () => applyFilters({ ...filters, entity_id: trimmed || undefined }),
      ENTITY_ID_DEBOUNCE_MS,
    )
    return () => window.clearTimeout(handle)
  }, [entityIdText, filters])

  return (
    <form
      className="filters"
      role="search"
      aria-label="Audit filters"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="field filters-compact">
        <label htmlFor="audit-entity-type">Entity type</label>
        <select
          id="audit-entity-type"
          value={filters.entity_type ?? ''}
          onChange={(event) =>
            applyFilters({
              ...filters,
              entity_type: (event.target.value || undefined) as EntityType | undefined,
            })
          }
        >
          <option value="">All</option>
          {ENTITY_TYPES.map((type) => (
            <option key={type} value={type}>
              {ENTITY_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>
      <div className="field filters-search">
        <label htmlFor="audit-entity-id">Entity ID</label>
        <input
          id="audit-entity-id"
          type="search"
          placeholder="rfnd_003, flag_…"
          value={entityIdText}
          onChange={(event) => setEntityIdText(event.target.value)}
        />
      </div>
      <div className="field filters-compact">
        <label htmlFor="audit-actor">Actor</label>
        <select
          id="audit-actor"
          value={filters.actor ?? ''}
          onChange={(event) => applyFilters({ ...filters, actor: event.target.value || undefined })}
        >
          <option value="">All</option>
          {roster.map((user) => (
            <option key={user.id} value={user.id}>
              {user.display_name}
            </option>
          ))}
          {!actorInRoster && filters.actor && (
            <option value={filters.actor}>{filters.actor} (not in roster)</option>
          )}
        </select>
      </div>
      <div className="field filters-compact">
        <label htmlFor="audit-action">Action</label>
        <select
          id="audit-action"
          value={filters.action ?? ''}
          onChange={(event) =>
            applyFilters({
              ...filters,
              action: (event.target.value || undefined) as AuditAction | undefined,
            })
          }
        >
          <option value="">All</option>
          {AUDIT_ACTIONS.map((action) => (
            <option key={action} value={action}>
              {AUDIT_ACTION_LABELS[action]}
            </option>
          ))}
        </select>
      </div>
      {hasAnyFilter(filters) && (
        <button
          type="button"
          className="link"
          onClick={() => {
            setEntityIdText('')
            applyFilters({})
          }}
        >
          Clear filters
        </button>
      )}
    </form>
  )
}

export function AuditTrailPage({ filters }: Props) {
  const client = useApiClient()
  const events = useQuery(
    (signal) => client.listAuditEvents(filters, signal),
    JSON.stringify(filters),
    { isEmpty: isEmptyList },
  )

  const loading = events.state.status === 'loading'
  const settled = events.state.status === 'success' || events.state.status === 'empty'
  const count = events.state.data?.length

  return (
    <section className="panel" aria-labelledby="audit-trail-heading">
      <h1 id="audit-trail-heading">Audit Trail</h1>
      <p className="muted">
        Every successful refund action and feature-flag change, newest first. Events are append-only
        through the application; this page is read-only and filters are applied by the server.
      </p>
      <div className="queue-toolbar">
        <AuditFilters filters={filters} />
        <div className="audit-toolbar-status">
          <p className="result-count" role="status">
            {settled && count !== undefined && (count === 1 ? '1 event' : `${count} events`)}
          </p>
          <button type="button" className="secondary" onClick={events.reload} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>
      {loading && events.state.data === undefined && <LoadingState label="Loading audit events…" />}
      {events.state.status === 'error' && (
        <ErrorNotice error={events.state.error} onRetry={events.reload} />
      )}
      {events.state.status === 'empty' && (
        <EmptyState title={hasAnyFilter(filters) ? 'No events match' : 'No audit events yet'}>
          {hasAnyFilter(filters) ? (
            <p className="muted">Try clearing a filter.</p>
          ) : (
            <p className="muted">Refund actions and feature-flag changes will appear here.</p>
          )}
        </EmptyState>
      )}
      {events.state.data !== undefined && events.state.data.length > 0 && (
        <>
          {loading && <p className="muted">Refreshing…</p>}
          <AuditEventList events={events.state.data} showEntity />
        </>
      )}
    </section>
  )
}
