import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline'
import { quizzesApi } from '../lib/api'
import type { QuizQuestion, AttemptResult } from '../types'
import clsx from 'clsx'

export default function QuizTake() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const quizId = parseInt(id || '0')

  const [attemptId, setAttemptId] = useState<number | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<number, { answer: string; correct: boolean }>>({})
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startTime, setStartTime] = useState<number>(Date.now())
  const [elapsedTime, setElapsedTime] = useState(0)

  // Get quiz
  const { data: quiz, isLoading } = useQuery({
    queryKey: ['quiz', quizId],
    queryFn: () => quizzesApi.get(quizId),
    enabled: !!quizId,
  })

  // Start attempt
  const startMutation = useMutation({
    mutationFn: () => quizzesApi.startAttempt(quizId),
    onSuccess: (attempt) => {
      setAttemptId(attempt.id)
      setStartTime(Date.now())
    },
  })

  // Submit answer
  const answerMutation = useMutation({
    mutationFn: ({
      questionId,
      answer,
    }: {
      questionId: number
      answer: string
    }) => quizzesApi.submitAnswer(quizId, attemptId!, questionId, answer, Date.now() - startTime),
  })

  // Finish attempt
  const finishMutation = useMutation({
    mutationFn: () => quizzesApi.finishAttempt(quizId, attemptId!),
    onSuccess: (result) => {
      setResult(result)
    },
  })

  // Timer
  useEffect(() => {
    if (attemptId && !result) {
      const interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000))
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [attemptId, result, startTime])

  // Start quiz on mount
  useEffect(() => {
    if (quiz && !attemptId && !startMutation.isPending) {
      startMutation.mutate()
    }
  }, [quiz])

  const questions = quiz?.questions || []
  const currentQuestion = questions[currentIndex]
  const isLastQuestion = currentIndex === questions.length - 1

  const handleAnswer = async () => {
    if (!selectedAnswer || !currentQuestion) return

    const response = await answerMutation.mutateAsync({
      questionId: currentQuestion.id,
      answer: selectedAnswer,
    })

    setAnswers((prev) => ({
      ...prev,
      [currentQuestion.id]: {
        answer: selectedAnswer,
        correct: response.is_correct,
      },
    }))

    // Move to next question or finish
    if (isLastQuestion) {
      finishMutation.mutate()
    } else {
      setCurrentIndex((prev) => prev + 1)
      setSelectedAnswer(null)
      setStartTime(Date.now())
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (isLoading || startMutation.isPending) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  // Results screen
  if (result) {
    const passed = result.passed
    return (
      <div className="max-w-2xl mx-auto py-8">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="card p-8 text-center"
        >
          <div
            className={clsx(
              'w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6',
              passed ? 'bg-green-100' : 'bg-red-100'
            )}
          >
            {passed ? (
              <CheckCircleIcon className="w-10 h-10 text-green-600" />
            ) : (
              <XCircleIcon className="w-10 h-10 text-red-600" />
            )}
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {passed ? 'Congratulations!' : 'Keep Practicing!'}
          </h1>
          <p className="text-gray-600 mb-6">
            {passed
              ? 'You passed the quiz!'
              : "You didn't pass this time, but don't give up!"}
          </p>

          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="card p-4 bg-gray-50">
              <p className="text-3xl font-bold text-gray-900">{result.percentage}%</p>
              <p className="text-sm text-gray-500">Score</p>
            </div>
            <div className="card p-4 bg-gray-50">
              <p className="text-3xl font-bold text-green-600">{result.correct_count}</p>
              <p className="text-sm text-gray-500">Correct</p>
            </div>
            <div className="card p-4 bg-gray-50">
              <p className="text-3xl font-bold text-red-600">
                {result.total_questions - result.correct_count}
              </p>
              <p className="text-sm text-gray-500">Incorrect</p>
            </div>
          </div>

          <div className="flex gap-4 justify-center">
            <Link to={`/quizzes/${quizId}`} className="btn-secondary">
              View Quiz
            </Link>
            <button
              onClick={() => {
                setAttemptId(null)
                setCurrentIndex(0)
                setSelectedAnswer(null)
                setAnswers({})
                setResult(null)
                startMutation.mutate()
              }}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </motion.div>
      </div>
    )
  }

  if (!currentQuestion) return null

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <Link
          to={`/quizzes/${quizId}`}
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-2" />
          Exit
        </Link>
        <div className="flex items-center gap-4">
          <div className="flex items-center text-gray-600">
            <ClockIcon className="w-5 h-5 mr-1" />
            {formatTime(elapsedTime)}
          </div>
          <div className="text-sm text-gray-500">
            {currentIndex + 1} / {questions.length}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-8">
        <div
          className="bg-green-500 h-2 rounded-full transition-all"
          style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestion.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
        >
          <div className="card p-6 mb-6">
            <span
              className={clsx(
                'inline-block mb-4 text-xs font-medium px-2 py-1 rounded',
                currentQuestion.question_type === 'multiple_choice' &&
                  'bg-blue-100 text-blue-700',
                currentQuestion.question_type === 'true_false' &&
                  'bg-purple-100 text-purple-700',
                currentQuestion.question_type === 'fill_blank' &&
                  'bg-orange-100 text-orange-700'
              )}
            >
              {currentQuestion.question_type.replace('_', ' ')}
            </span>
            <h2 className="text-xl font-medium text-gray-900">
              {currentQuestion.question_text}
            </h2>
          </div>

          {/* Answer options */}
          {currentQuestion.question_type === 'multiple_choice' && (
            <div className="space-y-3">
              {currentQuestion.options?.map((option, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedAnswer(option)}
                  className={clsx(
                    'w-full p-4 text-left rounded-lg border-2 transition-all',
                    selectedAnswer === option
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  )}
                >
                  <span className="font-medium text-gray-900">{option}</span>
                </button>
              ))}
            </div>
          )}

          {currentQuestion.question_type === 'true_false' && (
            <div className="grid grid-cols-2 gap-4">
              {['True', 'False'].map((option) => (
                <button
                  key={option}
                  onClick={() => setSelectedAnswer(option)}
                  className={clsx(
                    'p-6 text-center rounded-lg border-2 transition-all font-medium',
                    selectedAnswer === option
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-200 hover:border-gray-300 text-gray-700'
                  )}
                >
                  {option}
                </button>
              ))}
            </div>
          )}

          {(currentQuestion.question_type === 'fill_blank' ||
            currentQuestion.question_type === 'short_answer') && (
            <input
              type="text"
              value={selectedAnswer || ''}
              onChange={(e) => setSelectedAnswer(e.target.value)}
              placeholder="Type your answer..."
              className="input text-lg"
              autoFocus
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Submit button */}
      <button
        onClick={handleAnswer}
        disabled={!selectedAnswer || answerMutation.isPending}
        className="btn-primary w-full mt-6 py-3"
      >
        {answerMutation.isPending ? (
          'Submitting...'
        ) : isLastQuestion ? (
          'Finish Quiz'
        ) : (
          <>
            Next Question
            <ArrowRightIcon className="w-5 h-5 ml-2" />
          </>
        )}
      </button>
    </div>
  )
}
