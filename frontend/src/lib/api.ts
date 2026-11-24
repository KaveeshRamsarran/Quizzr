import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../stores/authStore'
import { supabase } from './supabase'
import type {
  AnalyticsOverview,
  AnswerResult,
  AttemptResult,
  Card,
  CardReviewResponse,
  Deck,
  DeckDetail,
  DeckGenerationRequest,
  DeckListResponse,
  DocumentDetail,
  Document,
  DocumentListResponse,
  GenerationJob,
  MissedQuestion,
  QuizAttempt,
  QuizDetail,
  QuizGenerationRequest,
  QuizListResponse,
  StudyProgress,
  Suggestion,
  TokenResponse,
  TopicAnalytics,
  User,
} from '../types'

export const api = axios.create({ baseURL: '/api/v1', timeout: 60_000 })

api.interceptors.request.use(async (config) => {
  // With Supabase, ask its client for the token: it refreshes it when it is about to expire.
  const token = supabase
    ? (await supabase.auth.getSession()).data.session?.access_token
    : useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Refresh the access token once on a 401, then retry the original request.
let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (supabase) {
    const { data } = await supabase.auth.refreshSession()
    if (data.session) return data.session.access_token
    await supabase.auth.signOut({ scope: 'local' }).catch(() => undefined)
    useAuthStore.getState().logout()
    return null
  }
  const { refreshToken, login, logout } = useAuthStore.getState()
  if (!refreshToken) return null
  try {
    const { data } = await axios.post<TokenResponse>('/api/v1/auth/refresh', { refresh_token: refreshToken })
    login(data.user, data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    logout()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
    const isAuthCall = original?.url?.startsWith('/auth/login') || original?.url?.startsWith('/auth/register') || original?.url?.startsWith('/auth/refresh')
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      refreshing = refreshing ?? refreshAccessToken().finally(() => { refreshing = null })
      const token = await refreshing
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

/** A readable message from any API error. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Try again.'): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Can’t reach the Quizzr server. Check that it is running.'
    const detail = (error.response.data as { detail?: unknown })?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string; loc?: string[] }
      const field = first.loc?.[first.loc.length - 1]
      return field ? `${field}: ${first.msg}` : first.msg ?? fallback
    }
    if (error.response.status === 413) return 'That file is too large.'
  }
  return fallback
}

function downloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function filenameFrom(header: string | undefined, fallback: string) {
  const match = header?.match(/filename="?([^"]+)"?/)
  return match?.[1] ?? fallback
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, password: string, name: string) =>
    api.post<TokenResponse>('/auth/register', { email, password, name }).then((r) => r.data),
  loginAsGuest: () => api.post<TokenResponse>('/auth/guest').then((r) => r.data),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
  updateMe: (data: Partial<Pick<User, 'name' | 'email' | 'school' | 'timezone' | 'preferred_difficulty' | 'study_goal_days' | 'simple_mode'>>) =>
    api.put<User>('/auth/me', data).then((r) => r.data),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }).then((r) => r.data),
  convertGuest: (email: string, password: string, name: string) =>
    api.post<TokenResponse>('/auth/convert-guest', { email, password, name }).then((r) => r.data),
  logout: () => api.post('/auth/logout').catch(() => undefined),
  deleteAccount: () => api.delete('/auth/me'),
}

export const documentsApi = {
  list: (params: { page?: number; limit?: number; search?: string; status?: string } = {}) =>
    api.get<DocumentListResponse>('/documents', { params }).then((r) => r.data),
  get: (id: number) => api.get<DocumentDetail>(`/documents/${id}`).then((r) => r.data),
  upload: (file: File, onProgress?: (percent: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<Document>('/documents/upload', form, {
        timeout: 0,
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      .then((r) => r.data)
  },
  update: (id: number, data: { title?: string; description?: string }) =>
    api.put<Document>(`/documents/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/documents/${id}`),
  reprocess: (id: number) => api.post<Document>(`/documents/${id}/reprocess`).then((r) => r.data),
  fileBlob: (id: number) => api.get<Blob>(`/documents/${id}/file`, { responseType: 'blob', timeout: 0 }).then((r) => r.data),
}

export const decksApi = {
  list: (params: { page?: number; limit?: number; search?: string; document_id?: number } = {}) =>
    api.get<DeckListResponse>('/decks', { params }).then((r) => r.data),
  get: (id: number) => api.get<DeckDetail>(`/decks/${id}`).then((r) => r.data),
  create: (data: { name: string; description?: string }) => api.post<Deck>('/decks', data).then((r) => r.data),
  update: (id: number, data: { name?: string; description?: string }) => api.put<Deck>(`/decks/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/decks/${id}`),
  addCard: (deckId: number, data: { front: string; back: string; card_type?: string }) =>
    api.post<Card>(`/decks/${deckId}/cards`, data).then((r) => r.data),
  updateCard: (deckId: number, cardId: number, data: Partial<Pick<Card, 'front' | 'back' | 'is_suspended' | 'needs_review'>>) =>
    api.put<Card>(`/decks/${deckId}/cards/${cardId}`, data).then((r) => r.data),
  deleteCard: (deckId: number, cardId: number) => api.delete(`/decks/${deckId}/cards/${cardId}`),
  getStudyCards: (deckId: number, limit = 20, mode: 'due' | 'all' = 'due') =>
    api.get<Card[]>(`/decks/${deckId}/study`, { params: { limit, mode } }).then((r) => r.data),
  reviewCard: (deckId: number, cardId: number, review: { rating: 'again' | 'hard' | 'good' | 'easy'; time_spent_ms: number }) =>
    api.post<CardReviewResponse>(`/decks/${deckId}/cards/${cardId}/review`, review).then((r) => r.data),
  exportCsv: async (deckId: number) => {
    const r = await api.get<Blob>(`/decks/${deckId}/export/csv`, { responseType: 'blob' })
    downloadBlob(r.data, filenameFrom(r.headers['content-disposition'], 'deck.csv'))
  },
  exportAnki: async (deckId: number) => {
    const r = await api.get<Blob>(`/decks/${deckId}/export/anki`, { responseType: 'blob' })
    downloadBlob(r.data, filenameFrom(r.headers['content-disposition'], 'deck.txt'))
  },
}

export const quizzesApi = {
  list: (params: { page?: number; limit?: number; search?: string; document_id?: number } = {}) =>
    api.get<QuizListResponse>('/quizzes', { params }).then((r) => r.data),
  get: (id: number) => api.get<QuizDetail>(`/quizzes/${id}`).then((r) => r.data),
  update: (id: number, data: { name?: string; time_limit_minutes?: number | null; pass_percentage?: number }) =>
    api.put(`/quizzes/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/quizzes/${id}`),
  startAttempt: (quizId: number) => api.post<QuizAttempt>(`/quizzes/${quizId}/attempts`).then((r) => r.data),
  listAttempts: (quizId: number) => api.get<QuizAttempt[]>(`/quizzes/${quizId}/attempts`, { params: { limit: 20 } }).then((r) => r.data),
  submitAnswer: (quizId: number, attemptId: number, questionId: number, answer: string, timeSpentMs: number) =>
    api
      .post<AnswerResult>(`/quizzes/${quizId}/attempts/${attemptId}/answers`, {
        question_id: questionId,
        answer,
        time_spent_ms: timeSpentMs,
      })
      .then((r) => r.data),
  finishAttempt: (quizId: number, attemptId: number) =>
    api.post<AttemptResult>(`/quizzes/${quizId}/attempts/${attemptId}/finish`).then((r) => r.data),
}

export const generationApi = {
  generateDeck: (data: DeckGenerationRequest) => api.post<GenerationJob>('/generation/deck', data).then((r) => r.data),
  generateQuiz: (data: QuizGenerationRequest) => api.post<GenerationJob>('/generation/quiz', data).then((r) => r.data),
  getJobStatus: (jobId: number) => api.get<GenerationJob>(`/generation/job/${jobId}`).then((r) => r.data),
  listJobs: (params: { document_id?: number; limit?: number } = {}) =>
    api.get<GenerationJob[]>('/generation/jobs', { params }).then((r) => r.data),
  cancel: (jobId: number) => api.delete(`/generation/job/${jobId}`),
}

export const analyticsApi = {
  getOverview: () => api.get<AnalyticsOverview>('/analytics/overview').then((r) => r.data),
  getProgress: (days = 30) => api.get<StudyProgress>('/analytics/progress', { params: { days } }).then((r) => r.data),
  getTopics: () => api.get<TopicAnalytics>('/analytics/topics').then((r) => r.data),
  getMissed: (limit = 10) =>
    api.get<{ questions: MissedQuestion[]; total: number }>('/analytics/missed-questions', { params: { limit } }).then((r) => r.data),
  getSuggestions: () => api.get<Suggestion[]>('/analytics/suggestions').then((r) => r.data),
}
