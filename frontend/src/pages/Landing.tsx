import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ArrowPathIcon, ArrowRightIcon, ArrowUpTrayIcon, CheckIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { authErrorMessage, signInAsGuest } from '../lib/auth'
import { useAuthStore } from '../stores/authStore'
import { Brand, Button } from '../components/ui'
import { EASE_OUT, Reveal } from '../components/motion'
import FlipCard from '../components/FlipCard'

// Real output of the built-in generator on a page of sample cell-biology notes.
const SAMPLE = [
  { front: 'What is osmosis?', back: 'The diffusion of water across a selectively permeable membrane.', type: 'Definition', page: 1 },
  { front: 'Active transport requires energy in the form of _____ because it moves substances against their gradient.', back: 'ATP', type: 'Fill the gap', page: 1 },
  { front: 'What are ribosomes?', back: 'The sites of protein synthesis in all living cells.', type: 'Definition', page: 2 },
]

// SM-2 intervals for a card you keep rating Good (starting ease 2.5).
const GOOD_INTERVALS = [1, 6, 15, 38, 95]

function DemoCard() {
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const card = SAMPLE[index]

  const next = () => {
    setFlipped(false)
    setTimeout(() => setIndex((i) => (i + 1) % SAMPLE.length), flipped ? 180 : 0)
  }

  return (
    <div className="demo">
      <div className="demo__cards">
      <motion.div className="demo__stack" style={{ rotate: -4, scale: 0.94, y: 18 }} aria-hidden="true" />
      <motion.div className="demo__stack" style={{ rotate: 3, scale: 0.97, y: 9 }} aria-hidden="true" />
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 30, rotate: -2 }}
          animate={{ opacity: 1, y: 0, rotate: 0 }}
          exit={{ opacity: 0, x: 80, rotate: 6, transition: { duration: 0.22 } }}
          transition={{ duration: 0.5, ease: EASE_OUT }}
          style={{ position: 'relative' }}
        >
          <FlipCard
            flipped={flipped}
            onFlip={() => setFlipped((f) => !f)}
            label="Sample flashcard"
            front={
              <>
                <span className="flip__meta"><span className="badge badge--accent">{card.type}</span><span className="tiny muted">Page {card.page}</span></span>
                <span className="flip__text">{card.front}</span>
                <span className="flip__hint">Tap the card to turn it over</span>
              </>
            }
            back={
              <>
                <span className="flip__meta"><span className="badge badge--success"><CheckIcon /> Answer</span><span className="tiny muted">Page {card.page}</span></span>
                <span className="flip__text flip__text--answer">{card.back}</span>
                <span className="flip__hint">From cell-biology.pdf</span>
              </>
            }
          />
        </motion.div>
      </AnimatePresence>
      </div>
      <div className="flex items-center justify-between" style={{ marginTop: 28 }}>
        <span className="small muted figure-font">{index + 1} of {SAMPLE.length} sample cards</span>
        <Button size="sm" onClick={next} icon={<ArrowRightIcon />}>Next card</Button>
      </div>
    </div>
  )
}

export default function Landing() {
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()
  const [guestLoading, setGuestLoading] = useState(false)

  const tryAsGuest = async () => {
    setGuestLoading(true)
    try {
      await signInAsGuest()
      navigate('/upload')
    } catch (error) {
      toast.error(authErrorMessage(error))
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div>
      <header className="l-nav">
        <div className="l-wrap l-nav__inner">
          <Link to="/" aria-label="Quizzr home"><Brand /></Link>
          <nav aria-label="Main">
            <a href="#how" className="btn btn--ghost btn--sm hide-sm">How it works</a>
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn btn--sm">Open Quizzr</Link>
            ) : (
              <>
                <Link to="/login" className="btn btn--ghost btn--sm">Sign in</Link>
                <Link to="/register" className="btn btn--sm">Create account</Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="l-wrap hero" aria-labelledby="hero-title">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE_OUT }}>
            <h1 id="hero-title">Study from your own notes.</h1>
            <p className="hero__lead">Drop in a lecture PDF and get flashcards, quizzes and a review plan.</p>
            <div className="hero__actions">
              <Link to={isAuthenticated ? '/upload' : '/register'} className="btn btn--primary btn--lg">
                <ArrowUpTrayIcon aria-hidden="true" /> Upload your first PDF
              </Link>
              {!isAuthenticated && <Button size="lg" onClick={tryAsGuest} loading={guestLoading}>Try it as a guest</Button>}
            </div>
            <p className="small muted inline-flex items-center gap-2" style={{ marginTop: 20 }}>
              <SparklesIcon aria-hidden="true" style={{ width: 18, height: 18, color: 'var(--color-accent-text)' }} /> Works offline, nothing to set up.
            </p>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 30, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.7, ease: EASE_OUT, delay: 0.15 }}>
            <DemoCard />
          </motion.div>
        </section>

        <section id="how" className="l-section" aria-labelledby="how-title">
          <div className="l-wrap">
            <Reveal className="l-head">
              <h2 id="how-title">From PDF to practice in a minute.</h2>
              <p>Quizzr reads your notes, pulls out definitions and key facts, and keeps the page each one came from.</p>
            </Reveal>
            <div className="steps">
              {([
                [ArrowUpTrayIcon, 'Upload a PDF', 'Lecture notes, slides or a textbook chapter, up to 50 MB.'],
                [SparklesIcon, 'Make a deck or a quiz', 'Definitions, fill-the-gap cards, multiple choice, true or false.'],
                [ArrowPathIcon, 'Review what’s due', 'Rate each card. Quizzr decides when you see it next.'],
              ] as const).map(([Icon, title, text], i) => (
                <Reveal key={title} delay={i * 0.08} className="card step">
                  <div className="flex items-center gap-3">
                    <div className="icon-tile"><Icon aria-hidden="true" /></div>
                    <h3 style={{ marginTop: 0 }}>{title}</h3>
                  </div>
                  <p>{text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="l-section" style={{ paddingTop: 0 }} aria-labelledby="schedule-title">
          <div className="l-wrap">
            <Reveal className="l-head">
              <h2 id="schedule-title">Reviews that space themselves out.</h2>
              <p>Know a card, and the gap before you see it again grows. Miss it, and it comes back tomorrow.</p>
            </Reveal>
            <div className="timeline">
              {GOOD_INTERVALS.map((days, i) => (
                <Reveal key={days} delay={i * 0.07} className="card timeline__item" >
                  <div className="timeline__days">{days}</div>
                  <div className="small muted" style={{ marginTop: 6 }}>{days === 1 ? 'day' : 'days'}, review {i + 1}</div>
                </Reveal>
              ))}
            </div>
            <p className="small muted" style={{ marginTop: 14 }}>Days until the next review when you rate a card Good each time.</p>
          </div>
        </section>

        <section className="l-section" style={{ paddingTop: 0 }}>
          <div className="l-wrap">
            <Reveal className="violet-band">
              <div className="grid gap-8 md:grid-cols-2 md:items-center">
                <div>
                  <h2>Bring tonight’s lecture.</h2>
                  <p style={{ marginTop: 12, opacity: 0.85, maxWidth: '36ch' }}>
                    Your decks export to CSV or straight into Anki, so nothing is locked in.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3 md:justify-end">
                  <Link to={isAuthenticated ? '/upload' : '/register'} className="btn btn--light btn--lg">
                    <ArrowUpTrayIcon aria-hidden="true" /> Upload a PDF
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="l-wrap flex flex-wrap items-center justify-between gap-3">
          <Brand />
          <span>Cards are written on your computer from your own notes. No API keys, nothing sent to the cloud.</span>
        </div>
      </footer>
    </div>
  )
}
