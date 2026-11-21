import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { CheckCircleIcon, SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { decksApi, errorMessage } from '../lib/api'
import { CARD_TYPE_LABEL, duration, pages } from '../lib/format'
import { getCardsPerSession } from '../lib/theme'
import { Brand, Button, ErrorState, PageLoading } from '../components/ui'
import { CountUp, EASE_OUT, ProgressBar, Ring } from '../components/motion'
import FlipCard from '../components/FlipCard'
import type { Card } from '../types'

type Rating = 'again' | 'hard' | 'good' | 'easy'
const RATINGS: { value: Rating; label: string; hint: string; key: string }[] = [
  { value: 'again', label: 'Again', hint: 'Didn’t know', key: '1' },
  { value: 'hard', label: 'Hard', hint: 'Took a while', key: '2' },
  { value: 'good', label: 'Good', hint: 'Knew it', key: '3' },
  { value: 'easy', label: 'Easy', hint: 'Instantly', key: '4' },
]

function ClozeText({ text }: { text: string }) {
  const parts = text.split('_____')
  return (
    <span>
      {parts.map((part, i) => (
        <span key={i}>
          {part}
          {i < parts.length - 1 && <span className="cloze-blank" aria-label="blank">&nbsp;?&nbsp;</span>}
        </span>
      ))}
    </span>
  )
}

export default function StudyMode() {
  const { id } = useParams()
  const deckId = Number(id)
  const [params] = useSearchParams()
  const mode = params.get('mode') === 'all' ? 'all' : 'due'
  const queryClient = useQueryClient()

  const deck = useQuery({ queryKey: ['decks', deckId], queryFn: () => decksApi.get(deckId) })
  const session = useQuery({
    queryKey: ['study', deckId, mode],
    queryFn: () => decksApi.getStudyCards(deckId, mode === 'all' ? 200 : getCardsPerSession(), mode),
    staleTime: Infinity,
    gcTime: 0,
  })

  const [queue, setQueue] = useState<Card[]>([])
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [direction, setDirection] = useState<Rating>('good')
  const [tally, setTally] = useState<Record<Rating, number>>({ again: 0, hard: 0, good: 0, easy: 0 })
  const [startedAt, setStartedAt] = useState(() => Date.now())
  const [finishedAt, setFinishedAt] = useState<number | null>(null)
  const shownAt = useRef(Date.now())

  useEffect(() => {
    if (session.data) {
      setQueue(session.data)
      setIndex(0)
      setTally({ again: 0, hard: 0, good: 0, easy: 0 })
      setFinishedAt(null)
      setStartedAt(Date.now())
    }
  }, [session.data])

  const card = queue[index]
  const done = queue.length > 0 && index >= queue.length
  const uniqueTotal = useMemo(() => new Set(queue.map((c) => c.id)).size, [queue])

  useEffect(() => {
    shownAt.current = Date.now()
    setFlipped(false)
  }, [index])

  useEffect(() => {
    if (done && !finishedAt) {
      setFinishedAt(Date.now())
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    }
  }, [done, finishedAt, queryClient])

  const rate = useCallback(async (rating: Rating) => {
    if (!card || submitting) return
    setSubmitting(true)
    try {
      await decksApi.reviewCard(deckId, card.id, { rating, time_spent_ms: Date.now() - shownAt.current })
      setTally((t) => ({ ...t, [rating]: t[rating] + 1 }))
      setDirection(rating)
      if (rating === 'again') {
        setQueue((q) => (q.slice(index + 1).some((c) => c.id === card.id) ? q : [...q, card]))
      }
      setIndex((i) => i + 1)
    } catch (err) {
      toast.error(errorMessage(err, 'That rating didn’t save. Try again.'))
    } finally {
      setSubmitting(false)
    }
  }, [card, deckId, index, submitting])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || !card) return
      if (e.key === ' ' || e.key === 'Enter') {
        if (document.activeElement instanceof HTMLButtonElement && document.activeElement.dataset.rating) return
        e.preventDefault()
        setFlipped((f) => !f)
      } else if (flipped) {
        const r = RATINGS.find((x) => x.key === e.key)
        if (r) { e.preventDefault(); rate(r.value) }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [card, flipped, rate])

  if (session.isLoading || deck.isLoading) return <PageLoading />

  const header = (
    <header style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--color-paper)' }}>
      <div className="page" style={{ paddingBlock: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
        <Link to={`/decks/${deckId}`} aria-label="Back to the deck" className="hidden sm:block"><Brand /></Link>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between small" style={{ marginBottom: 6 }}>
            <span className="row-title truncate">{deck.data?.name ?? 'Deck'}</span>
            {!done && queue.length > 0 && <span className="muted figure-font">{Math.min(index + 1, queue.length)} / {queue.length}</span>}
          </div>
          <ProgressBar value={queue.length ? ((done ? queue.length : index) / queue.length) * 100 : 0} label="Session progress" />
        </div>
        <Link to={`/decks/${deckId}`} className="btn btn--ghost btn--sm"><XMarkIcon aria-hidden="true" /> End</Link>
      </div>
    </header>
  )

  if (session.isError) {
    return (<>{header}<div className="page page--narrow"><ErrorState message={errorMessage(session.error)} onRetry={() => session.refetch()} /></div></>)
  }

  if (queue.length === 0) {
    return (
      <>
        {header}
        <motion.div className="page page--narrow" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="card card--pad text-center grid justify-items-center gap-3" style={{ padding: 40 }}>
            <CheckCircleIcon style={{ width: 56, height: 56, color: 'var(--color-success)' }} aria-hidden="true" />
            <h1 style={{ fontSize: 'var(--text-2xl)' }}>You’re all caught up</h1>
            <p className="muted" style={{ maxWidth: '40ch' }}>Every card in this deck is scheduled for later. You can still practise the whole deck now.</p>
            <div className="flex flex-wrap justify-center gap-2" style={{ marginTop: 8 }}>
              {deck.data && deck.data.card_count > 0 && <Link to={`/decks/${deckId}/study?mode=all`} className="btn btn--primary">Practise all {deck.data.card_count}</Link>}
              <Link to="/dashboard" className="btn">Back home</Link>
            </div>
          </div>
        </motion.div>
      </>
    )
  }

  if (done) {
    const reviewed = Object.values(tally).reduce((a, b) => a + b, 0)
    const knew = tally.good + tally.easy
    const pct = reviewed ? Math.round((knew / reviewed) * 100) : 0
    return (
      <>
        {header}
        <motion.div className="page page--narrow" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4, ease: EASE_OUT }}>
          <div className="card text-center grid justify-items-center gap-4" style={{ padding: 'var(--space-xl)', borderRadius: 28 }}>
            <motion.span className="badge badge--accent" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <SparklesIcon /> Session complete
            </motion.span>
            <Ring value={pct} size={170}>
              <div>
                <div className="stat__value" style={{ margin: 0, fontSize: '2.6rem' }}><CountUp value={pct} suffix="%" /></div>
                <div className="tiny muted">knew it</div>
              </div>
            </Ring>
            <div>
              <h1 style={{ fontSize: 'var(--text-2xl)' }}>{pct >= 80 ? 'Great session!' : pct >= 50 ? 'Nice work' : 'Good practice'}</h1>
              <p className="muted" style={{ marginTop: 6 }}>{uniqueTotal} {uniqueTotal === 1 ? 'card' : 'cards'} in {duration(((finishedAt ?? Date.now()) - startedAt) / 1000)}. Missed cards come back tomorrow.</p>
            </div>
            <div className="grid grid-cols-4 gap-2 w-full" style={{ maxWidth: 440 }}>
              {RATINGS.map((r, i) => (
                <motion.div key={r.value} className="card--soft" style={{ borderRadius: 14, padding: '10px 4px' }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.06 }}>
                  <div className="figure-font" style={{ fontSize: '1.4rem', color: 'var(--color-ink)' }}>{tally[r.value]}</div>
                  <div className="tiny muted">{r.label}</div>
                </motion.div>
              ))}
            </div>
            <div className="flex flex-wrap justify-center gap-2" style={{ marginTop: 8 }}>
              <Link to="/dashboard" className="btn btn--primary btn--lg">Back home</Link>
              <Link to={`/decks/${deckId}`} className="btn btn--lg">Open the deck</Link>
            </div>
          </div>
        </motion.div>
      </>
    )
  }

  const isCloze = card.card_type === 'cloze' && (card.cloze_text || card.front).includes('_____')
  const prompt = isCloze ? card.cloze_text || card.front : card.front
  const source = card.source_snippets?.[0]
  const exitX = direction === 'again' ? -120 : 120

  return (
    <>
      {header}
      <main className="page page--narrow" style={{ paddingTop: 'var(--space-lg)' }}>
        <AnimatePresence mode="wait" custom={exitX}>
          <motion.div
            key={`${card.id}-${index}`}
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: exitX, rotate: exitX > 0 ? 4 : -4, transition: { duration: 0.22, ease: [0.7, 0, 0.84, 0] } }}
            transition={{ duration: 0.36, ease: EASE_OUT }}
          >
            <FlipCard
              flipped={flipped}
              onFlip={() => setFlipped((f) => !f)}
              front={
                <>
                  <span className="flip__meta">
                    <span className="badge badge--accent">{CARD_TYPE_LABEL[card.card_type] ?? 'Card'}</span>
                    <span className="tiny muted">{pages(card.source_pages)}</span>
                  </span>
                  <span className="flip__text">{isCloze ? <ClozeText text={prompt} /> : prompt}</span>
                  <span className="flip__hint">Tap or press <span className="kbd">Space</span> to see the answer</span>
                </>
              }
              back={
                <>
                  <span className="flip__meta">
                    <span className="small muted truncate" style={{ maxWidth: '75%' }}>{isCloze ? 'Answer' : card.front}</span>
                    <span className="tiny muted">{pages(card.source_pages)}</span>
                  </span>
                  <span className="flip__text flip__text--answer">{card.back}</span>
                  {source && source !== card.back ? (
                    <span className="flip__source"><strong className="row-title">From your notes:</strong> “{source}”</span>
                  ) : card.extra_explanation ? (
                    <span className="flip__source">{card.extra_explanation}</span>
                  ) : null}
                </>
              }
            />
          </motion.div>
        </AnimatePresence>

        <div style={{ marginTop: 'var(--space-lg)', minHeight: 96 }}>
          <AnimatePresence mode="wait" initial={false}>
            {flipped ? (
              <motion.div key="ratings" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.22, ease: EASE_OUT }}>
                <p className="small muted text-center" style={{ marginBottom: 10 }}>How well did you know it?</p>
                <div className="ratings">
                  {RATINGS.map((r) => (
                    <motion.button
                      key={r.value}
                      type="button"
                      data-rating={r.value}
                      className={`rating rating--${r.value}`}
                      onClick={() => rate(r.value)}
                      disabled={submitting}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {r.label}
                      <small><span className="kbd" style={{ height: 18, minWidth: 18, marginRight: 4 }}>{r.key}</span>{r.hint}</small>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div key="show" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.22, ease: EASE_OUT }}>
                <Button variant="primary" size="lg" block onClick={() => setFlipped(true)}>Show answer</Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </>
  )
}
