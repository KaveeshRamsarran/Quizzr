import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authApi, errorMessage } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { Brand, Button, Field } from '../components/ui'
import AuthShell from './AuthShell'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)
  const next = (location.state as { from?: string } | null)?.from || '/dashboard'

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await authApi.login(email.trim(), password)
      login(data.user, data.access_token, data.refresh_token)
      navigate(next, { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Couldn’t sign in.'))
      document.getElementById('password')?.focus()
    } finally {
      setLoading(false)
    }
  }

  const guest = async () => {
    setGuestLoading(true)
    try {
      const data = await authApi.loginAsGuest()
      login(data.user, data.access_token, data.refresh_token)
      navigate('/upload', { replace: true })
    } catch (err) {
      toast.error(errorMessage(err))
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
        {error && <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{error}</div>}
        <Field label="Email" htmlFor="email">
          <input id="email" name="email" type="email" autoComplete="email" inputMode="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password" htmlFor="password">
          <input id="password" name="password" type="password" autoComplete="current-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!error} required />
        </Field>
        <Button type="submit" variant="primary" size="lg" block loading={loading} disabled={!email || !password}>Sign in</Button>
        <div className="flex items-center gap-3 muted small" aria-hidden="true">
          <span className="flex-1" style={{ borderTop: '1px solid var(--color-rule)' }} />or<span className="flex-1" style={{ borderTop: '1px solid var(--color-rule)' }} />
        </div>
        <Button size="lg" block onClick={guest} loading={guestLoading}>Continue as a guest</Button>
      </form>
    </AuthShell>
  )
}
