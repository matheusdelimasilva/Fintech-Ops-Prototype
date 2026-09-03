import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { ROLE_LABELS, formatApprovalLimit } from '../shared/format.ts'
import { DEFAULT_USER_ID, useIdentity } from './context.ts'

export function UserSwitcher() {
  const { userId, setUserId, resetToDefault, session, reloadSession } = useIdentity()
  const roster = session.data?.available_users ?? []
  const current = session.status === 'success' ? session.data : null

  return (
    <section className="user-switcher" aria-labelledby="user-switcher-heading">
      <h2 id="user-switcher-heading" className="visually-hidden">
        Demo user
      </h2>
      <div className="user-switcher-row">
        <label htmlFor="demo-user-select">Acting as</label>
        {roster.length > 0 ? (
          <select
            id="demo-user-select"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
          >
            {roster.map((user) => (
              <option key={user.id} value={user.id}>
                {user.display_name} — {ROLE_LABELS[user.role]}
              </option>
            ))}
            {!roster.some((user) => user.id === userId) && (
              <option value={userId}>{userId} (unknown)</option>
            )}
          </select>
        ) : (
          <output id="demo-user-select">
            <code>{userId}</code>
          </output>
        )}
      </div>
      <dl className="user-switcher-facts">
        <div>
          <dt>Role</dt>
          <dd>{current ? ROLE_LABELS[current.user.role] : '…'}</dd>
        </div>
        <div>
          <dt>Refund approval limit</dt>
          <dd>{current ? formatApprovalLimit(current.policy.approval_limit_cents) : '…'}</dd>
        </div>
        <div>
          <dt>May escalate refunds</dt>
          <dd>{current ? (current.policy.can_escalate_refunds ? 'Yes' : 'No') : '…'}</dd>
        </div>
      </dl>
      {session.status === 'loading' && (
        <p role="status" className="muted">
          Resolving identity on the server…
        </p>
      )}
      {session.status === 'error' && (
        <div className="user-switcher-error">
          <ErrorNotice error={session.error} onRetry={reloadSession} />
          {userId !== DEFAULT_USER_ID && (
            <button type="button" onClick={resetToDefault}>
              Reset to Sam Support
            </button>
          )}
        </div>
      )}
    </section>
  )
}
