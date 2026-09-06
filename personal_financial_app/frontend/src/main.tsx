/**
 * Entry point: mounts React into #root, loads global styles and applies the
 * theme provider (light by default, persisted under "vite-ui-theme").
 *
 * i18n is imported for its side effect — it must initialise before the first
 * component renders, since every screen reads from it.
 *
 * Light is the design's primary direction — warm paper, hairline rules — and
 * dark is the same system under lamplight. The default follows the design
 * rather than the platform, so a first visit looks like the thing that was
 * designed; the toggle in the header switches and the choice sticks.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'
import { ThemeProvider } from './components/provider/theme-provider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <App />
    </ThemeProvider>
  </StrictMode>,
)