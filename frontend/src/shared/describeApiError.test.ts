import { describe, expect, it } from 'vitest'
import { ApiError, INVALID_RESPONSE, NETWORK_ERROR, UNEXPECTED_ERROR } from '../api/client.ts'
import { describeApiError } from './describeApiError.ts'

describe('describeApiError', () => {
  it('presents a 403 approval-limit denial with money-formatted details', () => {
    const presentation = describeApiError(
      new ApiError(403, 'APPROVAL_LIMIT_EXCEEDED', 'Amount exceeds your approval limit.', {
        approval_limit_cents: 50000,
        amount_cents: 50001,
        role: 'support_agent',
      }),
    )
    expect(presentation.heading).toBe('Not permitted')
    expect(presentation.body).toBe('Amount exceeds your approval limit.')
    expect(presentation.details).toEqual([
      { label: 'Approval limit cents', value: '$500.00' },
      { label: 'Amount cents', value: '$500.01' },
      { label: 'Role', value: 'support_agent' },
    ])
    expect(presentation.suggestsRefresh).toBe(false)
  })

  it('decides from status/code, not message text', () => {
    const misleading = describeApiError(
      new ApiError(403, 'ACTION_NOT_PERMITTED_FOR_ROLE', 'Refund has changed. Check your input.'),
    )
    expect(misleading.heading).toBe('Not permitted')
  })

  it.each([
    [401, 'Identity not recognized'],
    [404, 'Not found'],
    [409, 'Record has changed'],
    [422, 'Check your input'],
    [500, 'Something went wrong'],
  ])('maps HTTP %i to "%s"', (status, heading) => {
    expect(describeApiError(new ApiError(status, 'ANY', 'msg')).heading).toBe(heading)
  })

  it('suggests a refresh only for 409', () => {
    expect(describeApiError(new ApiError(409, 'INVALID_STATE_TRANSITION', 'x')).suggestsRefresh).toBe(
      true,
    )
    expect(describeApiError(new ApiError(422, 'VALIDATION_ERROR', 'x')).suggestsRefresh).toBe(false)
  })

  it('flattens 422 validation errors into field/message rows', () => {
    const presentation = describeApiError(
      new ApiError(422, 'VALIDATION_ERROR', 'Request validation failed.', {
        errors: [{ loc: ['body', 'reason'], msg: 'String should have at most 1000 characters' }],
      }),
    )
    expect(presentation.details).toEqual([
      { label: 'Reason', value: 'String should have at most 1000 characters' },
    ])
  })

  it('names client-side classifications regardless of status', () => {
    expect(describeApiError(new ApiError(0, NETWORK_ERROR, 'x')).heading).toBe('Backend unreachable')
    expect(describeApiError(new ApiError(502, INVALID_RESPONSE, 'x')).heading).toBe(
      'Unexpected response from the backend',
    )
    expect(describeApiError(new ApiError(0, UNEXPECTED_ERROR, 'x')).heading).toBe(
      'Something went wrong in the app',
    )
  })
})
