import { useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type BackendStatus =
  | { kind: 'loading' }
  | { kind: 'ok'; service: string }
  | { kind: 'error'; message: string }

function App() {
  const [status, setStatus] = useState<BackendStatus>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false

    fetch(`${API_BASE_URL}/health`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`)
        }
        return (await response.json()) as { status: string; service: string }
      })
      .then((body) => {
        if (!cancelled) {
          setStatus({ kind: 'ok', service: body.service })
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unknown error'
          setStatus({ kind: 'error', message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main>
      <p role="note" className="banner">
        Prototype only. All identities and business data are synthetic.
      </p>
      <h1>Fintech Ops Console</h1>
      <p>
        Placeholder shell. Refund Operations, Feature Flags, and Audit Trail are not implemented
        yet.
      </p>
      <section aria-labelledby="backend-status-heading">
        <h2 id="backend-status-heading">Backend status</h2>
        {status.kind === 'loading' && <p>Checking backend health…</p>}
        {status.kind === 'ok' && <p>Healthy: {status.service}</p>}
        {status.kind === 'error' && <p role="alert">Unreachable: {status.message}</p>}
      </section>
    </main>
  )
}

export default App
