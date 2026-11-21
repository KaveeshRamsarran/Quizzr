import { Suspense, lazy, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import { PageLoading } from './components/ui'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Upload = lazy(() => import('./pages/Upload'))
const Documents = lazy(() => import('./pages/Documents'))
const DocumentView = lazy(() => import('./pages/DocumentView'))
const Decks = lazy(() => import('./pages/Decks'))
const DeckView = lazy(() => import('./pages/DeckView'))
const StudyMode = lazy(() => import('./pages/StudyMode'))
const Quizzes = lazy(() => import('./pages/Quizzes'))
const QuizView = lazy(() => import('./pages/QuizView'))
const QuizTake = lazy(() => import('./pages/QuizTake'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Settings = lazy(() => import('./pages/Settings'))

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace state={{ from: location.pathname }} />
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" replace />
}

const TITLES: [RegExp, string][] = [
  [/^\/dashboard/, 'Today'],
  [/^\/upload/, 'Upload'],
  [/^\/documents/, 'Documents'],
  [/^\/decks\/\d+\/study/, 'Study'],
  [/^\/decks/, 'Decks'],
  [/^\/quizzes\/\d+\/take/, 'Quiz'],
  [/^\/quizzes/, 'Quizzes'],
  [/^\/analytics/, 'Progress'],
  [/^\/settings/, 'Settings'],
  [/^\/login/, 'Sign in'],
  [/^\/register/, 'Create an account'],
]

function useDocumentTitle() {
  const { pathname } = useLocation()
  useEffect(() => {
    const match = TITLES.find(([pattern]) => pattern.test(pathname))
    document.title = match ? `${match[1]} | Quizzr` : 'Quizzr: study from your own notes'
    window.scrollTo(0, 0)
  }, [pathname])
}

export default function App() {
  useDocumentTitle()
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/documents/:id" element={<DocumentView />} />
          <Route path="/decks" element={<Decks />} />
          <Route path="/decks/:id" element={<DeckView />} />
          <Route path="/quizzes" element={<Quizzes />} />
          <Route path="/quizzes/:id" element={<QuizView />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Focus screens without the top bar */}
        <Route path="/decks/:id/study" element={<PrivateRoute><StudyMode /></PrivateRoute>} />
        <Route path="/quizzes/:id/take" element={<PrivateRoute><QuizTake /></PrivateRoute>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
