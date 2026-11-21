import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { CheckCircleIcon, ExclamationCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { errorMessage, generationApi } from '../lib/api'
import { Button, Dialog, Field, Segmented } from './ui'
import { EASE_OUT, ProgressBar } from './motion'
import type { DeckGenerationRequest, GenerationJob, QuizGenerationRequest } from '../types'

type Kind = 'deck' | 'quiz'
type Difficulty = 'mixed' | 'easy' | 'hard'

const CARD_TYPES = [
  { value: 'basic', label: 'Definitions and key points' },
  { value: 'cloze', label: 'Fill-the-gap cards' },
  { value: 'reverse', label: 'Reverse (description to term)' },
] as const

const QUESTION_TYPES = [
  { value: 'multiple_choice', label: 'Multiple choice' },
  { value: 'true_false', label: 'True or false' },
  { value: 'fill_blank', label: 'Fill in the blank' },
  { value: 'short_answer', label: 'Short answer' },
] as const

const COUNTS = { deck: [10, 20, 30, 50], quiz: [5, 10, 15, 20] }

export default function GenerateDialog({
  kind, open, onClose, documentId, documentTitle,
}: { kind: Kind; open: boolean; onClose: () => void; documentId: number; documentTitle: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [title, setTitle] = useState('')
  const [count, setCount] = useState(kind === 'deck' ? 20 : 10)
  const [difficulty, setDifficulty] = useState<Difficulty>('mixed')
  const [cardTypes, setCardTypes] = useState<string[]>(['basic', 'cloze'])
  const [questionTypes, setQuestionTypes] = useState<string[]>(['multiple_choice', 'true_false', 'fill_blank'])
  const [timeLimit, setTimeLimit] = useState<string>('none')
  const [focus, setFocus] = useState('')
  const [job, setJob] = useState<GenerationJob | null>(null)

  useEffect(() => {
    if (open) {
      setJob(null)
      setTitle('')
      setCount(kind === 'deck' ? 20 : 10)
    }
  }, [open, kind])

  const status = useQuery({
    queryKey: ['job', job?.job_id],
    queryFn: () => generationApi.getJobStatus(job!.job_id),
    enabled: !!job && open,
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'completed' || s === 'failed' ? false : 600
    },
  })
  const current = status.data ?? job

  useEffect(() => {
    if (current?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: [kind === 'deck' ? 'decks' : 'quizzes'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    }
  }, [current?.status, kind, queryClient])

  const start = useMutation({
    mutationFn: () => {
      const focus_topics = focus.trim() ? focus.split(',').map((t) => t.trim()).filter(Boolean) : undefined
      if (kind === 'deck') {
        const body: DeckGenerationRequest = {
          document_id: documentId, title: title.trim() || undefined, card_count: count,
          card_types: cardTypes as DeckGenerationRequest['card_types'], difficulty, focus_topics,
        }
        return generationApi.generateDeck(body)
      }
      const body: QuizGenerationRequest = {
        document_id: documentId, title: title.trim() || undefined, question_count: count,
        question_types: questionTypes as QuizGenerationRequest['question_types'], difficulty,
        time_limit_minutes: timeLimit === 'none' ? null : Number(timeLimit), focus_topics,
      }
      return generationApi.generateQuiz(body)
    },
    onSuccess: (j) => {
      setJob(j)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const toggle = (list: string[], value: string, set: (v: string[]) => void) =>
    set(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])

  const typesChosen = kind === 'deck' ? cardTypes.length > 0 : questionTypes.length > 0
  const running = current && (current.status === 'pending' || current.status === 'processing')
  const step = !current ? 'form' : running ? 'running' : current.status

  return (
    <Dialog open={open} onClose={onClose} title={kind === 'deck' ? 'Make flashcards' : 'Make a quiz'}>
      <AnimatePresence mode="wait" initial={false}>
        {step === 'form' && (
          <motion.form key="form" onSubmit={(e) => { e.preventDefault(); if (typesChosen) start.mutate() }} className="grid gap-5"
            initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.22, ease: EASE_OUT }}>
            <p className="muted small" style={{ marginTop: -8 }}>
              From “{documentTitle}”. Ready in a few seconds.
            </p>

            <div className="field">
              <span className="label">{kind === 'deck' ? 'How many cards?' : 'How many questions?'}</span>
              <Segmented<string>
                label={kind === 'deck' ? 'Number of cards' : 'Number of questions'}
                value={String(count)}
                onChange={(v) => setCount(Number(v))}
                options={COUNTS[kind].map((n) => ({ value: String(n), label: String(n) }))}
              />
            </div>

            <fieldset className="grid gap-2" style={{ border: 0, padding: 0, margin: 0 }}>
              <legend className="label" style={{ marginBottom: 8 }}>{kind === 'deck' ? 'Card types' : 'Question types'}</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {(kind === 'deck' ? CARD_TYPES : QUESTION_TYPES).map((t) => {
                  const list = kind === 'deck' ? cardTypes : questionTypes
                  const set = kind === 'deck' ? setCardTypes : setQuestionTypes
                  return (
                    <label key={t.value} className="check">
                      <input type="checkbox" checked={list.includes(t.value)} onChange={() => toggle(list, t.value, set)} />
                      <span>{t.label}</span>
                    </label>
                  )
                })}
              </div>
              {!typesChosen && <p className="field-error">Choose at least one type.</p>}
            </fieldset>

            <div className="grid gap-5 sm:grid-cols-2">
              <div className="field">
                <span className="label">Difficulty</span>
                <Segmented<Difficulty>
                  label="Difficulty"
                  value={difficulty}
                  onChange={setDifficulty}
                  options={[{ value: 'mixed', label: 'Mixed' }, { value: 'easy', label: 'Easier' }, { value: 'hard', label: 'Harder' }]}
                />
              </div>
              {kind === 'quiz' && (
                <Field label="Time limit" htmlFor="gen-time">
                  <select id="gen-time" className="select" value={timeLimit} onChange={(e) => setTimeLimit(e.target.value)}>
                    <option value="none">No time limit</option>
                    <option value="5">5 minutes</option>
                    <option value="10">10 minutes</option>
                    <option value="20">20 minutes</option>
                    <option value="30">30 minutes</option>
                  </select>
                </Field>
              )}
            </div>

            <details>
              <summary className="link small" style={{ cursor: 'pointer', listStyle: 'none' }}>More options</summary>
              <div className="grid gap-4" style={{ marginTop: 14 }}>
                <Field label={kind === 'deck' ? 'Deck name' : 'Quiz name'} htmlFor="gen-title" help="Leave blank to name it after the document.">
                  <input id="gen-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={255} />
                </Field>
                <Field label="Focus on topics" htmlFor="gen-focus" help="Optional. Headings or words, separated by commas.">
                  <input id="gen-focus" className="input" value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="e.g. photosynthesis, membranes" />
                </Field>
              </div>
            </details>

            <div className="dialog__actions" style={{ marginTop: 4 }}>
              <Button onClick={onClose}>Cancel</Button>
              <Button type="submit" variant="primary" loading={start.isPending} disabled={!typesChosen} icon={<SparklesIcon />}>
                {kind === 'deck' ? 'Make flashcards' : 'Make quiz'}
              </Button>
            </div>
          </motion.form>
        )}

        {step === 'running' && current && (
          <motion.div key="running" aria-live="polite" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.22, ease: EASE_OUT }}>
            <div className="grid justify-items-center text-center gap-3" style={{ padding: '12px 0 4px' }}>
              <motion.div className="empty__icon" animate={{ rotate: [0, 8, -8, 0], scale: [1, 1.05, 1] }} transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}>
                <SparklesIcon />
              </motion.div>
              <h3>{kind === 'deck' ? 'Writing your flashcards' : 'Writing your quiz'}</h3>
              <p className="muted small">{current.step || 'Starting'}…</p>
            </div>
            <div style={{ marginTop: 20 }}><ProgressBar value={current.progress ?? 5} label="Generation progress" /></div>
            <div className="dialog__actions">
              <Button variant="ghost" onClick={async () => { await generationApi.cancel(current.job_id).catch(() => undefined); onClose() }}>Cancel</Button>
              <Button onClick={onClose}>Keep going in the background</Button>
            </div>
          </motion.div>
        )}

        {step === 'completed' && current?.result_id && (
          <motion.div key="done" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: 'spring', stiffness: 320, damping: 24 }}>
            <div className="grid justify-items-center text-center gap-3" style={{ padding: '12px 0 4px' }}>
              <motion.div initial={{ scale: 0, rotate: -60 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 420, damping: 14, delay: 0.05 }}>
                <CheckCircleIcon style={{ width: 64, height: 64, color: 'var(--color-success)' }} aria-hidden="true" />
              </motion.div>
              <h3>{kind === 'deck' ? 'Your flashcards are ready' : 'Your quiz is ready'}</h3>
              <p className="muted small">Every item links back to the page it came from.</p>
            </div>
            <div className="dialog__actions" style={{ justifyContent: 'center' }}>
              {kind === 'deck' ? (
                <>
                  <Button onClick={() => navigate(`/decks/${current.result_id}`)}>See the cards</Button>
                  <Button variant="primary" onClick={() => navigate(`/decks/${current.result_id}/study`)}>Start studying</Button>
                </>
              ) : (
                <>
                  <Button onClick={() => navigate(`/quizzes/${current.result_id}`)}>See the questions</Button>
                  <Button variant="primary" onClick={() => navigate(`/quizzes/${current.result_id}/take`)}>Take the quiz</Button>
                </>
              )}
            </div>
          </motion.div>
        )}

        {step === 'failed' && current && (
          <motion.div key="failed" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{current.message || 'Generation failed.'}</div>
            <div className="dialog__actions">
              <Button onClick={onClose}>Close</Button>
              <Button variant="primary" onClick={() => setJob(null)}>Change options</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Dialog>
  )
}
