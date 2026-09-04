import { createContext, useContext } from 'react'
import type { ApiClient } from '../api/client.ts'
import type { Session } from '../api/types.ts'
import type { QueryState } from '../shared/useQuery.ts'

export const DEFAULT_USER_ID = 'user_sam_support'

export interface IdentityContextValue {
  /** The id the browser is currently sending; the server decides everything else. */
  userId: string
  setUserId: (userId: string) => void
  resetToDefault: () => void
  /** Client bound to `userId`; recreated whenever the identity changes. */
  client: ApiClient
  session: QueryState<Session>
  reloadSession: () => void
}

export const IdentityContext = createContext<IdentityContextValue | null>(null)

export function useIdentity(): IdentityContextValue {
  const value = useContext(IdentityContext)
  if (!value) throw new Error('useIdentity must be used inside <IdentityProvider>')
  return value
}

/** Context-bound client for data screens. Built on createApiClient, never the other way round. */
export function useApiClient(): ApiClient {
  return useIdentity().client
}
