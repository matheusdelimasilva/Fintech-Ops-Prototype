import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import App from './App.tsx'
import { IdentityProvider } from './identity/IdentityProvider.tsx'
import { NoticesProvider } from './shared/NoticesProvider.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IdentityProvider>
      <NoticesProvider>
        <App />
      </NoticesProvider>
    </IdentityProvider>
  </StrictMode>,
)
