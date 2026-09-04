import { useState } from 'react'
import { ApiError, toApiError } from '../api/client.ts'
import type { AuditEvent, FeatureFlagPatch } from '../api/types.ts'
import { AuditEventList } from '../audit/AuditEventList.tsx'
import { useApiClient } from '../identity/context.ts'
import { featureFlagHash, navigate } from '../router.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { type RefreshStatus, describeRefresh } from '../shared/describeRefresh.ts'
import { AUDIT_ACTION_LABELS, formatTimestamp } from '../shared/format.ts'
import { EmptyState, LoadingState } from '../shared/States.tsx'
import { StatusBanner } from '../shared/StatusBanner.tsx'
import { noticeKey, useNotices } from '../shared/noticesContext.ts'
import { useQuery } from '../shared/useQuery.ts'
import { FeatureFlagDetail } from './FeatureFlagDetail.tsx'
import { FeatureFlagEditForm } from './FeatureFlagEditForm.tsx'

interface Props {
  flagId: string
  /** Called whenever the server reports a state this panel did not have (success or 409). */
  reloadList: () => void
  /** Status of the parent's list query, so the banner never claims a refresh it cannot see. */
  listStatus: RefreshStatus
}

const isEmptyList = (events: AuditEvent[]) => events.length === 0

/** Mounted per flag id (keyed by the parent) so no state leaks between flags. */
export function FeatureFlagDetailPanel({ flagId, reloadList, listStatus }: Props) {
  const client = useApiClient()
  const detail = useQuery((signal) => client.getFeatureFlag(flagId, signal), flagId)
  const audit = useQuery(
    (signal) => client.listAuditEvents('feature_flag', flagId, signal),
    flagId,
    { isEmpty: isEmptyList },
  )

  const [editing, setEditing] = useState(false)
  const [pending, setPending] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  const notices = useNotices()
  const successKey = noticeKey('feature_flag', flagId)
  const success = notices.notices[successKey]
  const dismissSuccess = () => notices.dismiss(successKey)

  const flag = detail.state.data
  const refreshSummary = describeRefresh({ list: listStatus, 'audit trail': audit.state.status })
  // The form is stale if the server stops offering edits (e.g. after an identity switch refetch).
  const showForm = editing && flag?.can_edit === true

  async function save(patch: FeatureFlagPatch) {
    setPending(true)
    setActionError(null)
    dismissSuccess()
    try {
      const updated = await client.updateFeatureFlag(flagId, patch)
      detail.setData(() => updated)
      // The flag carries no actor column; the refreshed audit list below is the authority on who.
      notices.record(successKey, {
        action: 'feature_flag.updated',
        actor: null,
        at: updated.updated_at,
      })
      setEditing(false)
      audit.reload()
      reloadList()
    } catch (error: unknown) {
      const apiError = toApiError(error)
      setActionError(apiError)
      if (apiError.status === 409) reloadAll()
    } finally {
      setPending(false)
    }
  }

  /** A 409 means the server holds state this page has not seen: refetch everything showing it. */
  function reloadAll() {
    detail.reload()
    audit.reload()
    reloadList()
  }

  if (detail.state.status === 'error') {
    return (
      <>
        <ErrorNotice error={detail.state.error} onRetry={detail.reload} />
        <button type="button" className="secondary" onClick={() => navigate(featureFlagHash(null))}>
          Back to flags
        </button>
      </>
    )
  }
  if (flag === undefined) {
    return <LoadingState label="Loading feature flag…" />
  }

  return (
    <>
      {success && (
        <StatusBanner onDismiss={dismissSuccess}>
          <strong>{AUDIT_ACTION_LABELS[success.action]}</strong>
          {success.at && (
            <>
              {' '}
              at <time dateTime={success.at}>{formatTimestamp(success.at)}</time>
            </>
          )}
          . Detail updated; {refreshSummary}
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
                  reloadAll()
                }
              : undefined
          }
        />
      )}
      {detail.state.status === 'loading' && (
        <p role="status" className="muted">
          Refreshing flag…
        </p>
      )}

      <FeatureFlagDetail flag={flag} />

      <section aria-labelledby="flag-actions-heading">
        <h3 id="flag-actions-heading">Actions</h3>
        {flag.can_edit ? (
          <div className="button-row">
            <button
              type="button"
              aria-pressed={showForm}
              disabled={pending}
              onClick={() => {
                setActionError(null)
                setEditing(!showForm)
              }}
            >
              Edit flag
            </button>
          </div>
        ) : (
          <p className="muted">You cannot edit this flag.</p>
        )}
        <p className="field-help">
          Edit availability is determined by server policy for the acting user and the flag's
          environment. The server re-checks permission and production confirmation on every save.
        </p>
        {showForm && (
          <FeatureFlagEditForm
            key={flag.updated_at}
            flag={flag}
            pending={pending}
            onConfirm={(patch) => void save(patch)}
            onCancel={() => setEditing(false)}
          />
        )}
      </section>

      <section aria-labelledby="flag-audit-heading">
        <h3 id="flag-audit-heading">Audit trail</h3>
        {audit.state.status === 'loading' && audit.state.data === undefined && (
          <LoadingState label="Loading audit events…" />
        )}
        {audit.state.status === 'error' && (
          <ErrorNotice error={audit.state.error} onRetry={audit.reload} />
        )}
        {audit.state.status === 'empty' && (
          <EmptyState title="No audit events yet">
            <p className="muted">Changes to this flag will appear here with before/after state.</p>
          </EmptyState>
        )}
        {audit.state.data !== undefined && audit.state.data.length > 0 && (
          <AuditEventList events={audit.state.data} />
        )}
      </section>
    </>
  )
}
