import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, requestPasswordReset, usesSupabase } from '../lib/auth'
import { Brand, Button, Field } from '../components/ui'
import AuthShell from './AuthShell'

export default function ForgotPassword() {
  const location = useLocation()
  const [email, setEmail] = useState((location.state as { email?: string } | null)?.email ?? '')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  // Built-in accounts have no way to send email, so there is no reset flow.
  if (!usesSupabase()) return <Navigate to="/login" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) { setError('Enter a valid email address.'); return }
    setLoading(true)
    try {
      await requestPasswordReset(email.trim())
      setSent(true)
    } catch (err) {
      setError(authErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <form className="auth__form" onSubmit={submit} noValidate>
        <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
        <div>
          <h1>Reset your password</h1>
          <p className="muted" style={{ marginTop: 8 }}>
            Enter your account’s email and we’ll send you a link to choose a new password.
          </p>
        </div>
        {error && <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{error}</div>}
        {sent ? (
          <div className="notice notice--success" role="status">
            <CheckCircleIcon aria-hidden="true" />
            <span>If there’s an account for {email.trim()}, a reset link is on its way. Check your spam folder if it doesn’t arrive.</span>
          </div>
        ) : (
          <>
            <Field label="Email" htmlFor="email">
              <input id="email" type="email" autoComplete="email" inputMode="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
            <Button type="submit" variant="primary" size="lg" block loading={loading} disabled={!email.trim()}>Send reset link</Button>
          </>
        )}
        <p className="muted small"><Link to="/login" className="link">Back to sign in</Link></p>
      </form>
    </AuthShell>
  )
}
