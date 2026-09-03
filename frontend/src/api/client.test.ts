import { describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  IDENTITY_HEADER,
  INVALID_RESPONSE,
  NETWORK_ERROR,
  createApiClient,
  parseResponse,
} from './client.ts'

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

async function capture(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (error) {
    if (error instanceof ApiError) return error
    throw error
  }
  throw new Error('expected the promise to reject')
}

describe('parseResponse', () => {
  it('returns the JSON body for 2xx responses', async () => {
    await expect(parseResponse(json(200, { ok: true }))).resolves.toEqual({ ok: true })
  })

  it('maps the backend error envelope onto ApiError', async () => {
    const error = await capture(
      parseResponse(
        json(403, {
          error: {
            code: 'APPROVAL_LIMIT_EXCEEDED',
            message: 'Amount exceeds your approval limit.',
            details: { approval_limit_cents: 50000 },
          },
        }),
      ),
    )
    expect(error).toMatchObject({
      status: 403,
      code: 'APPROVAL_LIMIT_EXCEEDED',
      message: 'Amount exceeds your approval limit.',
      details: { approval_limit_cents: 50000 },
    })
  })

  it('defaults details to an empty object when the envelope omits them', async () => {
    const error = await capture(
      parseResponse(json(401, { error: { code: 'MISSING_IDENTITY', message: 'x' } })),
    )
    expect(error.details).toEqual({})
  })

  it('classifies a non-JSON HTTP error as INVALID_RESPONSE and keeps the status', async () => {
    const error = await capture(
      parseResponse(new Response('<html>Bad Gateway</html>', { status: 502 })),
    )
    expect(error.status).toBe(502)
    expect(error.code).toBe(INVALID_RESPONSE)
  })

  it('classifies a non-JSON 200 as INVALID_RESPONSE with status 200', async () => {
    const error = await capture(parseResponse(new Response('not json', { status: 200 })))
    expect(error).toMatchObject({ status: 200, code: INVALID_RESPONSE })
  })

  it('classifies JSON without the envelope shape as INVALID_RESPONSE', async () => {
    const error = await capture(parseResponse(json(500, { detail: 'plain fastapi error' })))
    expect(error).toMatchObject({ status: 500, code: INVALID_RESPONSE })
  })
})

describe('createApiClient', () => {
  it('sends only the identity header about the caller', async () => {
    const fetchImpl = vi.fn(async () => json(200, []))
    const client = createApiClient('user_sam_support', fetchImpl, 'http://api.test')

    await client.listRefunds({ status: 'pending', search: '' })

    expect(fetchImpl).toHaveBeenCalledTimes(1)
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://api.test/api/refunds?status=pending')
    const headers = init.headers as Record<string, string>
    expect(headers[IDENTITY_HEADER]).toBe('user_sam_support')
    expect(Object.keys(headers).sort()).toEqual(['Accept', IDENTITY_HEADER].sort())
    expect(init.body).toBeUndefined()
  })

  it('posts refund actions as {reason} JSON', async () => {
    const fetchImpl = vi.fn(async () => json(200, { id: 'rfnd_003' }))
    const client = createApiClient('user_olivia_ops', fetchImpl, 'http://api.test')

    await client.performRefundAction('rfnd_003', 'approve', 'Verified with customer')

    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://api.test/api/refunds/rfnd_003/approve')
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ reason: 'Verified with customer' }))
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
  })

  it('classifies a rejected fetch as NETWORK_ERROR with status 0', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    const client = createApiClient('user_sam_support', fetchImpl, 'http://api.test')
    const error = await capture(client.getSession())
    expect(error).toMatchObject({ status: 0, code: NETWORK_ERROR })
  })

  it('lets AbortError propagate untouched so stale requests are ignored, not shown', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new DOMException('aborted', 'AbortError')
    })
    const client = createApiClient('user_sam_support', fetchImpl, 'http://api.test')
    await expect(client.getSession()).rejects.toMatchObject({ name: 'AbortError' })
  })
})
