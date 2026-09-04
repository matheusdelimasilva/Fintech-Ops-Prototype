import { useId, useState } from 'react'
import type { FeatureFlag, FeatureFlagPatch } from '../api/types.ts'
import { ReasonField } from '../shared/ReasonField.tsx'
import { decidePatch, draftFromFlag } from './buildFlagPatch.ts'

interface Props {
  flag: FeatureFlag
  pending: boolean
  onConfirm: (patch: FeatureFlagPatch) => void
  onCancel: () => void
}

const HELP: Record<Exclude<ReturnType<typeof decidePatch>['kind'], 'ready'>, string> = {
  no_change: 'Change the enabled state or rollout to enable Confirm.',
  rollout_not_a_number: 'Rollout must be a number.',
  reason_required: 'A reason is required.',
  confirmation_required: 'Tick the production confirmation to enable Confirm.',
}

/**
 * Edit form for one flag. Rendered only when the server said `can_edit`; the server re-checks
 * authorization and production confirmation on submit. Rollout bounds are not enforced here so
 * an out-of-range value reaches the backend and its 422 is shown through the shared error path.
 */
export function FeatureFlagEditForm({ flag, pending, onConfirm, onCancel }: Props) {
  const [draft, setDraft] = useState(() => draftFromFlag(flag))
  const enabledId = useId()
  const rolloutId = useId()
  const rolloutHelpId = useId()
  const confirmId = useId()
  const confirmHelpId = useId()

  const decision = decidePatch(flag, draft)
  const ready = decision.kind === 'ready'

  return (
    <form
      className="action-form"
      aria-label={`Edit ${flag.key} (${flag.environment})`}
      onSubmit={(event) => {
        event.preventDefault()
        if (decision.kind === 'ready' && !pending) onConfirm(decision.patch)
      }}
    >
      <div className="field field-inline">
        <input
          id={enabledId}
          type="checkbox"
          checked={draft.enabled}
          disabled={pending}
          onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
        />
        <label htmlFor={enabledId}>Enabled</label>
      </div>

      <div className="field">
        <label htmlFor={rolloutId}>Rollout percentage</label>
        <input
          id={rolloutId}
          type="number"
          inputMode="numeric"
          className="rollout-input"
          value={draft.rolloutText}
          disabled={pending}
          aria-describedby={rolloutHelpId}
          onChange={(event) => setDraft({ ...draft, rolloutText: event.target.value })}
        />
        <p id={rolloutHelpId} className="field-help">
          Whole number from 0 to 100; the server validates the range.
        </p>
      </div>

      <ReasonField
        label="Reason for this change"
        value={draft.reason}
        onChange={(reason) => setDraft({ ...draft, reason })}
        help="Recorded in the audit trail with the before/after state. Must not be blank."
        disabled={pending}
      />

      {flag.requires_confirmation && (
        <div className="production-confirm" role="group" aria-labelledby={confirmHelpId}>
          <p id={confirmHelpId} className="production-confirm-title">
            This changes a <strong>production</strong> flag.
          </p>
          <p className="field-help">
            Prototype only: no real system is affected. The server refuses production changes
            that do not carry this explicit confirmation.
          </p>
          <div className="field-inline">
            <input
              id={confirmId}
              type="checkbox"
              checked={draft.confirmProduction}
              disabled={pending}
              onChange={(event) => setDraft({ ...draft, confirmProduction: event.target.checked })}
            />
            <label htmlFor={confirmId}>I confirm this production change</label>
          </div>
        </div>
      )}

      {!ready && (
        <p className="field-help" role="status">
          {HELP[decision.kind]}
        </p>
      )}

      <div className="button-row">
        <button
          type="submit"
          className={flag.requires_confirmation ? 'danger' : undefined}
          disabled={!ready || pending}
        >
          {pending ? 'Saving…' : 'Confirm change'}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={pending}>
          Cancel
        </button>
      </div>
    </form>
  )
}
