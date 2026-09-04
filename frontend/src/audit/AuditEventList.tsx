import type { AuditEvent } from '../api/types.ts'
import {
  AUDIT_ACTION_LABELS,
  ROLE_LABELS,
  formatTimestamp,
  humanizeKey,
} from '../shared/format.ts'
import { changedFields, formatSnapshotValue } from './changedFields.ts'

interface Props {
  events: AuditEvent[]
}

/** Domain-neutral audit rendering: newest first, changed fields up front, raw snapshots behind. */
export function AuditEventList({ events }: Props) {
  const ordered = [...events].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at))
  return (
    <ol className="audit-timeline" aria-label="Audit events, newest first">
      {ordered.map((event) => {
        const changes = changedFields(event.before_state, event.after_state)
        return (
          <li key={event.id} className="audit-event">
            <div className="audit-event-header">
              <strong>{AUDIT_ACTION_LABELS[event.action] ?? event.action}</strong>
              <time dateTime={event.occurred_at}>{formatTimestamp(event.occurred_at)}</time>
            </div>
            <p className="audit-event-meta">
              {event.actor_display_name}{' '}
              <span className="muted">
                ({ROLE_LABELS[event.actor_role] ?? event.actor_role}, <code>{event.actor_user_id}</code>)
              </span>
            </p>
            <p className="audit-event-meta">
              <span className="muted">Reason:</span> {event.reason}
            </p>
            {changes.length > 0 ? (
              <div className="table-scroll">
                <table className="compact-table" aria-label={`Changed fields for ${event.id}`}>
                  <thead>
                    <tr>
                      <th scope="col">Field</th>
                      <th scope="col">Before</th>
                      <th scope="col">After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {changes.map((change) => (
                      <tr key={change.key}>
                        <th scope="row">{humanizeKey(change.key)}</th>
                        <td>{formatSnapshotValue(change.before)}</td>
                        <td>{formatSnapshotValue(change.after)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="muted audit-event-meta">No field changes recorded.</p>
            )}
            <details>
              <summary>Raw before/after snapshots</summary>
              <div className="raw-json">
                <div>
                  <h4>Before</h4>
                  <pre>{JSON.stringify(event.before_state, null, 2)}</pre>
                </div>
                <div>
                  <h4>After</h4>
                  <pre>{JSON.stringify(event.after_state, null, 2)}</pre>
                </div>
              </div>
            </details>
          </li>
        )
      })}
    </ol>
  )
}
