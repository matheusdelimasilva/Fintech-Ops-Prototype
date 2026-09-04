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
    <section aria-labelledby="page-heading">
      <h1 id="page-heading">{title}</h1>
      <p>Not implemented in this checkpoint.</p>
    </section>
  )
}

function App() {
  const route = useHashRoute()
  const { userId, session } = useIdentity()

  return (
    <>
      <header className="app-header">
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
      </header>
      <p role="note" className="banner">
        Prototype only. All identities and business data are synthetic.{' '}
        {session.data?.identity_note ??
          'The browser sends only a demo user id; the server resolves role and permissions.'}
      </p>
      <main key={userId} className="app-main">
        {route.page === 'refunds' && <RefundsPage selectedId={route.refundId} />}
        {route.page === 'feature-flags' && <PlaceholderPage title="Feature Flags" />}
        {route.page === 'audit' && <PlaceholderPage title="Audit Trail" />}
      </main>
    </>
  )
}

export default App
