import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { createApiClient } from '../api/client.ts'
import { useQuery } from '../shared/useQuery.ts'
import { DEFAULT_USER_ID, IdentityContext, type IdentityContextValue } from './context.ts'

const STORAGE_KEY = 'fintech-ops-console.demo-user-id'

function readStoredUserId(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? DEFAULT_USER_ID
  } catch {
    return DEFAULT_USER_ID
  }
}

function storeUserId(userId: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, userId)
  } catch {
    // Persistence is a convenience; the in-memory value still drives requests.
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [userId, setUserIdState] = useState<string>(readStoredUserId)
  const client = useMemo(() => createApiClient(userId), [userId])
  const { state: session, reload: reloadSession } = useQuery(
    (signal) => client.getSession(signal),
    userId,
  )

  const setUserId = useCallback((next: string) => {
    storeUserId(next)
    setUserIdState(next)
  }, [])
  const resetToDefault = useCallback(() => setUserId(DEFAULT_USER_ID), [setUserId])

  const value = useMemo<IdentityContextValue>(
    () => ({ userId, setUserId, resetToDefault, client, session, reloadSession }),
    [userId, setUserId, resetToDefault, client, session, reloadSession],
  )

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}
