import { describe, expect, it } from 'vitest'
import { auditHash, entityHash, featureFlagHash, parseHash, refundHash } from './router.ts'

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
    ['#/audit', { page: 'audit', filters: {} }],
    ['#/audit?', { page: 'audit', filters: {} }],
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

describe('audit filters in the hash', () => {
  it('parses every supported filter', () => {
    expect(
      parseHash(
        '#/audit?entity_type=refund&entity_id=rfnd_003&actor=user_sam_support&action=refund.approved',
      ),
    ).toEqual({
      page: 'audit',
      filters: {
        entity_type: 'refund',
        entity_id: 'rfnd_003',
        actor: 'user_sam_support',
        action: 'refund.approved',
      },
    })
  })

  it('drops invalid enum values but keeps free-text filters', () => {
    expect(parseHash('#/audit?entity_type=bogus&action=nope&entity_id=rfnd_003&actor=x')).toEqual({
      page: 'audit',
      filters: { entity_id: 'rfnd_003', actor: 'x' },
    })
  })

  it('drops blank and whitespace-only free-text filters', () => {
    expect(parseHash('#/audit?entity_id=&actor=%20%20')).toEqual({ page: 'audit', filters: {} })
  })

  it('serializes with fixed key order, omitting empty values and encoding', () => {
    expect(auditHash()).toBe('#/audit')
    expect(auditHash({ entity_id: '', actor: undefined })).toBe('#/audit')
    expect(
      auditHash({ action: 'feature_flag.updated', entity_type: 'feature_flag', actor: 'a b&c' }),
    ).toBe('#/audit?entity_type=feature_flag&actor=a+b%26c&action=feature_flag.updated')
  })

  it('round-trips filters through auditHash', () => {
    const filters = {
      entity_type: 'feature_flag',
      entity_id: 'flag_bulk_export_staging',
      actor: 'user_olivia_ops',
      action: 'feature_flag.updated',
    } as const
    expect(parseHash(auditHash(filters))).toEqual({ page: 'audit', filters })
    expect(parseHash(auditHash({ actor: 'a b&c' }))).toEqual({
      page: 'audit',
      filters: { actor: 'a b&c' },
    })
  })
})

describe('entityHash', () => {
  it('maps known entity types to their detail pages', () => {
    expect(entityHash('refund', 'rfnd_003')).toBe('#/refunds/rfnd_003')
    expect(entityHash('feature_flag', 'flag_x')).toBe('#/feature-flags/flag_x')
  })

  it('returns null for entity types the UI has no page for', () => {
    expect(entityHash('ledger_entry', 'le_1')).toBeNull()
  })
})
