import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react'
import { ApiError, NETWORK_ERROR } from '../api/client.ts'

export type QueryState<T> =
  | { status: 'loading'; data: T | undefined }
  | { status: 'success'; data: T }
  | { status: 'empty'; data: T }
  | { status: 'error'; error: ApiError; data: T | undefined }

export interface QueryResult<T> {
  state: QueryState<T>
  /** Re-run the fetch; previous data stays visible while loading. */
  reload: () => void
  /** Replace the cached data without a network round trip (e.g. with a mutation response). */
  setData: (updater: (previous: T | undefined) => T) => void
}

export interface QueryOptions<T> {
  /** Distinguishes an empty result from a populated one; defaults to "never empty". */
  isEmpty?: (data: T) => boolean
  enabled?: boolean
}

/**
 * Minimal fetch-on-change hook. The fetcher receives an AbortSignal that is aborted when the
 * dependencies change or the component unmounts, so late responses never overwrite fresh state.
 */
export function useQuery<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
  options: QueryOptions<T> = {},
): QueryResult<T> {
  const { isEmpty, enabled = true } = options
  const [state, setState] = useState<QueryState<T>>({ status: 'loading', data: undefined })
  const [version, setVersion] = useState(0)
  const latestData = useRef<T | undefined>(undefined)

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    setState({ status: 'loading', data: latestData.current })

    fetcher(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        latestData.current = data
        setState(isEmpty?.(data) ? { status: 'empty', data } : { status: 'success', data })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const apiError =
          error instanceof ApiError
            ? error
            : new ApiError(0, NETWORK_ERROR, 'Could not reach the backend.')
        setState({ status: 'error', error: apiError, data: latestData.current })
      })

    return () => controller.abort()
  }, [...deps, version, enabled])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback(
    (updater: (previous: T | undefined) => T) => {
      const data = updater(latestData.current)
      latestData.current = data
      setState(isEmpty?.(data) ? { status: 'empty', data } : { status: 'success', data })
    },
    [isEmpty],
  )

  return { state, reload, setData }
}
