import { createClient, type SupabaseClient } from '@supabase/supabase-js'

/** How this server signs people in, from GET /api/v1/auth/config. */
export interface AuthConfig {
  provider: 'builtin' | 'supabase'
  supabase_url?: string
  supabase_anon_key?: string
  oauth_providers?: string[]
}

let config: AuthConfig = { provider: 'builtin' }

/** The address the app was opened at, before supabase-js strips tokens or errors from it. */
const landingUrl = new URL(window.location.href)

/** The error Supabase put in a confirmation, recovery or OAuth link, if any (e.g. an expired link). */
export function linkError(): { code: string; message: string } | null {
  const params = new URLSearchParams(landingUrl.hash.replace(/^#/, ''))
  const code = params.get('error_code') ?? landingUrl.searchParams.get('error_code') ?? params.get('error') ?? landingUrl.searchParams.get('error')
  if (!code) return null
  const message = params.get('error_description') ?? landingUrl.searchParams.get('error_description') ?? 'That link didn’t work.'
  return { code, message }
}

/** The Supabase client, or null when the server uses Quizzr's built-in accounts. */
export let supabase: SupabaseClient | null = null

/** Fetch the auth config once at startup, before the app renders. */
export async function loadAuthConfig(): Promise<AuthConfig> {
  try {
    const response = await fetch('/api/v1/auth/config')
    if (response.ok) config = (await response.json()) as AuthConfig
  } catch {
    // Server unreachable: fall back to built-in accounts; API calls will report the error.
  }
  if (config.provider === 'supabase' && config.supabase_url && config.supabase_anon_key) {
    supabase = createClient(config.supabase_url, config.supabase_anon_key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'quizzr-supabase-auth' },
    })
  }
  return config
}

export const authConfig = () => config
