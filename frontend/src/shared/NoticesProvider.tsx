import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { NoticesContext, type CompletedAction } from './noticesContext.ts'

/**
 * Holds success notices above the routed pages so they outlive navigation, refund switches, and
 * identity changes. A notice disappears only when the user dismisses it or starts another action
 * on the same entity.
 */
export function NoticesProvider({ children }: { children: ReactNode }) {
  const [notices, setNotices] = useState<Record<string, CompletedAction>>({})

  const record = useCallback((key: string, notice: CompletedAction) => {
    setNotices((current) => ({ ...current, [key]: notice }))
  }, [])

  const dismiss = useCallback((key: string) => {
    setNotices((current) => {
      if (!(key in current)) return current
      const { [key]: _removed, ...rest } = current
      return rest
    })
  }, [])

  const value = useMemo(() => ({ notices, record, dismiss }), [notices, record, dismiss])

  return <NoticesContext.Provider value={value}>{children}</NoticesContext.Provider>
}
