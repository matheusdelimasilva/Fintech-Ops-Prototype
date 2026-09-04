import { useState } from 'react'
import type { RefundAction } from '../api/types.ts'
import { ReasonField } from '../shared/ReasonField.tsx'
import { REFUND_ACTION_LABELS, REFUND_ACTION_TONE } from '../shared/format.ts'

interface Props {
  action: RefundAction
  pending: boolean
  onConfirm: (reason: string) => void
  onCancel: () => void
}

/** Inline confirmation with a required reason; the backend re-validates everything. */
export function RefundActionForm({ action, pending, onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState('')
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
      <ReasonField
        label={`Reason for ${label.toLowerCase()}`}
        value={reason}
        onChange={setReason}
        help="Recorded on the refund and in the audit trail. Must not be blank."
        disabled={pending}
        autoFocus
      />
      <div className="button-row">
        <button
          type="submit"
          className={REFUND_ACTION_TONE[action]}
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
