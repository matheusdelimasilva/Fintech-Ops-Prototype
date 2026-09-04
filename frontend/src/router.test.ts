import { describe, expect, it } from 'vitest'
import { featureFlagHash, parseHash, refundHash } from './router.ts'

describe('parseHash', () => {
  it.each([
    ['', { page: 'refunds', refundId: null }],
    ['#', { page: 'refunds', refundId: null }],
    ['#/', { page: 'refunds', refundId: null }],
    ['#/refunds', { page: 'refunds', refundId: null }],
    ['#/refunds/', { page: 'refunds', refundId: null }],
    ['#/refunds/rfnd_003', { page: 'refunds', refundId: 'rfnd_003' }],
    ['#/feature-flags', { page: 'feature-flags', flagId: null }],
    ['#/feature-flags/', { page: 'feature-flags', flagId: null }],
    ['#/feature-flags/flag_x', { page: 'feature-flags', flagId: 'flag_x' }],
    ['#/audit', { page: 'audit' }],
    ['#/nonsense/xyz', { page: 'refunds', refundId: null }],
  ])('parses %j', (hash, route) => {
    expect(parseHash(hash)).toEqual(route)
  })

  it('round-trips refund ids through refundHash', () => {
    expect(parseHash(refundHash('rfnd_003'))).toEqual({ page: 'refunds', refundId: 'rfnd_003' })
    expect(refundHash(null)).toBe('#/refunds')
  })

  it('round-trips flag ids through featureFlagHash', () => {
    expect(parseHash(featureFlagHash('flag_x'))).toEqual({ page: 'feature-flags', flagId: 'flag_x' })
    expect(featureFlagHash(null)).toBe('#/feature-flags')
  })
})
