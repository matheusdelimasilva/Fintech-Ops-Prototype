import { describe, expect, it } from 'vitest'
import {
  formatApprovalLimit,
  formatDate,
  formatEnabled,
  formatMoney,
  formatRollout,
  formatTimestamp,
  humanizeKey,
} from './format.ts'

describe('formatMoney', () => {
  it.each([
    [0, '$0.00'],
    [1, '$0.01'],
    [50000, '$500.00'],
    [50001, '$500.01'],
    [500000, '$5,000.00'],
    [500001, '$5,000.01'],
    [123456789, '$1,234,567.89'],
    [-250, '-$2.50'],
  ])('formats %i cents as %s', (cents, expected) => {
    expect(formatMoney(cents, 'USD')).toBe(expected)
  })

  it('does not lose precision on amounts that are inexact as floats', () => {
    // 0.1 + 0.2 style trap: 29 cents is 0.29 which is not exactly representable.
    expect(formatMoney(29, 'USD')).toBe('$0.29')
    expect(formatMoney(1005, 'USD')).toBe('$10.05')
  })
})

describe('formatApprovalLimit', () => {
  it('renders null as Unlimited', () => {
    expect(formatApprovalLimit(null)).toBe('Unlimited')
    expect(formatApprovalLimit(500000)).toBe('$5,000.00')
  })
})

describe('formatTimestamp', () => {
  it('renders backend UTC timestamps as UTC regardless of viewer time zone', () => {
    expect(formatTimestamp('2026-08-30T14:05:09Z')).toBe('2026-08-30 14:05:09 UTC')
    expect(formatTimestamp('2026-08-30T14:05:09.123456Z')).toBe('2026-08-30 14:05:09 UTC')
    expect(formatDate('2026-08-30T23:59:59Z')).toBe('2026-08-30')
  })

  it('passes through unparseable input instead of showing Invalid Date', () => {
    expect(formatTimestamp('not-a-date')).toBe('not-a-date')
  })
})

describe('feature flag formatters', () => {
  it('labels enabled state and rollout', () => {
    expect(formatEnabled(true)).toBe('Enabled')
    expect(formatEnabled(false)).toBe('Disabled')
    expect(formatRollout(0)).toBe('0%')
    expect(formatRollout(100)).toBe('100%')
  })
})

describe('humanizeKey', () => {
  it('turns snake_case into a sentence-case label', () => {
    expect(humanizeKey('last_action_by')).toBe('Last action by')
  })
})
