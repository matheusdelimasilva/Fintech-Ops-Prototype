import { useState } from 'react'
import { ApiError, NETWORK_ERROR } from '../api/client.ts'
import type { AuditEvent, Refund, RefundAction } from '../api/types.ts'
import { AuditEventList } from '../audit/AuditEventList.tsx'
import { useApiClient } from '../identity/context.ts'
import { navigate, refundHash } from '../router.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { AUDIT_ACTION_LABELS, REFUND_ACTION_LABELS, formatTimestamp } from '../shared/format.ts'
import { EmptyState, LoadingState } from '../shared/States.tsx'
import { StatusBanner } from '../shared/StatusBanner.tsx'
import { useQuery } from '../shared/useQuery.ts'
import { RefundActionForm } from './RefundActionForm.tsx'
import { RefundDetail } from './RefundDetail.tsx'

interface Props {
  refundId: string
  /** Called after a successful mutation so the parent can refresh the queue. */
  onMutated: () => void
}

const isEmptyList = (events: AuditEvent[]) => events.length === 0

/** Mounted per refund id (keyed by the parent) so no state leaks between refunds. */
export function RefundDetailPanel({ refundId, onMutated }: Props) {
  const client = useApiClient()
  const detail = useQuery((signal) => client.getRefund(refundId, signal), refundId)
  const audit = useQuery(
    (signal) => client.listRefundAuditEvents(refundId, signal),
    refundId,
    { isEmpty: isEmptyList },
  )

  const [openAction, setOpenAction] = useState<RefundAction | null>(null)
  const [pending, setPending] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const [success, setSuccess] = useState<Refund | null>(null)

  const refund = detail.state.data
  const allowedActions = refund?.allowed_actions ?? []

  // A form for an action the server no longer offers (e.g. after a 409 refresh) is stale.
  const activeForm = openAction && allowedActions.includes(openAction) ? openAction : null

  async function perform(action: RefundAction, reason: string) {
    setPending(true)
    setActionError(null)
    setSuccess(null)
    try {
      const updated = await client.performRefundAction(refundId, action, reason)
      detail.setData(() => updated)
      setSuccess(updated)
      setOpenAction(null)
      audit.reload()
      onMutated()
    } catch (error: unknown) {
      const apiError =
        error instanceof ApiError
          ? error
          : new ApiError(0, NETWORK_ERROR, 'Could not reach the backend.')
      setActionError(apiError)
      if (apiError.status === 409) {
        detail.reload()
        audit.reload()
      }
    } finally {
      setPending(false)
    }
  }

  if (detail.state.status === 'error') {
    return (
      <>
        <ErrorNotice error={detail.state.error} onRetry={detail.reload} />
        <button type="button" className="secondary" onClick={() => navigate(refundHash(null))}>
          Back to queue
        </button>
      </>
    )
  }
  if (refund === undefined) {
    return <LoadingState label="Loading refund…" />
  }

  return (
    <>
      {success && success.last_action && (
        <StatusBanner onDismiss={() => setSuccess(null)}>
          <strong>{AUDIT_ACTION_LABELS[success.last_action]}</strong> by {success.last_action_by}
          {success.last_action_at && (
            <>
              {' '}
              at <time dateTime={success.last_action_at}>{formatTimestamp(success.last_action_at)}</time>
            </>
          )}
          . Queue, detail, and audit trail refreshed.
        </StatusBanner>
      )}
      {actionError && (
        <ErrorNotice
          error={actionError}
          onDismiss={() => setActionError(null)}
          onRetry={
            actionError.status === 409
              ? () => {
                  setActionError(null)
                  detail.reload()
                  audit.reload()
                }
              : undefined
          }
        />
      )}
      {detail.state.status === 'loading' && (
        <p role="status" className="muted">
          Refreshing refund…
        </p>
      )}

      <RefundDetail refund={refund} />

      <section aria-labelledby="actions-heading">
        <h3 id="actions-heading">Actions</h3>
        {allowedActions.length > 0 ? (
          <div className="button-row">
            {allowedActions.map((action) => (
              <button
                key={action}
                type="button"
                className={action === 'reject' ? 'danger' : undefined}
                aria-pressed={activeForm === action}
                disabled={pending}
                onClick={() => {
                  setActionError(null)
                  setSuccess(null)
                  setOpenAction(activeForm === action ? null : action)
                }}
              >
                {REFUND_ACTION_LABELS[action]}
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">No actions are available to you for this refund.</p>
        )}
        <p className="field-help">
          Available actions are determined by server policy for the acting user and the refund's
          current status. The server re-checks every action when it is submitted.
        </p>
        {activeForm && (
          <RefundActionForm
            key={activeForm}
            action={activeForm}
            pending={pending}
            onConfirm={(reason) => void perform(activeForm, reason)}
            onCancel={() => setOpenAction(null)}
          />
        )}
      </section>

      <section aria-labelledby="audit-heading">
        <h3 id="audit-heading">Audit trail</h3>
        {audit.state.status === 'loading' && audit.state.data === undefined && (
          <LoadingState label="Loading audit events…" />
        )}
        {audit.state.status === 'error' && (
          <ErrorNotice error={audit.state.error} onRetry={audit.reload} />
        )}
        {audit.state.status === 'empty' && (
          <EmptyState title="No audit events yet">
            <p className="muted">Actions on this refund will appear here with before/after state.</p>
          </EmptyState>
        )}
        {audit.state.data !== undefined && audit.state.data.length > 0 && (
          <AuditEventList events={audit.state.data} />
        )}
      </section>
    </>
  )
}
