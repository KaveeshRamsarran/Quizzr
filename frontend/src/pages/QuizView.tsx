import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ArrowLeftIcon, ChevronDownIcon, PlayIcon, TrashIcon } from '@heroicons/react/24/outline'
import { errorMessage, quizzesApi } from '../lib/api'
import { QUESTION_TYPE_LABEL, duration, relativeDate } from '../lib/format'
import { Button, ConfirmDialog, EmptyState, ErrorState, PageLoading, SectionTitle } from '../components/ui'
import { CountUp, EASE_OUT, Item, Page, Stagger } from '../components/motion'
import type { QuizQuestion } from '../types'

function answerText(q: QuizQuestion) {
  if (!q.correct_answer) return ''
  if (q.options?.length) return q.options.find((o) => o.id === q.correct_answer)?.text ?? q.correct_answer
  return q.correct_answer
}

export default function QuizView() {
  const { id } = useParams()
  const quizId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState<number | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const quiz = useQuery({ queryKey: ['quizzes', quizId], queryFn: () => quizzesApi.get(quizId), enabled: Number.isFinite(quizId) })
  const attempts = useQuery({ queryKey: ['quizzes', quizId, 'attempts'], queryFn: () => quizzesApi.listAttempts(quizId), enabled: Number.isFinite(quizId) })

  const remove = useMutation({
    mutationFn: () => quizzesApi.delete(quizId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quizzes'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      toast.success('Quiz deleted')
      navigate('/quizzes')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  if (quiz.isLoading) return <PageLoading />
  if (quiz.isError || !quiz.data) {
    return (
      <div className="page">
        <Link to="/quizzes" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Quizzes</Link>
        <ErrorState message={errorMessage(quiz.error, 'This quiz couldn’t be found.')} onRetry={() => quiz.refetch()} />
      </div>
    )
  }

  const q = quiz.data
  const completed = (attempts.data ?? []).filter((a) => a.is_completed)
  const best = completed.length ? Math.max(...completed.map((a) => a.score ?? 0)) : null

  return (
    <Page>
      <Link to="/quizzes" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Quizzes</Link>

      <motion.section className="card card--accent" style={{ padding: 'var(--space-xl)', borderRadius: 26 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_OUT }}>
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="min-w-0">
            <h1 style={{ fontSize: 'clamp(1.5rem, 1.1rem + 1.2vw, 2.1rem)' }}>{q.name}</h1>
            <p style={{ marginTop: 8, opacity: 0.85 }}>
              {q.question_count} questions{q.time_limit_minutes ? `, ${q.time_limit_minutes} minute limit` : ', no time limit'}, pass mark {q.pass_percentage}%
            </p>
          </div>
          {q.question_count > 0 && (
            <Link to={`/quizzes/${q.id}/take`} className="btn btn--light btn--lg"><PlayIcon aria-hidden="true" /> {completed.length ? 'Take it again' : 'Start the quiz'}</Link>
          )}
        </div>
        <div className="flex flex-wrap gap-8" style={{ marginTop: 24 }}>
          <div><div className="stat__value" style={{ color: 'inherit', margin: 0 }}><CountUp value={completed.length} /></div><div className="small" style={{ opacity: 0.8 }}>Attempts</div></div>
          <div><div className="stat__value" style={{ color: 'inherit', margin: 0 }}>{best != null ? <CountUp value={Math.round(best)} suffix="%" /> : '–'}</div><div className="small" style={{ opacity: 0.8 }}>Best score</div></div>
        </div>
      </motion.section>

      {completed.length > 0 && (
        <section className="section">
          <SectionTitle title="Your attempts" />
          <Stagger className="card list">
            {completed.map((a) => {
              const pct = Math.round(a.score ?? 0)
              const passed = pct >= q.pass_percentage
              return (
                <Item key={a.id} className="list-row">
                  <div className="figure-font" style={{ fontSize: '1.5rem', fontWeight: 300, minWidth: 64, color: 'var(--color-ink)' }}>{pct}%</div>
                  <div className="flex-1 min-w-0">
                    <div className="row-title small">{a.correct_count} of {q.question_count} correct</div>
                    <div className="row-meta">{relativeDate(a.time_completed)}, took {duration(a.time_spent_seconds)}</div>
                  </div>
                  <span className={`badge ${passed ? 'badge--success' : 'badge--error'}`}>{passed ? 'Passed' : 'Below pass mark'}</span>
                </Item>
              )
            })}
          </Stagger>
        </section>
      )}

      <section className="section">
        <SectionTitle title="Questions" action={<span className="small muted">Tap a question to see its answer</span>} />
        {q.questions.length === 0 ? (
          <div className="card"><EmptyState icon={<PlayIcon />} title="No questions in this quiz" /></div>
        ) : (
          <Stagger className="grid gap-2">
            {q.questions.map((question, i) => {
              const isOpen = open === question.id
              return (
                <Item key={question.id} className="card">
                  <button type="button" className="w-full text-left flex items-start gap-3" style={{ padding: 16, background: 'none', border: 0, cursor: 'pointer' }} aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : question.id)}>
                    <span className="option__key" style={{ marginTop: 1 }}>{i + 1}</span>
                    <span className="flex-1 min-w-0">
                      <span className="row-title block">{question.question_text}</span>
                      <span className="row-meta block">{QUESTION_TYPE_LABEL[question.question_type] ?? question.question_type}{question.topic ? `, ${question.topic}` : ''}</span>
                    </span>
                    <motion.span animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }} style={{ display: 'inline-flex', color: 'var(--color-muted)' }}>
                      <ChevronDownIcon style={{ width: 18, height: 18 }} aria-hidden="true" />
                    </motion.span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.12 } }} transition={{ duration: 0.25, ease: EASE_OUT }}>
                        <div className="notice notice--success" style={{ margin: '0 16px 16px 58px' }}>
                          <span><strong>Answer:</strong> {answerText(question)}{question.explanation ? <span className="muted"> {question.explanation}</span> : null}</span>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Item>
              )
            })}
          </Stagger>
        )}
      </section>

      <div className="section">
        <Button size="sm" variant="ghost" icon={<TrashIcon />} onClick={() => setConfirmDelete(true)}>Delete quiz</Button>
      </div>

      <ConfirmDialog open={confirmDelete} title="Delete this quiz?" body="The quiz, its questions and every attempt will be deleted."
        confirmLabel="Delete quiz" loading={remove.isPending} onConfirm={() => remove.mutate()} onClose={() => setConfirmDelete(false)} />
    </Page>
  )
}
