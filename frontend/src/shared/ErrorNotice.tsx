import type { ApiError } from '../api/client.ts'
import { describeApiError } from './describeApiError.ts'

interface Props {
  error: ApiError
  onRetry?: () => void
  onDismiss?: () => void
}

export function ErrorNotice({ error, onRetry, onDismiss }: Props) {
  const presentation = describeApiError(error)
  return (
    <div role="alert" className="notice notice-error">
      <div className="notice-body">
        <strong>{presentation.heading}</strong>
        <p>{presentation.body}</p>
        {presentation.details.length > 0 && (
          <dl className="details-list">
            {presentation.details.map((item, index) => (
              <div key={`${item.label}-${index}`}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="muted">
          <code>
            {error.code}
            {error.status > 0 ? ` (HTTP ${error.status})` : ''}
          </code>
        </p>
      </div>
      <div className="notice-actions">
        {onRetry && (
          <button type="button" onClick={onRetry}>
            {presentation.suggestsRefresh ? 'Refresh' : 'Retry'}
          </button>
        )}
        {onDismiss && (
          <button type="button" className="secondary" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  )
}
