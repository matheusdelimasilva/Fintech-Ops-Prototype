import { describe, expect, it } from 'vitest'
import { parseHash, refundHash } from './router.ts'

describe('parseHash', () => {
  it.each([
    ['', { page: 'refunds', refundId: null }],
    ['#', { page: 'refunds', refundId: null }],
    ['#/', { page: 'refunds', refundId: null }],
    ['#/refunds', { page: 'refunds', refundId: null }],
    ['#/refunds/', { page: 'refunds', refundId: null }],
    ['#/refunds/rfnd_003', { page: 'refunds', refundId: 'rfnd_003' }],
    ['#/feature-flags', { page: 'feature-flags' }],
    ['#/audit', { page: 'audit' }],
    ['#/nonsense/xyz', { page: 'refunds', refundId: null }],
  ])('parses %j', (hash, route) => {
    expect(parseHash(hash)).toEqual(route)
  })

  it('round-trips refund ids through refundHash', () => {
    expect(parseHash(refundHash('rfnd_003'))).toEqual({ page: 'refunds', refundId: 'rfnd_003' })
    expect(refundHash(null)).toBe('#/refunds')
  })
})
