import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { EnvelopeIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, oauthProviders, resendConfirmation, signUp } from '../lib/auth'
import { Brand, Button, Field } from '../components/ui'
import AuthShell, { OrDivider, ProviderButtons } from './AuthShell'

export default function Register() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [resending, setResending] = useState(false)

  const validate = () => {
    const next: Record<string, string> = {}
    if (!name.trim()) next.name = 'Enter your name.'
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Enter a valid email address.'
    if (password.length < 8) next.password = 'Use at least 8 characters.'
    setErrors(next)
    const first = Object.keys(next)[0]
    if (first) document.getElementById(first)?.focus()
    return !first
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!validate()) return
    setLoading(true)
    try {
      const { needsConfirmation } = await signUp(email.trim(), password, name.trim())
      if (needsConfirmation) setSentTo(email.trim())
      else navigate('/upload', { replace: true })
    } catch (err) {
      setFormError(authErrorMessage(err, 'Couldn’t create the account.'))
    } finally {
      setLoading(false)
    }
  }

  const resend = async () => {
    if (!sentTo) return
    setResending(true)
    try {
      await resendConfirmation(sentTo)
      toast.success('Sent again')
    } catch (err) {
      toast.error(authErrorMessage(err))
    } finally {
      setResending(false)
    }
  }

  if (sentTo) {
    return (
      <AuthShell>
        <div className="auth__form" role="status">
          <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
          <EnvelopeIcon aria-hidden="true" style={{ width: 40, height: 40, color: 'var(--color-accent-text)' }} />
          <div>
            <h1>Check your inbox</h1>
            <p className="muted" style={{ marginTop: 8 }}>
              We sent a confirmation link to <strong style={{ color: 'var(--color-ink)' }}>{sentTo}</strong>. Open it to finish
              creating your account. It can take a minute to arrive, so check your spam folder too.
            </p>
          </div>
          <Button size="lg" block onClick={resend} loading={resending}>Send it again</Button>
          <p className="muted small">
            Wrong address? <button type="button" className="link" onClick={() => setSentTo(null)}>Go back</button>
            {' · '}
            <Link to="/login" className="link">Sign in</Link>
          </p>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <form className="auth__form" onSubmit={submit} noValidate>
        <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
        <div>
          <h1>Create your account</h1>
          <p className="muted" style={{ marginTop: 8 }}>
            Already have one? <Link to="/login" className="link">Sign in</Link>
          </p>
        </div>
        {formError && <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{formError}</div>}
        <ProviderButtons onError={setFormError} />
        {oauthProviders().length > 0 && <OrDivider />}
        <Field label="Name" htmlFor="name" error={errors.name}>
          <input id="name" name="name" autoComplete="name" className="input" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={!!errors.name} aria-describedby={errors.name ? 'name-error' : undefined} />
        </Field>
        <Field label="Email" htmlFor="email" error={errors.email}>
          <input id="email" name="email" type="email" autoComplete="email" inputMode="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!errors.email} aria-describedby={errors.email ? 'email-error' : undefined} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password} help="At least 8 characters.">
          <input id="password" name="password" type="password" autoComplete="new-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} aria-describedby={errors.password ? 'password-error' : undefined} />
        </Field>
        <Button type="submit" variant="primary" size="lg" block loading={loading}>Create account</Button>
      </form>
    </AuthShell>
  )
}
