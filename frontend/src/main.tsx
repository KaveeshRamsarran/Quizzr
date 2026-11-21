import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import axios from 'axios'
import { MotionConfig } from 'framer-motion'
import App from './App'
import { applyThemeMode, getThemeMode, watchSystemTheme } from './lib/theme'
import './index.css'

applyThemeMode(getThemeMode())
watchSystemTheme()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => {
        const status = axios.isAxiosError(error) ? error.response?.status : undefined
        if (status && status >= 400 && status < 500) return false
        return count < 1
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <App />
        <Toaster
          position="bottom-center"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'var(--color-ink)',
              color: 'var(--color-paper)',
              borderRadius: '14px',
              padding: '10px 14px',
              fontFamily: 'var(--font-body)',
              fontSize: '0.95rem',
              boxShadow: 'none',
            },
            success: { iconTheme: { primary: 'var(--color-success)', secondary: 'var(--color-paper)' } },
            error: { iconTheme: { primary: 'var(--color-error)', secondary: 'var(--color-paper)' } },
          }}
        />
      </BrowserRouter>
      </MotionConfig>
    </QueryClientProvider>
  </React.StrictMode>,
)
