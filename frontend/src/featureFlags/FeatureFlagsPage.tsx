import { useState } from 'react'
import type { Environment, FeatureFlag, FeatureFlagListFilters } from '../api/types.ts'
import { useApiClient } from '../identity/context.ts'
import { ErrorNotice } from '../shared/ErrorNotice.tsx'
import { ENVIRONMENT_LABELS } from '../shared/format.ts'
import { EmptyState, LoadingState } from '../shared/States.tsx'
import { useQuery } from '../shared/useQuery.ts'
import { FeatureFlagDetailPanel } from './FeatureFlagDetailPanel.tsx'
import { FeatureFlagTable } from './FeatureFlagTable.tsx'

interface Props {
  selectedId: string | null
}

const ENVIRONMENTS = Object.keys(ENVIRONMENT_LABELS) as Environment[]
const isEmptyList = (flags: FeatureFlag[]) => flags.length === 0

export function FeatureFlagsPage({ selectedId }: Props) {
  const client = useApiClient()
  const [filters, setFilters] = useState<FeatureFlagListFilters>({})

  const list = useQuery(
    (signal) => client.listFeatureFlags(filters, signal),
    JSON.stringify(filters),
    { isEmpty: isEmptyList },
  )

  return (
    <div className="split">
      <section className="panel" aria-labelledby="flags-heading">
        <h1 id="flags-heading">Feature Flags</h1>
        <p className="muted">
          Synthetic flags for staging and production. Nothing here controls a real system.
        </p>
        <form
          className="filters"
          aria-label="Feature flag filters"
          onSubmit={(event) => event.preventDefault()}
        >
          <div className="field">
            <label htmlFor="flag-environment">Environment</label>
            <select
              id="flag-environment"
              value={filters.environment ?? ''}
              onChange={(event) =>
                setFilters({
                  environment: (event.target.value || undefined) as Environment | undefined,
                })
              }
            >
              <option value="">All</option>
              {ENVIRONMENTS.map((environment) => (
                <option key={environment} value={environment}>
                  {ENVIRONMENT_LABELS[environment]}
                </option>
              ))}
            </select>
          </div>
        </form>
        {list.state.status === 'loading' && list.state.data === undefined && (
          <LoadingState label="Loading feature flags…" />
        )}
        {list.state.status === 'error' && (
          <ErrorNotice error={list.state.error} onRetry={list.reload} />
        )}
        {list.state.status === 'empty' && (
          <EmptyState title="No flags match">
            <p className="muted">Try a different environment filter.</p>
          </EmptyState>
        )}
        {list.state.data !== undefined && list.state.data.length > 0 && (
          <>
            {list.state.status === 'loading' && (
              <p role="status" className="muted">
                Refreshing…
              </p>
            )}
            <FeatureFlagTable flags={list.state.data} selectedId={selectedId} />
          </>
        )}
      </section>

      <section className="panel" aria-labelledby="flag-detail-heading">
        <h2 id="flag-detail-heading">Flag detail</h2>
        {selectedId === null ? (
          <EmptyState title="No flag selected">
            <p className="muted">Choose a flag from the list to see its state and audit trail.</p>
          </EmptyState>
        ) : (
          <FeatureFlagDetailPanel
            key={selectedId}
            flagId={selectedId}
            reloadList={list.reload}
            listStatus={list.state.status}
          />
        )}
      </section>
    </div>
  )
}
