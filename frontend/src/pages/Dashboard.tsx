import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowRightIcon, ArrowUpTrayIcon, BoltIcon, CheckCircleIcon, ClockIcon, DocumentTextIcon, FireIcon, LightBulbIcon, QuestionMarkCircleIcon, RectangleStackIcon,
} from '@heroicons/react/24/outline'
import { analyticsApi, decksApi, documentsApi, errorMessage, quizzesApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { relativeDate } from '../lib/format'
import { EmptyState, ErrorState, SectionTitle, SkeletonRows, StatusBadge } from '../components/ui'
import { CountUp, EASE_OUT, Item, Page, ProgressBar, Stagger } from '../components/motion'

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const overview = useQuery({ queryKey: ['analytics', 'overview'], queryFn: analyticsApi.getOverview })
  const decks = useQuery({ queryKey: ['decks', 'list', { limit: 50 }], queryFn: () => decksApi.list({ limit: 50 }) })
  const documents = useQuery({
    queryKey: ['documents', 'list', { limit: 5 }],
    queryFn: () => documentsApi.list({ limit: 5 }),
    refetchInterval: (q) => (q.state.data?.documents.some((d) => d.status === 'pending' || d.status === 'processing') ? 2000 : false),
  })
  const quizzes = useQuery({ queryKey: ['quizzes', 'list', { limit: 4 }], queryFn: () => quizzesApi.list({ limit: 4 }) })
  const suggestions = useQuery({ queryKey: ['analytics', 'suggestions'], queryFn: analyticsApi.getSuggestions })

  const o = overview.data
  const deckRows = [...(decks.data?.decks ?? [])].sort((a, b) => b.due_count + b.new_count - (a.due_count + a.new_count))
  const nextDeck = deckRows.find((d) => d.due_count + d.new_count > 0)
  const firstRun = documents.data && documents.data.total === 0
  const firstName = user && !user.is_guest ? user.name.split(' ')[0] : null

  return (
    <Page>
      <header className="page-header">
        <div>
          <h1>{greeting()}{firstName ? `, ${firstName}` : ''}</h1>
          <p className="page-header__sub">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        </div>
      </header>

      {firstRun ? (
        <motion.div className="card card--pad" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_OUT }}>
          <EmptyState
            icon={<ArrowUpTrayIcon />}
            title="Let’s make your first deck"
            action={<Link to="/upload" className="btn btn--primary btn--lg"><ArrowUpTrayIcon aria-hidden="true" /> Upload a PDF</Link>}
          >
            Upload lecture notes, slides or a textbook chapter. Quizzr turns it into flashcards and quizzes in seconds.
          </EmptyState>
        </motion.div>
      ) : (
        <>
          {/* The one thing to do next */}
          <motion.section
            className="card card--accent"
            style={{ padding: 'var(--space-xl)', borderRadius: 26 }}
            initial={{ opacity: 0, y: 14, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, ease: EASE_OUT }}
            aria-labelledby="next-title"
          >
            <div className="flex flex-wrap items-center justify-between gap-6">
              <div className="min-w-0">
                <p style={{ opacity: 0.85 }} className="small">{nextDeck ? 'Ready when you are' : 'All caught up'}</p>
                <h2 id="next-title" style={{ fontSize: 'clamp(1.5rem, 1.1rem + 1.4vw, 2.2rem)', marginTop: 6 }}>
                  {nextDeck
                    ? <><CountUp value={o?.cards_due_today ?? nextDeck.due_count + nextDeck.new_count} /> cards to study today</>
                    : 'Nothing due right now'}
                </h2>
                <p style={{ marginTop: 8, opacity: 0.85 }}>
                  {nextDeck ? <>Start with <strong>{nextDeck.name}</strong>.</> : 'Come back tomorrow, or practise a deck any time.'}
                </p>
              </div>
              {nextDeck ? (
                <Link to={`/decks/${nextDeck.id}/study`} className="btn btn--light btn--lg">
                  Start studying <ArrowRightIcon aria-hidden="true" />
                </Link>
              ) : deckRows[0] ? (
                <Link to={`/decks/${deckRows[0].id}/study?mode=all`} className="btn btn--light btn--lg">Practise a deck</Link>
              ) : (
                <Link to="/documents" className="btn btn--light btn--lg">Make a deck</Link>
              )}
            </div>
          </motion.section>

          {/* Figures */}
          {overview.isError ? (
            <div className="section"><ErrorState message={errorMessage(overview.error)} onRetry={() => overview.refetch()} /></div>
          ) : (
            <Stagger className="stats section">
              {[
                { label: 'Study streak', icon: FireIcon, value: o?.study_streak, unit: o?.study_streak === 1 ? 'day' : 'days' },
                { label: 'Reviewed today', icon: CheckCircleIcon, value: o?.cards_studied_today, unit: 'cards' },
                { label: 'Time studied', icon: ClockIcon, value: o?.total_study_time_minutes, unit: 'min' },
                { label: 'Answered right', icon: BoltIcon, value: o ? Math.round(o.overall_accuracy) : undefined, unit: '%' },
              ].map((s) => (
                <Item key={s.label} className="card stat">
                  <div className="stat__top"><span>{s.label}</span><s.icon aria-hidden="true" /></div>
                  <div className="stat__value">{s.value == null ? '–' : <CountUp value={s.value} />}<small>{s.unit}</small></div>
                </Item>
              ))}
            </Stagger>
          )}

          <div className="grid gap-x-8 lg:grid-cols-[minmax(0,1fr)_340px]">
            <div className="min-w-0">
              <section className="section" aria-labelledby="decks-title">
                <SectionTitle title={<span id="decks-title">Your flashcards</span>} action={<Link to="/decks" className="link small">See all</Link>} />
                {decks.isLoading ? <SkeletonRows rows={3} height={96} /> : decks.isError ? (
                  <ErrorState message={errorMessage(decks.error)} onRetry={() => decks.refetch()} />
                ) : deckRows.length === 0 ? (
                  <div className="card"><EmptyState icon={<RectangleStackIcon />} title="No flashcards yet" action={<Link to="/documents" className="btn btn--primary">Choose a document</Link>}>Open a document and choose Make flashcards.</EmptyState></div>
                ) : (
                  <Stagger className="grid gap-3 sm:grid-cols-2">
                    {deckRows.slice(0, 6).map((deck) => {
                      const ready = deck.due_count + deck.new_count
                      const mastery = deck.card_count ? (deck.mastered_count / deck.card_count) * 100 : 0
                      return (
                        <Item key={deck.id}>
                          <Link to={`/decks/${deck.id}`} className="card card--pad card-link" style={{ padding: 20 }}>
                            <div className="flex items-start justify-between gap-3">
                              <div className="icon-tile"><RectangleStackIcon aria-hidden="true" /></div>
                              {ready > 0 ? <span className="badge badge--accent">{ready} to study</span> : <span className="badge badge--success"><CheckCircleIcon /> Done</span>}
                            </div>
                            <h3 className="truncate" style={{ marginTop: 14 }}>{deck.name}</h3>
                            <p className="row-meta">{deck.card_count} cards, studied {relativeDate(deck.last_studied)}</p>
                            <div className="flex items-center gap-3" style={{ marginTop: 14 }}>
                              <div className="flex-1"><ProgressBar value={mastery} label={`${deck.name} mastery`} className="progress--thin" /></div>
                              <span className="tiny muted figure-font">{Math.round(mastery)}% mastered</span>
                            </div>
                          </Link>
                        </Item>
                      )
                    })}
                  </Stagger>
                )}
              </section>

              <section className="section" aria-labelledby="quizzes-title">
                <SectionTitle title={<span id="quizzes-title">Recent quizzes</span>} action={<Link to="/quizzes" className="link small">See all</Link>} />
                {quizzes.isLoading ? <SkeletonRows rows={2} /> : quizzes.data?.quizzes.length ? (
                  <Stagger className="card list">
                    {quizzes.data.quizzes.map((q) => (
                      <Item key={q.id} className="list-row list-row--link" onClick={() => navigate(`/quizzes/${q.id}`)}>
                        <div className="icon-tile icon-tile--neutral"><QuestionMarkCircleIcon aria-hidden="true" /></div>
                        <div className="min-w-0 flex-1">
                          <Link to={`/quizzes/${q.id}`} className="row-title truncate block" onClick={(e) => e.stopPropagation()}>{q.name}</Link>
                          <div className="row-meta">{q.question_count} questions{q.times_taken ? `, taken ${q.times_taken} ${q.times_taken === 1 ? 'time' : 'times'}` : ''}</div>
                        </div>
                        {q.average_score != null && <span className="badge figure-font">{Math.round(q.average_score)}%</span>}
                      </Item>
                    ))}
                  </Stagger>
                ) : (
                  <p className="muted small">No quizzes yet. Make one from any document.</p>
                )}
              </section>
            </div>

            <aside className="min-w-0">
              <section className="section" aria-labelledby="tips-title">
                <SectionTitle title={<span id="tips-title">Next steps</span>} />
                {suggestions.data?.length ? (
                  <Stagger className="grid gap-2">
                    {suggestions.data.map((s) => {
                      const to = s.action === 'study_deck' && s.target_id ? `/decks/${s.target_id}/study`
                        : s.action === 'upload' ? '/upload'
                        : s.action === 'open_documents' ? '/documents'
                        : s.action === 'take_quiz' ? '/quizzes'
                        : s.action === 'study_deck' ? '/decks' : null
                      const body = (
                        <div className="flex gap-3">
                          <LightBulbIcon aria-hidden="true" style={{ width: 20, height: 20, flex: 'none', marginTop: 2, color: 'var(--color-accent-text)' }} />
                          <div>
                            <p className="row-title">{s.title}</p>
                            <p className="row-meta">{s.description}</p>
                          </div>
                        </div>
                      )
                      return (
                        <Item key={s.title}>
                          {to ? <Link to={to} className="card card-link" style={{ padding: 16 }}>{body}</Link> : <div className="card" style={{ padding: 16 }}>{body}</div>}
                        </Item>
                      )
                    })}
                  </Stagger>
                ) : (
                  <p className="muted small">{suggestions.isLoading ? 'Loading…' : 'Nothing waiting. Nice work.'}</p>
                )}
              </section>

              <section className="section" aria-labelledby="docs-title">
                <SectionTitle title={<span id="docs-title">Recent documents</span>} action={<Link to="/documents" className="link small">See all</Link>} />
                {documents.isLoading ? <SkeletonRows rows={2} height={56} /> : (
                  <Stagger className="card list">
                    {documents.data?.documents.map((d) => (
                      <Item key={d.id} className="list-row list-row--link" onClick={() => navigate(`/documents/${d.id}`)}>
                        <DocumentTextIcon aria-hidden="true" style={{ width: 20, height: 20, flex: 'none', color: 'var(--color-muted)' }} />
                        <Link to={`/documents/${d.id}`} className="row-title truncate flex-1 small" onClick={(e) => e.stopPropagation()}>{d.title || d.original_filename}</Link>
                        <StatusBadge status={d.status} />
                      </Item>
                    ))}
                  </Stagger>
                )}
              </section>
            </aside>
          </div>
        </>
      )}
    </Page>
  )
}
