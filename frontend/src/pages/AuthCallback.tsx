import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, loadProfile, usesSupabase } from '../lib/auth'
import { linkError, supabase } from '../lib/supabase'
import { Brand, PageLoading } from '../components/ui'
import AuthShell from './AuthShell'

/** Where email confirmation, email change and Google/GitHub sign-in links return to. */
export default function AuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!supabase) return
    const failure = linkError()
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) {
        setError(
          failure?.code === 'otp_expired'
            ? 'That link has expired or was already used. Sign in, or request a new link.'
            : failure?.message ?? 'We couldn’t sign you in from that link.',
        )
        return
      }
      try {
        await loadProfile()
        navigate('/dashboard', { replace: true })
      } catch (err) {
        await supabase?.auth.signOut({ scope: 'local' }).catch(() => undefined)
        setError(authErrorMessage(err))
      }
    })
  }, [navigate])

  if (!usesSupabase()) return <Navigate to="/login" replace />
  if (!error) return <PageLoading />

  return (
    <AuthShell>
      <div className="auth__form">
        <Link to="/" className="lg:hidden" aria-label="Quizzr home"><Brand /></Link>
        <h1>Couldn’t sign you in</h1>
        <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{error}</div>
        <Link to="/login" className="btn btn--primary btn--lg btn--block">Go to sign in</Link>
      </div>
    </AuthShell>
  )
}
