import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeftIcon,
  CheckIcon,
  LightBulbIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { decksApi } from '../lib/api'
import type { Card, CardReview } from '../types'
import clsx from 'clsx'

type Rating = 'again' | 'hard' | 'good' | 'easy'

export default function StudyMode() {
  const { id } = useParams<{ id: string }>()
  const deckId = parseInt(id || '0')

  const [currentIndex, setCurrentIndex] = useState(0)
  const [isFlipped, setIsFlipped] = useState(false)
  const [studyCards, setStudyCards] = useState<Card[]>([])
  const [startTime, setStartTime] = useState<number>(Date.now())
  const [sessionStats, setSessionStats] = useState({
    reviewed: 0,
    again: 0,
    hard: 0,
    good: 0,
    easy: 0,
  })

  const { data: cards, isLoading } = useQuery({
    queryKey: ['study-cards', deckId],
    queryFn: () => decksApi.getStudyCards(deckId, 20),
    enabled: !!deckId,
  })

  useEffect(() => {
    if (cards) {
      setStudyCards(cards)
      setStartTime(Date.now())
    }
  }, [cards])

  const reviewMutation = useMutation({
    mutationFn: ({ cardId, review }: { cardId: number; review: CardReview }) =>
      decksApi.reviewCard(deckId, cardId, review),
  })

  const currentCard = studyCards[currentIndex]
  const isComplete = currentIndex >= studyCards.length

  const handleRate = async (rating: Rating) => {
    if (!currentCard) return

    const timeSpent = Date.now() - startTime

    // Submit review
    reviewMutation.mutate({
      cardId: currentCard.id,
      review: {
        rating,
        time_spent_ms: timeSpent,
      },
    })

    // Update stats
    setSessionStats((prev) => ({
      ...prev,
      reviewed: prev.reviewed + 1,
      [rating]: prev[rating] + 1,
    }))

    // Move to next card
    setIsFlipped(false)
    setTimeout(() => {
      setCurrentIndex((prev) => prev + 1)
      setStartTime(Date.now())
    }, 200)
  }

  const handleFlip = () => {
    setIsFlipped(!isFlipped)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (studyCards.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <CheckIcon className="w-16 h-16 mx-auto text-green-500 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">All caught up!</h2>
        <p className="text-gray-600 mb-6">
          You've reviewed all due cards. Check back later for more.
        </p>
        <Link to={`/decks/${deckId}`} className="btn-primary">
          Back to Deck
        </Link>
      </div>
    )
  }

  if (isComplete) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6"
        >
          <CheckIcon className="w-10 h-10 text-green-600" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Session Complete!</h2>
        <p className="text-gray-600 mb-6">
          You reviewed {sessionStats.reviewed} cards.
        </p>

        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-red-600">{sessionStats.again}</p>
            <p className="text-sm text-gray-500">Again</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-orange-600">{sessionStats.hard}</p>
            <p className="text-sm text-gray-500">Hard</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{sessionStats.good}</p>
            <p className="text-sm text-gray-500">Good</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{sessionStats.easy}</p>
            <p className="text-sm text-gray-500">Easy</p>
          </div>
        </div>

        <div className="flex gap-4 justify-center">
          <Link to={`/decks/${deckId}`} className="btn-secondary">
            Back to Deck
          </Link>
          <button
            onClick={() => {
              setCurrentIndex(0)
              setIsFlipped(false)
              setSessionStats({ reviewed: 0, again: 0, hard: 0, good: 0, easy: 0 })
            }}
            className="btn-primary"
          >
            <ArrowPathIcon className="w-5 h-5 mr-2" />
            Study Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <Link
          to={`/decks/${deckId}`}
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-2" />
          Exit
        </Link>
        <div className="text-sm text-gray-500">
          {currentIndex + 1} / {studyCards.length}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-8">
        <div
          className="bg-primary-500 h-2 rounded-full transition-all"
          style={{ width: `${((currentIndex + 1) / studyCards.length) * 100}%` }}
        />
      </div>

      {/* Flashcard */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentCard.id}
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -50 }}
          className="perspective-1000"
        >
          <div
            onClick={handleFlip}
            className={clsx(
              'card min-h-[300px] p-8 cursor-pointer transition-transform duration-500 preserve-3d',
              isFlipped && 'rotate-y-180'
            )}
          >
            {/* Front */}
            <div className={clsx('backface-hidden', isFlipped && 'hidden')}>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium px-2 py-1 bg-primary-100 text-primary-700 rounded">
                  Question
                </span>
                <span className="text-xs text-gray-400">
                  Click to reveal answer
                </span>
              </div>
              <p className="text-xl text-gray-900 leading-relaxed">
                {currentCard.front}
              </p>
            </div>

            {/* Back */}
            <div className={clsx('backface-hidden rotate-y-180', !isFlipped && 'hidden')}>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium px-2 py-1 bg-green-100 text-green-700 rounded">
                  Answer
                </span>
              </div>
              <p className="text-xl text-gray-900 leading-relaxed">
                {currentCard.back}
              </p>
              {currentCard.source_snippets?.[0] && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <div className="flex items-center text-sm text-gray-500 mb-2">
                    <LightBulbIcon className="w-4 h-4 mr-1" />
                    Source
                  </div>
                  <p className="text-sm text-gray-600 italic">
                    "{currentCard.source_snippets[0]}"
                  </p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Rating buttons */}
      {isFlipped && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 grid grid-cols-4 gap-3"
        >
          <button
            onClick={() => handleRate('again')}
            className="btn py-4 bg-red-500 text-white hover:bg-red-600 flex-col"
          >
            <span className="text-lg font-bold">Again</span>
            <span className="text-xs opacity-75">&lt;1 min</span>
          </button>
          <button
            onClick={() => handleRate('hard')}
            className="btn py-4 bg-orange-500 text-white hover:bg-orange-600 flex-col"
          >
            <span className="text-lg font-bold">Hard</span>
            <span className="text-xs opacity-75">&lt;10 min</span>
          </button>
          <button
            onClick={() => handleRate('good')}
            className="btn py-4 bg-green-500 text-white hover:bg-green-600 flex-col"
          >
            <span className="text-lg font-bold">Good</span>
            <span className="text-xs opacity-75">1 day</span>
          </button>
          <button
            onClick={() => handleRate('easy')}
            className="btn py-4 bg-blue-500 text-white hover:bg-blue-600 flex-col"
          >
            <span className="text-lg font-bold">Easy</span>
            <span className="text-xs opacity-75">4 days</span>
          </button>
        </motion.div>
      )}

      {/* Keyboard hint */}
      <p className="text-center text-sm text-gray-400 mt-6">
        Press <kbd className="px-2 py-1 bg-gray-100 rounded">Space</kbd> to flip,{' '}
        <kbd className="px-2 py-1 bg-gray-100 rounded">1-4</kbd> to rate
      </p>
    </div>
  )
}
