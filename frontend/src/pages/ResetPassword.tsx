import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, loadProfile, setPassword, usesSupabase } from '../lib/auth'
import { linkError, supabase } from '../lib/supabase'
import { Brand, Button, Field, PageLoading } from '../components/ui'
import AuthShell from './AuthShell'

/** Where the password reset email lands: the link signs the user in, then they pick a new password. */
export default function ResetPassword() {
  const navigate = useNavigate()
  const [ready, setReady] = useState<boolean | null>(null)
  const [password, setPasswordValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    supabase?.auth.getSession().then(({ data }) => setReady(!!data.session))
  }, [])

  if (!usesSupabase()) return <Navigate to="/login" replace />
  if (ready === null) return <PageLoading />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Use at least 8 characters.'); return }
    setSaving(true)
    try {
      await setPassword(password)
      await loadProfile()
      toast.success('Password changed')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(authErrorMessage(err))
      setSaving(false)
    }
  }

  const failure = linkError()

  return (
    <AuthShell>
      {ready ? (
        <form className="auth__form" onSubmit={submit} noValidate>
          <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
          <div>
            <h1>Choose a new password</h1>
            <p className="muted" style={{ marginTop: 8 }}>You’ll stay signed in on this device.</p>
          </div>
          <Field label="New password" htmlFor="new-password" error={error} help="At least 8 characters.">
            <input id="new-password" type="password" autoComplete="new-password" className="input" value={password} onChange={(e) => setPasswordValue(e.target.value)} aria-invalid={!!error} autoFocus required />
          </Field>
          <Button type="submit" variant="primary" size="lg" block loading={saving} disabled={!password}>Save password</Button>
        </form>
      ) : (
        <div className="auth__form">
          <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
          <h1>That link didn’t work</h1>
          <div className="notice notice--error" role="alert">
            <ExclamationCircleIcon aria-hidden="true" />
            {failure?.code === 'otp_expired' || !failure ? 'Reset links expire after an hour and work only once.' : failure.message}
          </div>
          <Link to="/forgot-password" className="btn btn--primary btn--lg btn--block">Send a new link</Link>
        </div>
      )}
    </AuthShell>
  )
}
