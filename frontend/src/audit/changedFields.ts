import type { Snapshot } from '../api/types.ts'

export interface ChangedField {
  key: string
  before: unknown
  after: unknown
}

/** Keys whose value differs between the two snapshots, in the union key order (before first). */
export function changedFields(before: Snapshot, after: Snapshot): ChangedField[] {
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])]
  return keys
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .map((key) => ({ key, before: before[key], after: after[key] }))
}

export function formatSnapshotValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}
