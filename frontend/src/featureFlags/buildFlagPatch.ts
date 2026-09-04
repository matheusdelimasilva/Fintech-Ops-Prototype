import type { FeatureFlag, FeatureFlagPatch } from '../api/types.ts'

export interface FlagDraft {
  enabled: boolean
  /** Raw input text so the server, not the browser, decides what a valid rollout is. */
  rolloutText: string
  reason: string
  confirmProduction: boolean
}

export function draftFromFlag(flag: FeatureFlag): FlagDraft {
  return {
    enabled: flag.enabled,
    rolloutText: String(flag.rollout_percent),
    reason: '',
    confirmProduction: false,
  }
}

export type PatchDecision =
  | { kind: 'no_change' }
  | { kind: 'rollout_not_a_number' }
  | { kind: 'reason_required' }
  | { kind: 'confirmation_required' }
  | { kind: 'ready'; patch: FeatureFlagPatch }

/**
 * Pure decision for the edit form: which fields differ from the loaded flag and whether the form
 * may be submitted. Only client-side *gating* lives here (blank reason, unticked production
 * confirmation, a rollout that is not a number at all); range and integer validation of the
 * rollout are deliberately left to the backend so its 422 path stays reachable from the UI
 * (-1, 101, and 12.5 are all sent).
 */
export function decidePatch(flag: FeatureFlag, draft: FlagDraft): PatchDecision {
  const patch: FeatureFlagPatch = { reason: draft.reason.trim() }

  if (draft.enabled !== flag.enabled) patch.enabled = draft.enabled

  const rolloutText = draft.rolloutText.trim()
  const rollout = rolloutText === '' ? Number.NaN : Number(rolloutText)
  if (!Number.isFinite(rollout)) return { kind: 'rollout_not_a_number' }
  if (rollout !== flag.rollout_percent) patch.rollout_percent = rollout

  if (patch.enabled === undefined && patch.rollout_percent === undefined) return { kind: 'no_change' }
  if (patch.reason === '') return { kind: 'reason_required' }
  if (flag.requires_confirmation) {
    if (!draft.confirmProduction) return { kind: 'confirmation_required' }
    patch.confirm_production = true
  }
  return { kind: 'ready', patch }
}
