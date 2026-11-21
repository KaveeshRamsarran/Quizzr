import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { CheckIcon, ClockIcon, SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { errorMessage, quizzesApi } from '../lib/api'
import { QUESTION_TYPE_LABEL, duration, pages } from '../lib/format'
import { Brand, Button, ConfirmDialog, ErrorState, PageLoading, SectionTitle } from '../components/ui'
import { CountUp, EASE_OUT, Item, ProgressBar, Ring, Stagger } from '../components/motion'
import type { AnswerResult, AttemptResult, QuizAttempt, QuizQuestion } from '../types'

function shuffle<T>(list: T[]): T[] {
  const copy = [...list]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function optionText(q: { options: QuizQuestion['options'] }, id: string | null | undefined) {
  if (!id) return ''
  return q.options?.find((o) => o.id === id)?.text ?? id
}

export default function QuizTake() {
  const { id } = useParams()
  const quizId = Number(id)
  const queryClient = useQueryClient()
  const quiz = useQuery({ queryKey: ['quizzes', quizId], queryFn: () => quizzesApi.get(quizId), staleTime: Infinity })

  const [attempt, setAttempt] = useState<QuizAttempt | null>(null)
  const [startError, setStartError] = useState<string | null>(null)
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<string>('')
  const [results, setResults] = useState<Record<number, AnswerResult & { given: string }>>({})
  const [checking, setChecking] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [final, setFinal] = useState<AttemptResult | null>(null)
  const [confirmFinish, setConfirmFinish] = useState(false)
  const [now, setNow] = useState(Date.now())
  const shownAt = useRef(Date.now())
  const started = useRef(false)

  const questions = useMemo(() => {
    const q = quiz.data
    if (!q) return []
    const ordered = q.shuffle_questions ? shuffle(q.questions) : [...q.questions].sort((a, b) => a.question_order - b.question_order)
    return ordered.map((question) => ({
      ...question,
      options: question.options && q.shuffle_options && question.question_type !== 'true_false' ? shuffle(question.options) : question.options,
    }))
    // Shuffle once per attempt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quiz.data, attempt?.id])

  const start = useCallback(async () => {
    setStartError(null)
    try {
      const a = await quizzesApi.startAttempt(quizId)
      setAttempt(a)
      setIndex(0)
      setResults({})
      setFinal(null)
      setSelected('')
      shownAt.current = Date.now()
    } catch (err) {
      setStartError(errorMessage(err, 'The quiz couldn’t be started.'))
    }
  }, [quizId])

  useEffect(() => {
    if (quiz.data && !started.current) {
      started.current = true
      start()
    }
  }, [quiz.data, start])

  const limitMs = quiz.data?.time_limit_minutes ? quiz.data.time_limit_minutes * 60_000 : null
  const startedAt = attempt ? new Date(/[zZ]$/.test(attempt.time_started) ? attempt.time_started : `${attempt.time_started}Z`).getTime() : Date.now()
  const remaining = limitMs ? Math.max(0, startedAt + limitMs - now) : null

  useEffect(() => {
    if (!limitMs || final) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [limitMs, final])

  const finish = useCallback(async () => {
    if (!attempt || finishing || final) return
    setFinishing(true)
    setConfirmFinish(false)
    try {
      const r = await quizzesApi.finishAttempt(quizId, attempt.id)
      setFinal(r)
      queryClient.invalidateQueries({ queryKey: ['quizzes'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      window.scrollTo(0, 0)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setFinishing(false)
    }
  }, [attempt, finishing, final, quizId, queryClient])

  useEffect(() => {
    if (remaining === 0 && attempt && !final) {
      toast('Time’s up')
      finish()
    }
  }, [remaining, attempt, final, finish])

  const question = questions[index]
  const result = question ? results[question.id] : undefined
  const answeredCount = Object.keys(results).length

  useEffect(() => {
    setSelected(question && results[question.id] ? results[question.id].given : '')
    shownAt.current = Date.now()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index])

  const check = async () => {
    if (!attempt || !question || !selected.trim() || result) return
    setChecking(true)
    try {
      const r = await quizzesApi.submitAnswer(quizId, attempt.id, question.id, selected.trim(), Date.now() - shownAt.current)
      setResults((prev) => ({ ...prev, [question.id]: { ...r, given: selected.trim() } }))
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setChecking(false)
    }
  }

  const next = () => {
    if (index < questions.length - 1) setIndex(index + 1)
    else if (answeredCount === questions.length) finish()
    else setConfirmFinish(true)
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!question || final) return
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === 'Enter' && !typing) {
        e.preventDefault()
        if (result) next()
        else check()
      }
      if (!typing && !result && question.options?.length) {
        const n = Number(e.key)
        if (n >= 1 && n <= question.options.length) setSelected(question.options[n - 1].id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (quiz.isLoading || (!attempt && !startError)) return <PageLoading />

  const header = (
    <header style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--color-paper)' }}>
      <div className="page" style={{ paddingBlock: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
        <Link to={`/quizzes/${quizId}`} aria-label="Back to the quiz" className="hidden sm:block"><Brand /></Link>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between small" style={{ marginBottom: 6 }}>
            <span className="row-title truncate">{quiz.data?.name ?? 'Quiz'}</span>
            {remaining != null && !final && (
              <span className="figure-font inline-flex items-center gap-1" style={{ color: remaining < 60_000 ? 'var(--color-error)' : 'var(--color-muted)' }} aria-label="Time remaining">
                <ClockIcon style={{ width: 16, height: 16 }} aria-hidden="true" />{duration(remaining / 1000)}
              </span>
            )}
          </div>
          <ProgressBar value={final ? 100 : questions.length ? (answeredCount / questions.length) * 100 : 0} label="Questions answered" />
        </div>
        <Link to={`/quizzes/${quizId}`} className="btn btn--ghost btn--sm"><XMarkIcon aria-hidden="true" /> Leave</Link>
      </div>
    </header>
  )

  if (startError || quiz.isError) {
    return (<>{header}<div className="page page--narrow"><ErrorState message={startError ?? errorMessage(quiz.error)} onRetry={start} /></div></>)
  }

  if (final) {
    const passed = final.percentage >= (quiz.data?.pass_percentage ?? 70)
    const topics = Object.entries(final.by_topic ?? {})
    return (
      <>
        {header}
        <main className="page page--narrow">
          <motion.section className="card text-center grid justify-items-center gap-4" style={{ padding: 'var(--space-xl)', borderRadius: 28 }} initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4, ease: EASE_OUT }}>
            <motion.span className={`badge ${passed ? 'badge--success' : 'badge--accent'}`} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              {passed ? <><SparklesIcon /> Passed</> : 'Keep practising'}
            </motion.span>
            <Ring value={final.percentage} size={180}>
              <div>
                <div className="stat__value" style={{ margin: 0, fontSize: '2.8rem' }}><CountUp value={final.percentage} suffix="%" /></div>
                <div className="tiny muted">score</div>
              </div>
            </Ring>
            <div>
              <h1 style={{ fontSize: 'var(--text-2xl)' }}>{final.correct_count} of {questions.length} correct</h1>
              <p className="muted" style={{ marginTop: 6 }}>Finished in {duration(final.time_spent_seconds)}. Pass mark {quiz.data?.pass_percentage}%.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="primary" size="lg" onClick={start}>Take it again</Button>
              <Link to={`/quizzes/${quizId}`} className="btn btn--lg">Back to the quiz</Link>
            </div>
          </motion.section>

          {topics.length > 1 && (
            <section className="section">
              <SectionTitle title="By topic" />
              <Stagger className="card list">
                {topics.sort((a, b) => a[1].correct / a[1].total - b[1].correct / b[1].total).map(([topic, s]) => {
                  const pct = Math.round((s.correct / s.total) * 100)
                  return (
                    <Item key={topic} className="list-row">
                      <div className="flex-1 min-w-0">
                        <div className="row-title small">{topic}</div>
                        <div style={{ marginTop: 8 }}><ProgressBar value={pct} label={`${topic} score`} className="progress--thin" /></div>
                      </div>
                      <span className="figure-font small" style={{ color: pct < 70 ? 'var(--color-error)' : 'var(--color-ink)' }}>{s.correct}/{s.total}</span>
                    </Item>
                  )
                })}
              </Stagger>
            </section>
          )}

          <section className="section">
            <SectionTitle title="Review your answers" />
            <Stagger className="grid gap-2">
              {final.questions.map((q, i) => {
                const given = q.options?.length ? optionText(q, q.user_answer) : q.user_answer
                const correct = q.options?.length ? optionText(q, q.correct_answer) : q.correct_answer
                return (
                  <Item key={q.question_id} className="card">
                    <div className="flex gap-3" style={{ padding: 16 }}>
                      <span className="option__key" style={{ background: q.is_correct ? 'var(--color-success-soft)' : 'var(--color-error-soft)', color: q.is_correct ? 'var(--color-success)' : 'var(--color-error)' }}>
                        {q.is_correct ? <CheckIcon /> : <XMarkIcon />}
                      </span>
                      <div className="min-w-0">
                        <p className="row-title"><span className="muted">{i + 1}.</span> {q.question_text}</p>
                        {!q.is_correct && (
                          <p className="small" style={{ marginTop: 6 }}>
                            {given ? <>You said “{given}”. </> : <>Skipped. </>}
                            Answer: <strong style={{ color: 'var(--color-ink)' }}>{correct}</strong>
                          </p>
                        )}
                        {q.explanation && <p className="small muted" style={{ marginTop: 4 }}>{q.explanation}</p>}
                      </div>
                    </div>
                  </Item>
                )
              })}
            </Stagger>
          </section>
        </main>
      </>
    )
  }

  if (!question) return <>{header}<div className="page"><p className="muted">This quiz has no questions.</p></div></>

  const isChoice = !!question.options?.length
  const source = question.source_snippets?.[0]

  return (
    <>
      {header}
      <main className="page page--narrow" style={{ paddingTop: 'var(--space-md)' }}>
        <nav className="q-dots" aria-label="Questions" style={{ marginBottom: 20 }}>
          {questions.map((q, i) => (
            <button
              key={q.id}
              type="button"
              className="q-dot"
              aria-current={i === index ? 'step' : undefined}
              aria-label={`Question ${i + 1}${results[q.id] ? (results[q.id].is_correct ? ', correct' : ', incorrect') : ''}`}
              data-state={results[q.id] ? (results[q.id].is_correct ? 'correct' : 'wrong') : undefined}
              onClick={() => setIndex(i)}
            >
              {i + 1}
            </button>
          ))}
        </nav>

        <AnimatePresence mode="wait">
          <motion.section
            key={question.id}
            className="card"
            style={{ padding: 'var(--space-lg)', borderRadius: 24 }}
            aria-labelledby="question-text"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30, transition: { duration: 0.18 } }}
            transition={{ duration: 0.32, ease: EASE_OUT }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2" style={{ marginBottom: 14 }}>
              <span className="badge badge--accent">{QUESTION_TYPE_LABEL[question.question_type]}</span>
              <span className="small muted">Question {index + 1} of {questions.length}</span>
            </div>
            <h1 id="question-text" style={{ fontSize: 'clamp(1.2rem, 1rem + 0.7vw, 1.55rem)', lineHeight: 1.35, letterSpacing: '-0.015em' }}>
              {question.question_text}
            </h1>

            <div style={{ marginTop: 24 }}>
              {isChoice ? (
                <Stagger className="options">
                  {question.options!.map((o, i) => {
                    const state = result ? (o.id === result.correct_answer ? 'correct' : o.id === result.given ? 'wrong' : undefined) : undefined
                    return (
                      <Item key={o.id}>
                        <motion.button
                          type="button"
                          className="option"
                          aria-pressed={selected === o.id}
                          data-result={state}
                          disabled={!!result}
                          onClick={() => setSelected(o.id)}
                          whileTap={result ? undefined : { scale: 0.985 }}
                          animate={state === 'wrong' ? { x: [0, -6, 6, -4, 0] } : state === 'correct' ? { scale: [1, 1.02, 1] } : {}}
                          transition={{ duration: 0.4 }}
                        >
                          <span className="option__key">{state === 'correct' ? <CheckIcon /> : state === 'wrong' ? <XMarkIcon /> : i + 1}</span>
                          <span>{o.text}</span>
                        </motion.button>
                      </Item>
                    )
                  })}
                </Stagger>
              ) : (
                <div className="field">
                  <label htmlFor="answer" className="label">Your answer</label>
                  <input
                    id="answer"
                    className="input"
                    autoComplete="off"
                    value={selected}
                    disabled={!!result}
                    onChange={(e) => setSelected(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (result) next(); else check() } }}
                    aria-invalid={result ? !result.is_correct : undefined}
                    placeholder="Type your answer"
                    autoFocus
                  />
                </div>
              )}
            </div>

            <AnimatePresence>
              {result && (
                <motion.div
                  className={`notice ${result.is_correct ? 'notice--success' : 'notice--error'}`}
                  style={{ marginTop: 18 }}
                  aria-live="polite"
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 380, damping: 28 }}
                >
                  {result.is_correct ? <CheckIcon aria-hidden="true" /> : <XMarkIcon aria-hidden="true" />}
                  <div>
                    <p style={{ fontWeight: 600 }}>
                      {result.is_correct ? 'Correct!' : <>Not quite. The answer is {isChoice ? optionText(question, result.correct_answer) : result.correct_answer}.</>}
                    </p>
                    {result.explanation && <p style={{ marginTop: 4 }}>{result.explanation}</p>}
                    {source && <p className="muted" style={{ marginTop: 6 }}>{pages(question.source_pages)} of your notes.</p>}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.section>
        </AnimatePresence>

        <div className="flex flex-wrap items-center justify-between gap-3" style={{ marginTop: 20 }}>
          <Button variant="ghost" onClick={() => setIndex(Math.max(0, index - 1))} disabled={index === 0}>Previous</Button>
          <div className="flex flex-wrap gap-2">
            {!result && <Button variant="ghost" onClick={next}>Skip</Button>}
            {result ? (
              <Button variant="primary" size="lg" onClick={next} loading={finishing}>{index === questions.length - 1 ? 'See results' : 'Next question'}</Button>
            ) : (
              <Button variant="primary" size="lg" onClick={check} loading={checking} disabled={!selected.trim()}>Check answer</Button>
            )}
          </div>
        </div>
        <p className="small muted text-center" style={{ marginTop: 20 }}>
          {isChoice ? <>Press <span className="kbd">1</span> to <span className="kbd">{question.options!.length}</span> to choose and </> : 'Press '}
          <span className="kbd">Enter</span> to check. <button type="button" className="link" onClick={() => setConfirmFinish(true)}>Finish now</button>
        </p>
      </main>

      <ConfirmDialog
        open={confirmFinish}
        danger={false}
        title="Finish the quiz?"
        body={`${questions.length - answeredCount} ${questions.length - answeredCount === 1 ? 'question is' : 'questions are'} unanswered and will count as missed.`}
        confirmLabel="Finish and see results"
        loading={finishing}
        onConfirm={finish}
        onClose={() => setConfirmFinish(false)}
      />
    </>
  )
}
