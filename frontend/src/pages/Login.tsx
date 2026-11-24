import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { isAuthError } from '@supabase/supabase-js'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, oauthProviders, resendConfirmation, signIn, signInAsGuest, usesSupabase } from '../lib/auth'
import { Brand, Button, Field } from '../components/ui'
import AuthShell, { OrDivider, ProviderButtons } from './AuthShell'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [unconfirmed, setUnconfirmed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)
  const next = (location.state as { from?: string } | null)?.from || '/dashboard'

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setUnconfirmed(false)
    setLoading(true)
    try {
      await signIn(email.trim(), password)
      navigate(next, { replace: true })
    } catch (err) {
      setUnconfirmed(isAuthError(err) && err.code === 'email_not_confirmed')
      setError(authErrorMessage(err, 'Couldn’t sign in.'))
      document.getElementById('password')?.focus()
    } finally {
      setLoading(false)
    }
  }

  const resend = async () => {
    setResending(true)
    try {
      await resendConfirmation(email.trim())
      toast.success('Confirmation email sent')
    } catch (err) {
      toast.error(authErrorMessage(err))
    } finally {
      setResending(false)
    }
  }

  const guest = async () => {
    setGuestLoading(true)
    try {
      await signInAsGuest()
      navigate('/upload', { replace: true })
    } catch (err) {
      toast.error(authErrorMessage(err))
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <AuthShell>
      <form className="auth__form" onSubmit={submit} noValidate>
        <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
        <div>
          <h1>Welcome back</h1>
          <p className="muted" style={{ marginTop: 8 }}>
            New to Quizzr? <Link to="/register" className="link">Create an account</Link>
          </p>
        </div>
        {error && (
          <div className="notice notice--error" role="alert">
            <ExclamationCircleIcon aria-hidden="true" />
            <span>
              {error}
              {unconfirmed && (
                <> <button type="button" className="link" onClick={resend} disabled={resending}>{resending ? 'Sending…' : 'Send the link again'}</button></>
              )}
            </span>
          </div>
        )}
        <ProviderButtons onError={setError} />
        {oauthProviders().length > 0 && <OrDivider />}
        <Field label="Email" htmlFor="email">
          <input id="email" name="email" type="email" autoComplete="email" inputMode="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field
          label="Password"
          htmlFor="password"
          help={usesSupabase() ? <Link to="/forgot-password" state={{ email }} className="link">Forgot your password?</Link> : undefined}
        >
          <input id="password" name="password" type="password" autoComplete="current-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!error} required />
        </Field>
        <Button type="submit" variant="primary" size="lg" block loading={loading} disabled={!email || !password}>Sign in</Button>
        <OrDivider />
        <Button size="lg" block onClick={guest} loading={guestLoading}>Continue as a guest</Button>
      </form>
    </AuthShell>
  )
}
