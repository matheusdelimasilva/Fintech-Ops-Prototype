import { useEffect, useState } from 'react'
import type { RefundListFilters, RefundStatus, RiskLevel } from '../api/types.ts'
import { REFUND_STATUS_LABELS, RISK_LABELS } from '../shared/format.ts'

interface Props {
  filters: RefundListFilters
  onChange: (filters: RefundListFilters) => void
}

const SEARCH_DEBOUNCE_MS = 300
const STATUSES = Object.keys(REFUND_STATUS_LABELS) as RefundStatus[]
const RISKS = Object.keys(RISK_LABELS) as RiskLevel[]

export function RefundFilters({ filters, onChange }: Props) {
  const [searchText, setSearchText] = useState(filters.search ?? '')

  useEffect(() => {
    const trimmed = searchText.trim()
    if (trimmed === (filters.search ?? '')) return
    const handle = window.setTimeout(
      () => onChange({ ...filters, search: trimmed || undefined }),
      SEARCH_DEBOUNCE_MS,
    )
    return () => window.clearTimeout(handle)
  }, [searchText, filters, onChange])

  return (
    <form
      className="filters"
      role="search"
      aria-label="Refund filters"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="field">
        <label htmlFor="refund-search">Search</label>
        <input
          id="refund-search"
          type="search"
          placeholder="Customer, reference…"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="refund-status">Status</label>
        <select
          id="refund-status"
          value={filters.status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              status: (event.target.value || undefined) as RefundStatus | undefined,
            })
          }
        >
          <option value="">All</option>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {REFUND_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="refund-risk">Risk</label>
        <select
          id="refund-risk"
          value={filters.risk_level ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              risk_level: (event.target.value || undefined) as RiskLevel | undefined,
            })
          }
        >
          <option value="">All</option>
          {RISKS.map((risk) => (
            <option key={risk} value={risk}>
              {RISK_LABELS[risk]}
            </option>
          ))}
        </select>
      </div>
      {(filters.search || filters.status || filters.risk_level) && (
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setSearchText('')
            onChange({})
          }}
        >
          Clear filters
        </button>
      )}
    </form>
  )
}
