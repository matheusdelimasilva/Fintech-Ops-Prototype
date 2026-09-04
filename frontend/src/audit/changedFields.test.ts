import { describe, expect, it } from 'vitest'
import { changedFields, formatSnapshotValue } from './changedFields.ts'

describe('changedFields', () => {
  it('lists only keys whose values differ, in before-then-after key order', () => {
    const before = {
      id: 'rfnd_003',
      refund_status: 'pending',
      last_action: null,
      last_action_by: null,
      updated_at: '2026-08-01T00:00:00Z',
    }
    const after = {
      id: 'rfnd_003',
      refund_status: 'escalated',
      last_action: 'refund.escalated',
      last_action_by: 'Sam Support',
      updated_at: '2026-08-30T14:05:09Z',
    }
    expect(changedFields(before, after)).toEqual([
      { key: 'refund_status', before: 'pending', after: 'escalated' },
      { key: 'last_action', before: null, after: 'refund.escalated' },
      { key: 'last_action_by', before: null, after: 'Sam Support' },
      { key: 'updated_at', before: '2026-08-01T00:00:00Z', after: '2026-08-30T14:05:09Z' },
    ])
  })

  it('includes keys present on only one side', () => {
    expect(changedFields({ a: 1 }, { b: 2 })).toEqual([
      { key: 'a', before: 1, after: undefined },
      { key: 'b', before: undefined, after: 2 },
    ])
  })

  it('returns nothing for identical snapshots', () => {
    expect(changedFields({ a: [1, 2] }, { a: [1, 2] })).toEqual([])
  })
})

describe('formatSnapshotValue', () => {
  it('renders null/undefined as a dash and objects as JSON', () => {
    expect(formatSnapshotValue(null)).toBe('—')
    expect(formatSnapshotValue(undefined)).toBe('—')
    expect(formatSnapshotValue('pending')).toBe('pending')
    expect(formatSnapshotValue(42)).toBe('42')
    expect(formatSnapshotValue({ a: 1 })).toBe('{"a":1}')
  })
})
