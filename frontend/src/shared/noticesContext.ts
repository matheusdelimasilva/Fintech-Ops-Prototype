import { createContext, useContext } from 'react'
import type { AuditAction } from '../api/types.ts'

/** A completed mutation, recorded from the server's response so it can be shown until dismissed. */
export interface CompletedAction {
  action: AuditAction
  actor: string | null
  at: string | null
}

export interface NoticesContextValue {
  /** Keyed by entity, e.g. `refund:rfnd_003`. */
  notices: Record<string, CompletedAction>
  record: (key: string, notice: CompletedAction) => void
  dismiss: (key: string) => void
}

export const NoticesContext = createContext<NoticesContextValue | null>(null)

export function useNotices(): NoticesContextValue {
  const value = useContext(NoticesContext)
  if (value === null) throw new Error('useNotices must be used within NoticesProvider')
  return value
}

export function noticeKey(entityType: string, id: string): string {
  return `${entityType}:${id}`
}
