/**
 * Sign-in flows. Each function works with Supabase Auth when the server has it
 * configured, and with Quizzr's built-in accounts otherwise.
 */
import { isAuthError, type Provider } from '@supabase/supabase-js'
import { authApi, errorMessage } from './api'
import { authConfig, supabase } from './supabase'
import { useAuthStore } from '../stores/authStore'
import type { User } from '../types'

export const usesSupabase = () => supabase !== null

/** OAuth providers turned on for this server (SUPABASE_OAUTH_PROVIDERS). */
export const oauthProviders = () => (supabase ? authConfig().oauth_providers ?? [] : [])

const redirectTo = (path: string) => `${window.location.origin}${path}`

function client() {
  if (!supabase) throw new Error('Supabase is not configured')
  return supabase
}

let profileRequest: Promise<User> | null = null

/** Load the Quizzr profile for the current Supabase session into the auth store. */
export function loadProfile(): Promise<User> {
  if (!profileRequest) {
    profileRequest = (async () => {
      const { data } = await client().auth.getSession()
      if (!data.session) throw new Error('Not signed in')
      const user = await authApi.me()
      useAuthStore.getState().login(user, data.session.access_token, '')
      return user
    })().finally(() => { profileRequest = null })
  }
  return profileRequest
}

/** Load the profile after a Supabase sign-in; if Quizzr refuses it, don't stay half signed in. */
async function finishSignIn(): Promise<User> {
  try {
    return await loadProfile()
  } catch (err) {
    await client().auth.signOut({ scope: 'local' }).catch(() => undefined)
    throw err
  }
}

/** Restore the Supabase session and keep the auth store in step with it. Call once at startup. */
export async function initAuth() {
  if (!supabase) return
  const { data } = await supabase.auth.getSession()
  if (!data.session) useAuthStore.getState().logout()
  supabase.auth.onAuthStateChange((event, session) => {
    const store = useAuthStore.getState()
    if (!session) {
      if (store.isAuthenticated) store.logout()
      return
    }
    store.setTokens(session.access_token, '')
    // Supabase warns against awaiting its own calls inside this callback, so defer.
    if ((event === 'SIGNED_IN' || event === 'INITIAL_SESSION') && !store.user) {
      setTimeout(() => { loadProfile().catch(() => undefined) }, 0)
    }
  })
}

/** A readable message for errors from Supabase Auth or the Quizzr API. */
export function authErrorMessage(error: unknown, fallback = 'Something went wrong. Try again.'): string {
  if (isAuthError(error)) {
    switch (error.code) {
      case 'invalid_credentials': return 'That email and password don’t match.'
      case 'email_not_confirmed': return 'Confirm your email address first, using the link we sent you.'
      case 'user_already_exists':
      case 'email_exists': return 'An account with this email already exists. Sign in instead.'
      case 'weak_password': return error.message || 'Choose a stronger password.'
      case 'same_password': return 'Choose a password that’s different from your current one.'
      case 'over_email_send_rate_limit':
      case 'over_request_rate_limit': return 'Too many attempts. Wait a minute, then try again.'
      case 'anonymous_provider_disabled': return 'Guest access is turned off. Create a free account instead.'
      case 'signup_disabled': return 'New sign-ups are turned off.'
      case 'otp_expired': return 'That link has expired. Request a new one.'
      case 'reauthentication_needed': return 'For security, sign out and sign back in, then change your password.'
    }
    return error.message || fallback
  }
  return errorMessage(error, fallback)
}

export async function signIn(email: string, password: string): Promise<User> {
  if (!supabase) {
    const data = await authApi.login(email, password)
    useAuthStore.getState().login(data.user, data.access_token, data.refresh_token)
    return data.user
  }
  const { error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return finishSignIn()
}

/** Create an account. `needsConfirmation` means Supabase emailed a link the user must open first. */
export async function signUp(email: string, password: string, name: string): Promise<{ needsConfirmation: boolean }> {
  if (!supabase) {
    const data = await authApi.register(email, password, name)
    useAuthStore.getState().login(data.user, data.access_token, data.refresh_token)
    return { needsConfirmation: false }
  }
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { name }, emailRedirectTo: redirectTo('/auth/callback') },
  })
  if (error) throw error
  if (!data.session) return { needsConfirmation: true }
  await finishSignIn()
  return { needsConfirmation: false }
}

export async function signInAsGuest(): Promise<User> {
  if (!supabase) {
    const data = await authApi.loginAsGuest()
    useAuthStore.getState().login(data.user, data.access_token, data.refresh_token)
    return data.user
  }
  const { error } = await supabase.auth.signInAnonymously()
  if (error) throw error
  return finishSignIn()
}

/** Leaves the page for the provider's sign-in screen; it returns to /auth/callback. */
export async function signInWithProvider(provider: string) {
  const { error } = await client().auth.signInWithOAuth({
    provider: provider as Provider,
    options: { redirectTo: redirectTo('/auth/callback') },
  })
  if (error) throw error
}

export async function resendConfirmation(email: string) {
  const { error } = await client().auth.resend({
    type: 'signup',
    email,
    options: { emailRedirectTo: redirectTo('/auth/callback') },
  })
  if (error) throw error
}

export async function requestPasswordReset(email: string) {
  const { error } = await client().auth.resetPasswordForEmail(email, { redirectTo: redirectTo('/reset-password') })
  if (error) throw error
}

/** Set a new password for the signed-in user (after a reset link, or from Settings). */
export async function setPassword(password: string) {
  const { error } = await client().auth.updateUser({ password })
  if (error) throw error
}

export async function changePassword(currentPassword: string, newPassword: string) {
  if (!supabase) {
    await authApi.changePassword(currentPassword, newPassword)
    return
  }
  await setPassword(newPassword)
}

/** Start an email change. Supabase confirms it by email before it takes effect. */
export async function changeEmail(email: string) {
  const { error } = await client().auth.updateUser({ email }, { emailRedirectTo: redirectTo('/auth/callback') })
  if (error) throw error
}

/**
 * Turn a guest account into a full one, keeping everything made as a guest.
 * With email confirmation on, Supabase sends a link first (`pending: true`) and the
 * password is set afterwards from Settings.
 */
export async function upgradeGuest(email: string, password: string, name: string): Promise<{ pending: boolean }> {
  if (!supabase) {
    const data = await authApi.convertGuest(email, password, name)
    useAuthStore.getState().login(data.user, data.access_token, data.refresh_token)
    return { pending: false }
  }
  const { data, error } = await supabase.auth.updateUser(
    { email, data: { name } },
    { emailRedirectTo: redirectTo('/auth/callback') },
  )
  if (error) throw error
  if (data.user?.email?.toLowerCase() !== email.toLowerCase()) return { pending: true }
  await setPassword(password)
  // The access token still says "anonymous" until it is refreshed.
  await supabase.auth.refreshSession()
  await loadProfile()
  return { pending: false }
}

export async function signOut() {
  if (supabase) await supabase.auth.signOut().catch(() => undefined)
  else await authApi.logout()
  useAuthStore.getState().logout()
}

export async function deleteAccount() {
  await authApi.deleteAccount()
  if (supabase) await supabase.auth.signOut({ scope: 'local' }).catch(() => undefined)
  useAuthStore.getState().logout()
}
