import type { QueryState } from './useQuery.ts'

export type RefreshStatus = QueryState<unknown>['status']

/**
 * Sentence fragment for a success banner describing the follow-up refetches a mutation
 * triggered, keyed by a human label ("queue", "audit trail"). A refetch is only reported as
 * refreshed once its query has actually settled successfully; failures are named, never
 * folded into "refreshed".
 */
export function describeRefresh(parts: Record<string, RefreshStatus>): string {
  const failed: string[] = []
  const done: string[] = []
  const loading: string[] = []
  for (const [label, status] of Object.entries(parts)) {
    if (status === 'loading') loading.push(label)
    else if (status === 'error') failed.push(label)
    else done.push(label)
  }
  const segments: string[] = []
  if (failed.length > 0) segments.push(`${joinLabels(failed)} refresh failed`)
  if (done.length > 0) segments.push(`${joinLabels(done)} refreshed`)
  if (loading.length > 0) segments.push(`refreshing ${joinLabels(loading)}…`)
  const sentence = segments.join('; ')
  return sentence.endsWith('…') ? sentence : `${sentence}.`
}

function joinLabels(labels: string[]): string {
  if (labels.length <= 1) return labels.join('')
  return `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`
}
