import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authApi, errorMessage } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { Brand, Button, Field } from '../components/ui'
import AuthShell from './AuthShell'

export default function Register() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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
      const data = await authApi.register(email.trim(), password, name.trim())
      login(data.user, data.access_token, data.refresh_token)
      navigate('/upload', { replace: true })
    } catch (err) {
      setFormError(errorMessage(err, 'Couldn’t create the account.'))
    } finally {
      setLoading(false)
    }
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
