import { useCallback, useState } from 'react'
import type { Refund, RefundListFilters } from '../api/types.ts'
import { useApiClient } from '../identity/context.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { EmptyState, LoadingState } from '../shared/States.tsx'
import { useQuery } from '../shared/useQuery.ts'
import { RefundDetailPanel } from './RefundDetailPanel.tsx'
import { RefundFilters } from './RefundFilters.tsx'
import { RefundQueue } from './RefundQueue.tsx'

interface Props {
  selectedId: string | null
}

const isEmptyList = (refunds: Refund[]) => refunds.length === 0

export function RefundsPage({ selectedId }: Props) {
  const client = useApiClient()
  const [filters, setFilters] = useState<RefundListFilters>({})
  const onFiltersChange = useCallback((next: RefundListFilters) => setFilters(next), [])

  const queue = useQuery(
    (signal) => client.listRefunds(filters, signal),
    JSON.stringify(filters),
    { isEmpty: isEmptyList },
  )

  const hasFilters = Boolean(filters.search || filters.status || filters.risk_level)
  const count = queue.state.data?.length

  return (
    <div className="split">
      <section className="panel" aria-labelledby="queue-heading">
        <h1 id="queue-heading">Refund Operations</h1>
        <div className="queue-toolbar">
          <RefundFilters filters={filters} onChange={onFiltersChange} />
          {count !== undefined && (
            <p className="result-count" role="status">
              {count === 1 ? '1 refund' : `${count} refunds`}
            </p>
          )}
        </div>
        {queue.state.status === 'loading' && queue.state.data === undefined && (
          <LoadingState label="Loading refunds…" />
        )}
        {queue.state.status === 'error' && (
          <ErrorNotice error={queue.state.error} onRetry={queue.reload} />
        )}
        {queue.state.status === 'empty' && (
          <EmptyState title="No refunds match">
            {hasFilters ? (
              <p className="muted">Try clearing a filter or a different search term.</p>
            ) : (
              <p className="muted">The queue is empty.</p>
            )}
          </EmptyState>
        )}
        {queue.state.data !== undefined && queue.state.data.length > 0 && (
          <>
            {queue.state.status === 'loading' && (
              <p role="status" className="muted">
                Refreshing…
              </p>
            )}
            <RefundQueue refunds={queue.state.data} selectedId={selectedId} />
          </>
        )}
      </section>

      <section className="panel panel-detail" aria-labelledby="detail-heading">
        <h2 id="detail-heading">Refund detail</h2>
        {selectedId === null ? (
          <EmptyState title="No refund selected">
            <p className="muted">Choose a refund from the queue to see its context and actions.</p>
          </EmptyState>
        ) : (
          <RefundDetailPanel
            key={selectedId}
            refundId={selectedId}
            reloadQueue={queue.reload}
            queueStatus={queue.state.status}
          />
        )}
      </section>
    </div>
  )
}
