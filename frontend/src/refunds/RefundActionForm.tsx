import { useId, useState } from 'react'
import type { RefundAction } from '../api/types.ts'
import { REFUND_ACTION_LABELS } from '../shared/format.ts'

interface Props {
  action: RefundAction
  pending: boolean
  onConfirm: (reason: string) => void
  onCancel: () => void
}

/**
 * Inline confirmation with a required reason. Blank reasons are blocked here for UX only; the
 * backend validates length and content and remains the authority.
 */
export function RefundActionForm({ action, pending, onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState('')
  const reasonId = useId()
  const helpId = useId()
  const trimmed = reason.trim()
  const label = REFUND_ACTION_LABELS[action]

  return (
    <form
      className="action-form"
      aria-label={`${label} refund`}
      onSubmit={(event) => {
        event.preventDefault()
        if (trimmed && !pending) onConfirm(trimmed)
      }}
    >
      <div className="field">
        <label htmlFor={reasonId}>Reason for {label.toLowerCase()} (required)</label>
        <textarea
          id={reasonId}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          aria-describedby={helpId}
          aria-required="true"
          disabled={pending}
          autoFocus
        />
        <p id={helpId} className="field-help">
          Recorded on the refund and in the audit trail. Must not be blank.
        </p>
      </div>
      <div className="button-row">
        <button
          type="submit"
          className={action === 'reject' ? 'danger' : undefined}
          disabled={!trimmed || pending}
        >
          {pending ? 'Submitting…' : `Confirm ${label.toLowerCase()}`}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={pending}>
          Cancel
        </button>
      </div>
    </form>
  )
}
