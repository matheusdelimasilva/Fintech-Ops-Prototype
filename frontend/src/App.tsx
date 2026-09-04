import { FeatureFlagsPage } from './featureFlags/FeatureFlagsPage.tsx'
import { UserSwitcher } from './identity/UserSwitcher.tsx'
import { useIdentity } from './identity/context.ts'
import { RefundsPage } from './refunds/RefundsPage.tsx'
import { useHashRoute } from './router.ts'

const NAV_ITEMS = [
  { page: 'refunds', hash: '#/refunds', label: 'Refund Operations' },
  { page: 'feature-flags', hash: '#/feature-flags', label: 'Feature Flags' },
  { page: 'audit', hash: '#/audit', label: 'Audit Trail' },
] as const

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="panel" aria-labelledby="page-heading">
      <h1 id="page-heading">{title}</h1>
      <p className="muted">Not implemented in this checkpoint.</p>
    </section>
  )
}

function App() {
  const route = useHashRoute()
  const { userId, session } = useIdentity()

  return (
    <>
      <header className="app-header">
        <div className="shell app-header-inner">
          <div className="app-header-main">
            <p className="app-title">Fintech Ops Console</p>
            <nav aria-label="Primary">
              <ul>
                {NAV_ITEMS.map((item) => (
                  <li key={item.page}>
                    <a href={item.hash} aria-current={route.page === item.page ? 'page' : undefined}>
                      {item.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
          <UserSwitcher />
        </div>
      </header>
      <div role="note" className="shell demo-banner">
        <details>
          <summary>
            Demo environment · Synthetic identities and data · No real transactions
            <span className="demo-banner-more" aria-hidden="true">
              About this prototype
            </span>
          </summary>
          <p>
            Prototype only. All identities and business data are synthetic.{' '}
            {session.data?.identity_note ??
              'The browser sends only a demo user id; the server resolves role and permissions.'}
          </p>
        </details>
      </div>
      <main key={userId} className="shell app-main">
        {route.page === 'refunds' && <RefundsPage selectedId={route.refundId} />}
        {route.page === 'feature-flags' && <FeatureFlagsPage selectedId={route.flagId} />}
        {route.page === 'audit' && <PlaceholderPage title="Audit Trail" />}
      </main>
    </>
  )
}

export default App
