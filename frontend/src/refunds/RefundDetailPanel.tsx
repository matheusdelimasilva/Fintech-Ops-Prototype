import { useApiClient } from '../identity/context.ts'
import { navigate, refundHash } from '../router.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { LoadingState } from '../shared/States.tsx'
import { useQuery } from '../shared/useQuery.ts'
import { RefundDetail } from './RefundDetail.tsx'

interface Props {
  refundId: string
}

/** Mounted per refund id (keyed by the parent) so no state leaks between refunds. */
export function RefundDetailPanel({ refundId }: Props) {
  const client = useApiClient()
  const detail = useQuery((signal) => client.getRefund(refundId, signal), refundId)

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
  if (detail.state.data === undefined) {
    return <LoadingState label="Loading refund…" />
  }
  return <RefundDetail refund={detail.state.data} />
}
