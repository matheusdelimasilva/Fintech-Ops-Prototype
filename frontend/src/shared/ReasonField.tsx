import { useId } from 'react'

interface Props {
  label: string
  value: string
  onChange: (value: string) => void
  help: string
  disabled?: boolean
  autoFocus?: boolean
}

/**
 * The required free-text reason every mutation carries. Blank reasons are blocked by the
 * submitting form for UX only; the backend validates length and content and remains the authority.
 */
export function ReasonField({ label, value, onChange, help, disabled, autoFocus }: Props) {
  const reasonId = useId()
  const helpId = useId()
  return (
    <div className="field">
      <label htmlFor={reasonId}>{label} (required)</label>
      <textarea
        id={reasonId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={helpId}
        aria-required="true"
        disabled={disabled}
        autoFocus={autoFocus}
      />
      <p id={helpId} className="field-help">
        {help}
      </p>
    </div>
  )
}
