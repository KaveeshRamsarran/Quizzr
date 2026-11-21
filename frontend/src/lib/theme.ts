export type ThemeMode = 'light' | 'dark' | 'system'

const KEY = 'quizzr-theme'

export function getThemeMode(): ThemeMode {
  try {
    const value = localStorage.getItem(KEY)
    if (value === 'light' || value === 'dark' || value === 'system') return value
  } catch {
    /* storage unavailable */
  }
  return 'system'
}

export function applyThemeMode(mode: ThemeMode) {
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.toggle('dark', mode === 'dark' || (mode === 'system' && prefersDark))
}

export function setThemeMode(mode: ThemeMode) {
  try {
    localStorage.setItem(KEY, mode)
  } catch {
    /* storage unavailable */
  }
  applyThemeMode(mode)
}

export function watchSystemTheme() {
  const media = window.matchMedia?.('(prefers-color-scheme: dark)')
  const onChange = () => {
    if (getThemeMode() === 'system') applyThemeMode('system')
  }
  media?.addEventListener?.('change', onChange)
  return () => media?.removeEventListener?.('change', onChange)
}

const SESSION_KEY = 'quizzr-cards-per-session'

export function getCardsPerSession(): number {
  try {
    const n = Number(localStorage.getItem(SESSION_KEY))
    if (Number.isFinite(n) && n >= 5 && n <= 200) return n
  } catch {
    /* storage unavailable */
  }
  return 20
}

export function setCardsPerSession(n: number) {
  try {
    localStorage.setItem(SESSION_KEY, String(n))
  } catch {
    /* storage unavailable */
  }
}
