import { describe, expect, it } from 'vitest'
import type { FeatureFlag } from '../api/types.ts'
import { decidePatch, draftFromFlag } from './buildFlagPatch.ts'

const staging: FeatureFlag = {
  id: 'flag_bulk_export_staging',
  key: 'bulk_export',
  description: 'Allow CSV export of the refund queue.',
  environment: 'staging',
  enabled: true,
  rollout_percent: 50,
  updated_at: '2026-08-05T16:20:00Z',
  can_edit: true,
  requires_confirmation: false,
}

const production: FeatureFlag = {
  ...staging,
  id: 'flag_new_risk_scoring_production',
  environment: 'production',
  rollout_percent: 10,
  requires_confirmation: true,
}

describe('decidePatch', () => {
  it('starts from the loaded flag and reports no change until something differs', () => {
    const draft = draftFromFlag(staging)
    expect(draft).toEqual({ enabled: true, rolloutText: '50', reason: '', confirmProduction: false })
    expect(decidePatch(staging, draft)).toEqual({ kind: 'no_change' })
    expect(decidePatch(staging, { ...draft, rolloutText: ' 50 ', reason: 'x' })).toEqual({
      kind: 'no_change',
    })
  })

  it('requires a non-blank reason once a field changed', () => {
    const draft = { ...draftFromFlag(staging), enabled: false }
    expect(decidePatch(staging, draft)).toEqual({ kind: 'reason_required' })
    expect(decidePatch(staging, { ...draft, reason: '   \n' })).toEqual({ kind: 'reason_required' })
  })

  it('sends only the fields that differ, with the reason trimmed', () => {
    const base = draftFromFlag(staging)
    expect(decidePatch(staging, { ...base, enabled: false, reason: ' off ' })).toEqual({
      kind: 'ready',
      patch: { enabled: false, reason: 'off' },
    })
    expect(decidePatch(staging, { ...base, rolloutText: '75', reason: 'wider' })).toEqual({
      kind: 'ready',
      patch: { rollout_percent: 75, reason: 'wider' },
    })
    expect(
      decidePatch(staging, { ...base, enabled: false, rolloutText: '0', reason: 'kill' }),
    ).toEqual({ kind: 'ready', patch: { enabled: false, rollout_percent: 0, reason: 'kill' } })
  })

  it.each(['-1', '101', '12.5', '100', '0'])(
    'lets the backend judge rollout %s instead of validating range or integer-ness',
    (text) => {
      const draft = { ...draftFromFlag(staging), rolloutText: text, reason: 'r' }
      expect(decidePatch(staging, draft)).toEqual({
        kind: 'ready',
        patch: { rollout_percent: Number(text), reason: 'r' },
      })
    },
  )

  it('blocks only a rollout that is not a number at all', () => {
    const base = draftFromFlag(staging)
    expect(decidePatch(staging, { ...base, rolloutText: '', reason: 'r' })).toEqual({
      kind: 'rollout_not_a_number',
    })
    expect(decidePatch(staging, { ...base, rolloutText: 'abc', reason: 'r' })).toEqual({
      kind: 'rollout_not_a_number',
    })
  })

  it('gates production on the server-provided requires_confirmation flag', () => {
    const draft = { ...draftFromFlag(production), enabled: false, reason: 'incident' }
    expect(decidePatch(production, draft)).toEqual({ kind: 'confirmation_required' })
    expect(decidePatch(production, { ...draft, confirmProduction: true })).toEqual({
      kind: 'ready',
      patch: { enabled: false, reason: 'incident', confirm_production: true },
    })
  })

  it('never sends confirm_production when the server did not ask for confirmation', () => {
    const draft = { ...draftFromFlag(staging), enabled: false, reason: 'r', confirmProduction: true }
    expect(decidePatch(staging, draft)).toEqual({
      kind: 'ready',
      patch: { enabled: false, reason: 'r' },
    })
  })
})
