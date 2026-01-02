import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RectangleStackIcon,
  ArrowLeftIcon,
  PlayIcon,
  PencilIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import { decksApi } from '../lib/api'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function DeckView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const deckId = parseInt(id || '0')

  const { data: deck, isLoading } = useQuery({
    queryKey: ['deck', deckId],
    queryFn: () => decksApi.get(deckId),
    enabled: !!deckId,
  })

  const deleteMutation = useMutation({
    mutationFn: () => decksApi.delete(deckId),
    onSuccess: () => {
      toast.success('Deck deleted')
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      navigate('/dashboard')
    },
  })

  const handleExportCsv = async () => {
    const blob = await decksApi.exportCsv(deckId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${deck?.title || 'deck'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!deck) {
    return (
      <div className="text-center py-12">
        <RectangleStackIcon className="w-16 h-16 mx-auto text-gray-600 mb-4" />
        <h2 className="text-xl font-semibold text-white">Deck not found</h2>
        <Link to="/dashboard" className="text-primary-400 mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    )
  }

  const masteryPercentage = deck.card_count > 0
    ? Math.round((deck.mastered_count / deck.card_count) * 100)
    : 0

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
            <RectangleStackIcon className="w-12 h-12 text-purple-400" />
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-white">{deck.title}</h1>
              {deck.description && (
                <p className="text-gray-400">{deck.description}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCsv}
              className="btn-secondary bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600"
              title="Export to CSV"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => deleteMutation.mutate()}
              className="btn-danger"
              title="Delete deck"
            >
              <TrashIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-white">{deck.card_count}</p>
          <p className="text-sm text-gray-400">Total Cards</p>
        </div>
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-green-400">{deck.mastered_count}</p>
          <p className="text-sm text-gray-400">Mastered</p>
        </div>
        <div className="card bg-gray-800 border-gray-700 p-4 text-center">
          <p className="text-3xl font-bold text-purple-400">{masteryPercentage}%</p>
          <p className="text-sm text-gray-400">Progress</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="card bg-gray-800 border-gray-700 p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-300">Mastery Progress</span>
          <span className="text-sm text-gray-400">{masteryPercentage}%</span>
        </div>
        <div className="w-full bg-gray-600 rounded-full h-3">
          <div
            className="bg-gradient-to-r from-purple-500 to-primary-500 h-3 rounded-full transition-all"
            style={{ width: `${masteryPercentage}%` }}
          />
        </div>
      </div>

      {/* Study button */}
      {deck.card_count > 0 && (
        <Link
          to={`/decks/${deckId}/study`}
          className="card p-6 mb-6 flex items-center justify-between bg-gradient-to-r from-purple-500 to-primary-600 text-white hover:shadow-lg transition-shadow border-0"
        >
          <div>
            <h2 className="text-xl font-bold">Start Studying</h2>
            <p className="text-purple-100">
              Review cards using spaced repetition
            </p>
          </div>
          <PlayIcon className="w-12 h-12" />
        </Link>
      )}

      {/* Cards list */}
      <div className="card bg-gray-800 border-gray-700">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="font-semibold text-white">
            Cards ({deck.cards?.length || 0})
          </h2>
          <button className="btn-secondary bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600 text-sm">
            <PlusIcon className="w-4 h-4 mr-1" />
            Add Card
          </button>
        </div>

        {deck.cards?.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <RectangleStackIcon className="w-12 h-12 mx-auto text-gray-600 mb-3" />
            <p>No cards in this deck yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {deck.cards?.map((card, index) => (
              <div key={card.id} className="p-4 hover:bg-gray-700">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-medium px-2 py-0.5 bg-gray-700 text-gray-300 rounded">
                        #{index + 1}
                      </span>
                      <span
                        className={clsx(
                          'text-xs font-medium px-2 py-0.5 rounded',
                          card.card_type === 'basic' && 'bg-blue-900 text-blue-300',
                          card.card_type === 'cloze' && 'bg-purple-900 text-purple-300',
                          card.card_type === 'reverse' && 'bg-green-900 text-green-300'
                        )}
                      >
                        {card.card_type}
                      </span>
                      {card.needs_review && (
                        <span className="text-xs font-medium px-2 py-0.5 bg-yellow-900 text-yellow-300 rounded">
                          Needs Review
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-white">{card.front}</p>
                    <p className="text-gray-400 mt-1">{card.back}</p>
                    {card.source_page && (
                      <p className="text-xs text-gray-500 mt-2">
                        Source: Page {card.source_page}
                      </p>
                    )}
                  </div>
                  <button className="p-2 text-gray-500 hover:text-gray-300">
                    <PencilIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
