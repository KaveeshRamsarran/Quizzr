import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ComputerDesktopIcon, EnvelopeIcon, MoonIcon, SparklesIcon, SunIcon } from '@heroicons/react/24/outline'
import { authApi } from '../lib/api'
import { authErrorMessage, changeEmail, changePassword, deleteAccount as removeAccount, upgradeGuest, usesSupabase } from '../lib/auth'
import { getCardsPerSession, getThemeMode, setCardsPerSession, setThemeMode, type ThemeMode } from '../lib/theme'
import { useAuthStore } from '../stores/authStore'
import { Button, ConfirmDialog, Field, PageHeader, Segmented } from '../components/ui'
import { initials } from '../lib/format'
import { Item, Page, Stagger } from '../components/motion'

function Panel({ id, title, sub, children }: { id?: string; title: string; sub?: string; children: ReactNode }) {
  return (
    <Item className="card card--pad">
      <section id={id} aria-labelledby={`${id ?? title}-h`}>
        <h2 id={`${id ?? title}-h`} style={{ fontSize: 'var(--text-lg)' }}>{title}</h2>
        {sub && <p className="small muted" style={{ marginTop: 4 }}>{sub}</p>}
        <div style={{ marginTop: 18 }}>{children}</div>
      </section>
    </Item>
  )
}

export default function Settings() {
  const { user, updateUser } = useAuthStore()
  const supabaseMode = usesSupabase()
  const [pendingEmail, setPendingEmail] = useState<string | null>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const [name, setName] = useState(user?.name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [school, setSchool] = useState(user?.school ?? '')
  const [savingProfile, setSavingProfile] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [savingPassword, setSavingPassword] = useState(false)
  const [convertName, setConvertName] = useState('')
  const [convertEmail, setConvertEmail] = useState('')
  const [convertPassword, setConvertPassword] = useState('')
  const [converting, setConverting] = useState(false)
  const [theme, setTheme] = useState<ThemeMode>(getThemeMode())
  const [perSession, setPerSession] = useState(String(getCardsPerSession()))
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (location.hash) setTimeout(() => document.querySelector(location.hash)?.scrollIntoView({ behavior: 'smooth' }), 300)
  }, [location.hash])

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault()
    setSavingProfile(true)
    try {
      const newEmail = email.trim()
      const emailChanged = newEmail.toLowerCase() !== user?.email.toLowerCase()
      // With Supabase, the new address only takes effect once it is confirmed by email.
      const confirmByEmail = supabaseMode && emailChanged
      const updated = await authApi.updateMe({
        name: name.trim(),
        school: school.trim() || null,
        ...(confirmByEmail ? {} : { email: newEmail }),
      })
      updateUser(updated)
      if (confirmByEmail) {
        await changeEmail(newEmail)
        setEmail(updated.email)
        toast.success(`Saved. Open the link we sent to ${newEmail} to confirm your new email.`, { duration: 8000 })
      } else {
        toast.success('Profile saved')
      }
    } catch (err) {
      toast.error(authErrorMessage(err))
    } finally {
      setSavingProfile(false)
    }
  }

  const savePassword = async (e: FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    if (newPassword.length < 8) { setPasswordError('Use at least 8 characters.'); return }
    setSavingPassword(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      toast.success('Password changed')
    } catch (err) {
      setPasswordError(authErrorMessage(err))
    } finally {
      setSavingPassword(false)
    }
  }

  const convert = async (e: FormEvent) => {
    e.preventDefault()
    if (convertPassword.length < 8) { toast.error('Use a password of at least 8 characters.'); return }
    setConverting(true)
    try {
      const { pending } = await upgradeGuest(convertEmail.trim(), convertPassword, convertName.trim())
      if (pending) {
        setPendingEmail(convertEmail.trim())
        setConvertPassword('')
      } else {
        const saved = useAuthStore.getState().user
        setName(saved?.name ?? '')
        setEmail(saved?.email ?? '')
        toast.success('Account saved')
      }
    } catch (err) {
      toast.error(authErrorMessage(err))
    } finally {
      setConverting(false)
    }
  }

  const deleteAccount = async () => {
    setDeleting(true)
    try {
      await removeAccount()
      queryClient.clear()
      navigate('/')
      toast.success('Account deleted')
    } catch (err) {
      toast.error(authErrorMessage(err))
      setDeleting(false)
    }
  }

  if (!user) return null

  return (
    <Page className="page page--narrow">
      <PageHeader title="Settings" />

      <Stagger className="grid gap-4">
        <Item className="card card--pad flex items-center gap-4">
          <span className="avatar" style={{ width: 56, height: 56, fontSize: '1.2rem' }}>{user.is_guest ? 'G' : initials(user.name)}</span>
          <div className="min-w-0">
            <div className="row-title" style={{ fontSize: '1.1rem' }}>{user.is_guest ? 'Guest account' : user.name}</div>
            <div className="small muted truncate">{user.is_guest ? 'Your work isn’t saved to an account yet' : user.email}</div>
          </div>
        </Item>

        {user.is_guest ? (
          <Panel id="account" title="Keep your work" sub="Add an email and password to keep your documents, decks and history.">
            {pendingEmail ? (
              <div className="notice notice--accent" role="status">
                <EnvelopeIcon aria-hidden="true" />
                <span>
                  Almost there. Open the link we sent to <strong>{pendingEmail}</strong> to confirm it. Your work stays on this
                  account. Afterwards, set a password here under Password.
                </span>
              </div>
            ) : (
            <form onSubmit={convert} className="grid gap-4">
              <Field label="Name" htmlFor="cv-name"><input id="cv-name" className="input" autoComplete="name" value={convertName} onChange={(e) => setConvertName(e.target.value)} required /></Field>
              <Field label="Email" htmlFor="cv-email"><input id="cv-email" type="email" inputMode="email" autoComplete="email" className="input" value={convertEmail} onChange={(e) => setConvertEmail(e.target.value)} required /></Field>
              <Field label="Password" htmlFor="cv-password" help="At least 8 characters."><input id="cv-password" type="password" autoComplete="new-password" className="input" value={convertPassword} onChange={(e) => setConvertPassword(e.target.value)} required /></Field>
              <div><Button type="submit" variant="primary" loading={converting} disabled={!convertName.trim() || !convertEmail.trim() || !convertPassword}>Save my account</Button></div>
            </form>
            )}
          </Panel>
        ) : (
          <Panel title="Profile">
            <form onSubmit={saveProfile} className="grid gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Name" htmlFor="name"><input id="name" className="input" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required /></Field>
                <Field label="Email" htmlFor="email"><input id="email" type="email" inputMode="email" autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
              </div>
              <Field label="School or course (optional)" htmlFor="school"><input id="school" className="input" autoComplete="organization" value={school} onChange={(e) => setSchool(e.target.value)} /></Field>
              <div><Button type="submit" variant="primary" loading={savingProfile} disabled={!name.trim() || !email.trim()}>Save changes</Button></div>
            </form>
          </Panel>
        )}

        <Panel title="Appearance">
          <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Colour mode">
            {([
              ['system', 'Automatic', ComputerDesktopIcon],
              ['light', 'Light', SunIcon],
              ['dark', 'Dark', MoonIcon],
            ] as const).map(([value, label, Icon]) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={theme === value}
                className="check"
                style={{ flexDirection: 'column', justifyContent: 'center', minHeight: 84, gap: 6, border: 0 }}
                onClick={() => { setTheme(value); setThemeMode(value) }}
              >
                <Icon style={{ width: 24, height: 24, color: theme === value ? 'var(--color-accent-text)' : 'var(--color-muted)' }} aria-hidden="true" />
                <span className="small" style={{ fontWeight: 500 }}>{label}</span>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Studying">
          <div className="grid gap-5">
            <div className="field">
              <span className="label">Cards per session</span>
              <Segmented<string>
                label="Cards per session"
                value={perSession}
                onChange={(v) => { setPerSession(v); setCardsPerSession(Number(v)) }}
                options={['10', '20', '30', '50'].map((n) => ({ value: n, label: n }))}
              />
              <p className="help">Cards that are due come first, then ones you haven’t studied.</p>
            </div>
            <div className="notice notice--accent">
              <SparklesIcon aria-hidden="true" />
              <span>
Cards and quizzes are written on this computer from your own notes. It works offline, with nothing to set up.
              </span>
            </div>
          </div>
        </Panel>

        {!user.is_guest && (
          <Panel title="Password">
            <form onSubmit={savePassword} className="grid gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                {/* Supabase already checked who this is at sign-in; built-in accounts confirm the old password. */}
                {!supabaseMode && (
                  <Field label="Current password" htmlFor="current-password">
                    <input id="current-password" type="password" autoComplete="current-password" className="input" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
                  </Field>
                )}
                <Field label="New password" htmlFor="new-password" error={passwordError} help="At least 8 characters.">
                  <input id="new-password" type="password" autoComplete="new-password" className="input" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} aria-invalid={!!passwordError} required />
                </Field>
              </div>
              <div><Button type="submit" loading={savingPassword} disabled={(!supabaseMode && !currentPassword) || !newPassword}>{supabaseMode ? 'Set password' : 'Change password'}</Button></div>
            </form>
          </Panel>
        )}

        <Panel title="Delete account" sub="Removes your documents, decks, quizzes and study history. This can’t be undone.">
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>Delete my account</Button>
        </Panel>
      </Stagger>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete your account?"
        body="Everything you’ve uploaded and studied will be permanently deleted."
        confirmLabel="Delete everything"
        loading={deleting}
        onConfirm={deleteAccount}
        onClose={() => setConfirmDelete(false)}
      />
    </Page>
  )
}
