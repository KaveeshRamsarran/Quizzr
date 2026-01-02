import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  DocumentIcon,
  RectangleStackIcon,
  ClipboardDocumentListIcon,
  ArrowUpIcon,
  FireIcon,
  AcademicCapIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import { documentsApi, decksApi, quizzesApi, analyticsApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import clsx from 'clsx'

export default function Dashboard() {
  const { user } = useAuthStore()

  const { data: overview } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: analyticsApi.getOverview,
    retry: false,
    staleTime: 30000,
  })

  const { data: documents } = useQuery({
    queryKey: ['documents', { limit: 5 }],
    queryFn: () => documentsApi.list({ limit: 5 }),
    retry: false,
    staleTime: 30000,
  })

  const { data: decks } = useQuery({
    queryKey: ['decks', { limit: 5 }],
    queryFn: () => decksApi.list({ limit: 5 }),
    retry: false,
    staleTime: 30000,
  })

  const { data: quizzes } = useQuery({
    queryKey: ['quizzes', { limit: 5 }],
    queryFn: () => quizzesApi.list({ limit: 5 }),
    retry: false,
    staleTime: 30000,
  })

  const { data: cardsDue } = useQuery({
    queryKey: ['analytics', 'cards-due'],
    queryFn: analyticsApi.getCardsDue,
    retry: false,
    staleTime: 30000,
  })

  const stats = [
    {
      name: 'Documents',
      value: overview?.total_documents || 0,
      icon: DocumentIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Decks',
      value: overview?.total_decks || 0,
      icon: RectangleStackIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'Quizzes',
      value: overview?.total_quizzes || 0,
      icon: ClipboardDocumentListIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Cards Due',
      value: cardsDue?.due_now || 0,
      icon: AcademicCapIcon,
      color: 'bg-orange-500',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Welcome section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, {user?.name || user?.email?.split('@')[0] || 'Student'}!
          </h1>
          <p className="mt-1 text-gray-400">
            {overview?.study_streak ? (
              <span className="inline-flex items-center">
                <FireIcon className="w-5 h-5 text-orange-500 mr-1" />
                {overview.study_streak} day streak! Keep it going!
              </span>
            ) : (
              'Ready to study? Upload a document or review your cards.'
            )}
          </p>
        </div>
        <Link to="/upload" className="btn-primary mt-4 sm:mt-0">
          <PlusIcon className="w-5 h-5 mr-2" />
          Upload Document
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card bg-gray-800 border-gray-700 p-6">
            <div className="flex items-center">
              <div className={clsx('p-3 rounded-lg', stat.color)}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">{stat.name}</p>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      {cardsDue && cardsDue.due_now > 0 && (
        <div className="card p-6 bg-gradient-to-r from-primary-500 to-primary-600 text-white border-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Cards Ready for Review</h2>
              <p className="text-primary-100">
                You have {cardsDue.due_now} cards due now and {cardsDue.upcoming_24h} coming up today.
              </p>
            </div>
            <Link
              to={decks?.decks[0] ? `/decks/${decks.decks[0].id}/study` : '#'}
              className="btn bg-white text-primary-600 hover:bg-primary-50"
            >
              Start Studying
              <ArrowUpIcon className="w-5 h-5 ml-2 rotate-45" />
            </Link>
          </div>
        </div>
      )}

      {/* Recent content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent Documents */}
        <div className="card bg-gray-800 border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white">Recent Documents</h3>
              <Link to="/documents" className="text-sm text-primary-400 hover:text-primary-300">
                View all
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-700">
            {documents?.documents.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <DocumentIcon className="w-12 h-12 mx-auto text-gray-600 mb-3" />
                <p>No documents yet</p>
                <Link to="/upload" className="text-primary-400 text-sm">
                  Upload your first PDF
                </Link>
              </div>
            ) : (
              documents?.documents.map((doc) => (
                <Link
                  key={doc.id}
                  to={`/documents/${doc.id}`}
                  className="flex items-center p-4 hover:bg-gray-700 transition-colors"
                >
                  <DocumentIcon className="w-10 h-10 text-gray-500" />
                  <div className="ml-3 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {doc.title || doc.filename}
                    </p>
                    <p className="text-xs text-gray-400">
                      {doc.page_count} pages • {doc.status}
                    </p>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Recent Decks */}
        <div className="card bg-gray-800 border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white">Recent Decks</h3>
              <Link to="/dashboard" className="text-sm text-primary-400 hover:text-primary-300">
                View all
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-700">
            {decks?.decks.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <RectangleStackIcon className="w-12 h-12 mx-auto text-gray-600 mb-3" />
                <p>No decks yet</p>
                <p className="text-sm">Generate from a document</p>
              </div>
            ) : (
              decks?.decks.map((deck) => (
                <Link
                  key={deck.id}
                  to={`/decks/${deck.id}`}
                  className="flex items-center p-4 hover:bg-gray-700 transition-colors"
                >
                  <RectangleStackIcon className="w-10 h-10 text-purple-400" />
                  <div className="ml-3 min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">
                      {deck.title}
                    </p>
                    <p className="text-xs text-gray-400">
                      {deck.card_count} cards • {deck.mastered_count} mastered
                    </p>
                  </div>
                  <div className="ml-2">
                    <div className="w-12 h-2 bg-gray-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{
                          width: `${deck.card_count > 0 ? (deck.mastered_count / deck.card_count) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Recent Quizzes */}
        <div className="card bg-gray-800 border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white">Recent Quizzes</h3>
              <Link to="/dashboard" className="text-sm text-primary-400 hover:text-primary-300">
                View all
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-700">
            {quizzes?.quizzes.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <ClipboardDocumentListIcon className="w-12 h-12 mx-auto text-gray-600 mb-3" />
                <p>No quizzes yet</p>
                <p className="text-sm">Generate from a document</p>
              </div>
            ) : (
              quizzes?.quizzes.map((quiz) => (
                <Link
                  key={quiz.id}
                  to={`/quizzes/${quiz.id}`}
                  className="flex items-center p-4 hover:bg-gray-700 transition-colors"
                >
                  <ClipboardDocumentListIcon className="w-10 h-10 text-green-400" />
                  <div className="ml-3 min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">
                      {quiz.title}
                    </p>
                    <p className="text-xs text-gray-400">
                      {quiz.question_count} questions • {quiz.attempts_count} attempts
                    </p>
                  </div>
                  {quiz.best_score !== null && (
                    <span className={clsx(
                      'text-sm font-medium px-2 py-1 rounded',
                      quiz.best_score >= 80 ? 'bg-green-900 text-green-300' :
                      quiz.best_score >= 60 ? 'bg-yellow-900 text-yellow-300' :
                      'bg-red-900 text-red-300'
                    )}>
                      {quiz.best_score}%
                    </span>
                  )}
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
