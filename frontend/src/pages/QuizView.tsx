import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  PlayIcon,
  TrashIcon,
  ClockIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline'
import { quizzesApi } from '../lib/api'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function QuizView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const quizId = parseInt(id || '0')

  const { data: quiz, isLoading } = useQuery({
    queryKey: ['quiz', quizId],
    queryFn: () => quizzesApi.get(quizId),
    enabled: !!quizId,
  })

  const { data: attempts } = useQuery({
    queryKey: ['quiz-attempts', quizId],
    queryFn: () => quizzesApi.listAttempts(quizId),
    enabled: !!quizId,
  })

  const deleteMutation = useMutation({
    mutationFn: () => quizzesApi.delete(quizId),
    onSuccess: () => {
      toast.success('Quiz deleted')
      queryClient.invalidateQueries({ queryKey: ['quizzes'] })
      navigate('/dashboard')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!quiz) {
    return (
      <div className="text-center py-12">
        <ClipboardDocumentListIcon className="w-16 h-16 mx-auto text-gray-600 mb-4" />
        <h2 className="text-xl font-semibold text-white">Quiz not found</h2>
        <Link to="/dashboard" className="text-primary-400 mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center text-gray-400 hover:text-white mb-4"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <ClipboardDocumentListIcon className="w-12 h-12 text-green-400" />
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-white">{quiz.title}</h1>
              {quiz.description && (
                <p className="text-gray-400">{quiz.description}</p>
              )}
            </div>
          </div>

          <button
            onClick={() => deleteMutation.mutate()}
            className="btn-danger"
            title="Delete quiz"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-white">{quiz.question_count}</p>
          <p className="text-sm text-gray-400">Questions</p>
        </div>
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-white">{quiz.attempts_count}</p>
          <p className="text-sm text-gray-400">Attempts</p>
        </div>
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-green-400">
            {quiz.best_score !== null ? `${quiz.best_score}%` : '-'}
          </p>
          <p className="text-sm text-gray-400">Best Score</p>
        </div>
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-blue-400">
            {quiz.time_limit_minutes || '∞'}
          </p>
          <p className="text-sm text-gray-400">Minutes</p>
        </div>
      </div>

      {/* Start quiz button */}
      <Link
        to={`/quizzes/${quizId}/take`}
        className="card p-6 mb-6 flex items-center justify-between bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:shadow-lg transition-shadow border-0"
      >
        <div>
          <h2 className="text-xl font-bold">Start Quiz</h2>
          <p className="text-green-100">
            {quiz.question_count} questions • {quiz.pass_percentage}% to pass
          </p>
        </div>
        <PlayIcon className="w-12 h-12" />
      </Link>

      {/* Previous attempts */}
      {attempts && attempts.length > 0 && (
        <div className="card bg-gray-800 border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold text-white">Previous Attempts</h2>
          </div>
          <div className="divide-y divide-gray-700">
            {attempts.map((attempt) => (
              <div key={attempt.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center">
                  <div
                    className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      attempt.percentage && attempt.percentage >= quiz.pass_percentage
                        ? 'bg-green-900/50'
                        : 'bg-red-900/50'
                    )}
                  >
                    <TrophyIcon
                      className={clsx(
                        'w-5 h-5',
                        attempt.percentage && attempt.percentage >= quiz.pass_percentage
                          ? 'text-green-400'
                          : 'text-red-400'
                      )}
                    />
                  </div>
                  <div className="ml-3">
                    <p className="font-medium text-white">
                      {attempt.percentage}% ({attempt.correct_count}/{attempt.total_questions})
                    </p>
                    <p className="text-sm text-gray-400">
                      {new Date(attempt.started_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                {attempt.time_spent_seconds && (
                  <div className="flex items-center text-gray-400">
                    <ClockIcon className="w-4 h-4 mr-1" />
                    {Math.floor(attempt.time_spent_seconds / 60)}m {attempt.time_spent_seconds % 60}s
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Questions preview */}
      <div className="card bg-gray-800 border-gray-700 mt-6">
        <div className="p-4 border-b border-gray-700">
          <h2 className="font-semibold text-white">
            Questions ({quiz.questions?.length || 0})
          </h2>
        </div>
        <div className="divide-y divide-gray-700">
          {quiz.questions?.map((question, index) => (
            <div key={question.id} className="p-4">
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-gray-700 rounded-full flex items-center justify-center text-sm font-medium text-gray-300">
                  {index + 1}
                </span>
                <div>
                  <p className="text-gray-200">{question.question_text}</p>
                  <span
                    className={clsx(
                      'inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded',
                      question.question_type === 'multiple_choice' && 'bg-blue-900 text-blue-300',
                      question.question_type === 'true_false' && 'bg-purple-900 text-purple-300',
                      question.question_type === 'fill_blank' && 'bg-orange-900 text-orange-300',
                      question.question_type === 'short_answer' && 'bg-green-900 text-green-300'
                    )}
                  >
                    {question.question_type.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
