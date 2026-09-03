import { ApiError, INVALID_RESPONSE, NETWORK_ERROR } from '../api/client.ts'
import { formatMoney, humanizeKey } from './format.ts'

export interface ErrorPresentation {
  heading: string
  /** The backend's own message, shown verbatim as supporting text. */
  body: string
  /** Structured details rendered as a definition list; already formatted for display. */
  details: Array<{ label: string; value: string }>
  /** Whether the caller should refetch the affected resource to show the current server state. */
  suggestsRefresh: boolean
}

/**
 * Pure mapping from an ApiError to what the UI shows. Decisions are made on `status` and
 * `code` only; the message text is displayed, never interpreted.
 */
export function describeApiError(error: ApiError): ErrorPresentation {
  return {
    heading: headingFor(error),
    body: error.message,
    details: detailsFor(error),
    suggestsRefresh: error.status === 409,
  }
}

function headingFor(error: ApiError): string {
  if (error.code === NETWORK_ERROR) return 'Backend unreachable'
  if (error.code === INVALID_RESPONSE) return 'Unexpected response from the backend'
  switch (error.status) {
    case 401:
      return 'Identity not recognized'
    case 403:
      return 'Not permitted'
    case 404:
      return 'Not found'
    case 409:
      return 'Refund has changed'
    case 422:
      return 'Check your input'
    default:
      return 'Something went wrong'
  }
}

function detailsFor(error: ApiError): Array<{ label: string; value: string }> {
  const out: Array<{ label: string; value: string }> = []
  const { details } = error

  if (error.status === 422 && Array.isArray(details.errors)) {
    for (const item of details.errors) {
      if (typeof item === 'object' && item !== null) {
        const record = item as Record<string, unknown>
        const loc = Array.isArray(record.loc) ? record.loc.filter((p) => p !== 'body').join('.') : ''
        const msg = typeof record.msg === 'string' ? record.msg : JSON.stringify(record)
        out.push({ label: loc ? humanizeKey(loc) : 'Field', value: msg })
      }
    }
    return out
  }

  for (const [key, value] of Object.entries(details)) {
    if (value === undefined || value === null) continue
    out.push({ label: humanizeKey(key), value: formatDetailValue(key, value) })
  }
  return out
}

function formatDetailValue(key: string, value: unknown): string {
  if (typeof value === 'number' && key.endsWith('_cents')) return formatMoney(value, 'USD')
  if (Array.isArray(value)) return value.map(String).join(', ')
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}
