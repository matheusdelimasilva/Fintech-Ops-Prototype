import { useCallback, useEffect, useRef, useState } from 'react'
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
 * Minimal fetch-on-change hook. `key` identifies the request (identity, filters, ids…); when it
 * changes, the in-flight request is aborted via the AbortSignal handed to the fetcher so late
 * responses never overwrite fresh state. The latest `fetcher` is always used.
 */
export function useQuery<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  key: string,
  options: QueryOptions<T> = {},
): QueryResult<T> {
  const { isEmpty, enabled = true } = options
  const [state, setState] = useState<QueryState<T>>({ status: 'loading', data: undefined })
  const [version, setVersion] = useState(0)
  const latestData = useRef<T | undefined>(undefined)
  const fetcherRef = useRef(fetcher)
  const isEmptyRef = useRef(isEmpty)
  // Declared before the fetch effect so React runs it first on every commit.
  useEffect(() => {
    fetcherRef.current = fetcher
    isEmptyRef.current = isEmpty
  })

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    setState({ status: 'loading', data: latestData.current })

    fetcherRef
      .current(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        latestData.current = data
        setState(
          isEmptyRef.current?.(data) ? { status: 'empty', data } : { status: 'success', data },
        )
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
  }, [key, version, enabled])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback((updater: (previous: T | undefined) => T) => {
    const data = updater(latestData.current)
    latestData.current = data
    setState(isEmptyRef.current?.(data) ? { status: 'empty', data } : { status: 'success', data })
  }, [])

  return { state, reload, setData }
}
