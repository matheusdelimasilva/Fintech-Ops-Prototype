import type {
  AuditEvent,
  FeatureFlag,
  Refund,
  RefundAction,
  RefundListFilters,
  Session,
} from './types.ts'

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export const IDENTITY_HEADER = 'X-Demo-User-Id'

/** Codes the client itself produces; every other code comes from the backend envelope. */
export const NETWORK_ERROR = 'NETWORK_ERROR'
export const INVALID_RESPONSE = 'INVALID_RESPONSE'
/** A failure that is neither an HTTP response nor a rejected fetch: a bug in the caller's code. */
export const UNEXPECTED_ERROR = 'UNEXPECTED_ERROR'

export class ApiError extends Error {
  /** HTTP status; 0 when the request never produced a response. */
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

/** Normalizes anything thrown along a request path; only `fetch` itself may produce NETWORK_ERROR. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  const message = error instanceof Error ? error.message : String(error)
  return new ApiError(0, UNEXPECTED_ERROR, message || 'An unexpected error occurred.')
}

interface ErrorEnvelope {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!isRecord(value) || !isRecord(value.error)) return false
  const { code, message, details } = value.error
  return (
    typeof code === 'string' &&
    typeof message === 'string' &&
    (details === undefined || isRecord(details))
  )
}

/**
 * Turns a fetch Response into either parsed JSON or an ApiError.
 * Exported so the classification rules can be unit-tested without a server.
 */
export async function parseResponse<T>(response: Response): Promise<T> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new ApiError(
      response.status,
      INVALID_RESPONSE,
      `The server returned a non-JSON response (HTTP ${response.status}).`,
    )
  }

  if (response.ok) return body as T

  if (isErrorEnvelope(body)) {
    throw new ApiError(response.status, body.error.code, body.error.message, body.error.details)
  }
  throw new ApiError(
    response.status,
    INVALID_RESPONSE,
    `The server returned an error without the expected envelope (HTTP ${response.status}).`,
  )
}

function toQuery(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, value)
  }
  const encoded = query.toString()
  return encoded ? `?${encoded}` : ''
}

export interface ApiClient {
  getSession(signal?: AbortSignal): Promise<Session>
  listRefunds(filters: RefundListFilters, signal?: AbortSignal): Promise<Refund[]>
  getRefund(refundId: string, signal?: AbortSignal): Promise<Refund>
  performRefundAction(refundId: string, action: RefundAction, reason: string): Promise<Refund>
  listRefundAuditEvents(refundId: string, signal?: AbortSignal): Promise<AuditEvent[]>
  listFeatureFlags(signal?: AbortSignal): Promise<FeatureFlag[]>
}

/**
 * Low-level client bound to one demo user id. The only thing sent about the caller is the
 * identity header; role, limits, and names are always resolved by the backend.
 */
export function createApiClient(
  userId: string,
  fetchImpl: typeof fetch = (...args) => fetch(...args),
  baseUrl: string = API_BASE_URL,
): ApiClient {
  async function request<T>(
    method: 'GET' | 'POST',
    path: string,
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json', [IDENTITY_HEADER]: userId }
    if (body !== undefined) headers['Content-Type'] = 'application/json'

    let response: Response
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      })
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      throw new ApiError(0, NETWORK_ERROR, 'Could not reach the backend.')
    }
    return parseResponse<T>(response)
  }

  return {
    getSession: (signal) => request('GET', '/api/session', undefined, signal),
    listRefunds: (filters, signal) =>
      request('GET', `/api/refunds${toQuery({ ...filters })}`, undefined, signal),
    getRefund: (refundId, signal) =>
      request('GET', `/api/refunds/${encodeURIComponent(refundId)}`, undefined, signal),
    performRefundAction: (refundId, action, reason) =>
      request('POST', `/api/refunds/${encodeURIComponent(refundId)}/${action}`, { reason }),
    listRefundAuditEvents: (refundId, signal) =>
      request(
        'GET',
        `/api/audit-events${toQuery({ entity_type: 'refund', entity_id: refundId })}`,
        undefined,
        signal,
      ),
    listFeatureFlags: (signal) => request('GET', '/api/feature-flags', undefined, signal),
  }
}
