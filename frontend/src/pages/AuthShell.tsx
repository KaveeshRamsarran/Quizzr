import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brand, Button } from '../components/ui'
import { authErrorMessage, oauthProviders, signInWithProvider } from '../lib/auth'
import { EASE_OUT } from '../components/motion'

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth__side">
        <Link to="/" aria-label="Quizzr home"><Brand /></Link>
        <motion.div
          initial={{ opacity: 0, y: 24, rotate: -3 }}
          animate={{ opacity: 1, y: 0, rotate: -3 }}
          transition={{ duration: 0.7, ease: EASE_OUT, delay: 0.1 }}
          style={{ maxWidth: 420 }}
        >
          <div className="card" style={{ borderRadius: 24, padding: 28, boxShadow: 'var(--shadow-pop)', color: 'var(--color-ink)' }}>
            <span className="badge badge--accent">Definition</span>
            <p style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.6rem', lineHeight: 1.25, letterSpacing: '-0.02em', margin: '28px 0 12px' }}>
              What is the mitochondrion?
            </p>
            <p className="muted">The organelle that produces most of the cell’s ATP through cellular respiration.</p>
          </div>
        </motion.div>
        <p style={{ opacity: 0.85, maxWidth: '34ch' }}>Every card comes from a sentence in your own notes.</p>
      </aside>
      <main className="auth__main">
        <motion.div
          className="w-full grid place-items-center"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: EASE_OUT }}
        >
          {children}
        </motion.div>
      </main>
    </div>
  )
}

export function OrDivider() {
  return (
    <div className="flex items-center gap-3 muted small" aria-hidden="true">
      <span className="flex-1" style={{ borderTop: '1px solid var(--color-rule)' }} />or<span className="flex-1" style={{ borderTop: '1px solid var(--color-rule)' }} />
    </div>
  )
}

const PROVIDER_NAMES: Record<string, string> = {
  google: 'Google', github: 'GitHub', apple: 'Apple', azure: 'Microsoft', discord: 'Discord', gitlab: 'GitLab',
}

/** "Continue with Google" etc., for the providers enabled in Supabase (SUPABASE_OAUTH_PROVIDERS). */
export function ProviderButtons({ onError }: { onError: (message: string) => void }) {
  const providers = oauthProviders()
  const [pending, setPending] = useState<string | null>(null)
  if (!providers.length) return null
  return (
    <div className="grid gap-3">
      {providers.map((provider) => (
        <Button
          key={provider}
          size="lg"
          block
          loading={pending === provider}
          onClick={async () => {
            setPending(provider)
            try {
              await signInWithProvider(provider)
            } catch (err) {
              onError(authErrorMessage(err))
              setPending(null)
            }
          }}
        >
          Continue with {PROVIDER_NAMES[provider] ?? provider.charAt(0).toUpperCase() + provider.slice(1)}
        </Button>
      ))}
    </div>
  )
}
