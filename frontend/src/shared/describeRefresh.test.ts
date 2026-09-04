import { describe, expect, it } from 'vitest'
import { describeRefresh } from './describeRefresh.ts'

describe('describeRefresh', () => {
  it('reports in-flight refetches as still refreshing', () => {
    expect(describeRefresh({ queue: 'loading', 'audit trail': 'loading' })).toBe(
      'refreshing queue and audit trail…',
    )
  })

  it('reports refreshed only once every refetch settled successfully', () => {
    expect(describeRefresh({ queue: 'success', 'audit trail': 'empty' })).toBe(
      'queue and audit trail refreshed.',
    )
  })

  it('names a failed refetch instead of calling it refreshed', () => {
    expect(describeRefresh({ list: 'success', 'audit trail': 'error' })).toBe(
      'audit trail refresh failed; list refreshed.',
    )
    expect(describeRefresh({ list: 'error', 'audit trail': 'error' })).toBe(
      'list and audit trail refresh failed.',
    )
  })

  it('mixes settled, failed, and in-flight parts in a stable order', () => {
    expect(describeRefresh({ queue: 'error', 'audit trail': 'loading' })).toBe(
      'queue refresh failed; refreshing audit trail…',
    )
    expect(describeRefresh({ queue: 'success', 'audit trail': 'loading' })).toBe(
      'queue refreshed; refreshing audit trail…',
    )
  })
})
