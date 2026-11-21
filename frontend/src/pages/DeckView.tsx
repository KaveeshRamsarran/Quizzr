import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  ArrowDownTrayIcon, ArrowLeftIcon, ExclamationTriangleIcon, PencilIcon, PencilSquareIcon, PlayIcon, PlusIcon, TrashIcon,
} from '@heroicons/react/24/outline'
import { decksApi, errorMessage } from '../lib/api'
import { CARD_TYPE_LABEL, pages, relativeDate } from '../lib/format'
import { Button, ConfirmDialog, Dialog, EmptyState, ErrorState, Field, PageLoading, Segmented } from '../components/ui'
import { CountUp, EASE_OUT, Item, Page, ProgressBar, Stagger } from '../components/motion'
import SearchBox from '../components/SearchBox'
import type { Card } from '../types'

type Filter = 'all' | 'review' | 'mastered'

export default function DeckView() {
  const { id } = useParams()
  const deckId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState<Card | 'new' | null>(null)
  const [front, setFront] = useState('')
  const [back, setBack] = useState('')
  const [deleteCard, setDeleteCard] = useState<Card | null>(null)
  const [deleteDeck, setDeleteDeck] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState('')
  const [exporting, setExporting] = useState<'csv' | 'anki' | null>(null)

  const deck = useQuery({ queryKey: ['decks', deckId], queryFn: () => decksApi.get(deckId), enabled: Number.isFinite(deckId) })
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['decks'] })
    queryClient.invalidateQueries({ queryKey: ['analytics'] })
  }

  const saveCard = useMutation({
    mutationFn: () =>
      editing === 'new'
        ? decksApi.addCard(deckId, { front: front.trim(), back: back.trim(), card_type: 'basic' })
        : decksApi.updateCard(deckId, (editing as Card).id, { front: front.trim(), back: back.trim(), needs_review: false }),
    onSuccess: () => { refresh(); setEditing(null); toast.success(editing === 'new' ? 'Card added' : 'Card saved') },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const removeCard = useMutation({
    mutationFn: (cardId: number) => decksApi.deleteCard(deckId, cardId),
    onSuccess: () => { refresh(); setDeleteCard(null) },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const removeDeck = useMutation({
    mutationFn: () => decksApi.delete(deckId),
    onSuccess: () => { refresh(); toast.success('Deck deleted'); navigate('/decks') },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const renameDeck = useMutation({
    mutationFn: () => decksApi.update(deckId, { name: name.trim() }),
    onSuccess: () => { refresh(); setRenaming(false) },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const cards = useMemo(() => {
    const list = deck.data?.cards ?? []
    const q = search.trim().toLowerCase()
    return list.filter((c) => {
      if (filter === 'review' && !c.needs_review) return false
      if (filter === 'mastered' && !c.is_mastered) return false
      return !q || c.front.toLowerCase().includes(q) || c.back.toLowerCase().includes(q)
    })
  }, [deck.data, filter, search])

  const runExport = async (kind: 'csv' | 'anki') => {
    setExporting(kind)
    try {
      await (kind === 'csv' ? decksApi.exportCsv(deckId) : decksApi.exportAnki(deckId))
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setExporting(null)
    }
  }

  const openEditor = (card: Card | 'new') => {
    setEditing(card)
    setFront(card === 'new' ? '' : card.front)
    setBack(card === 'new' ? '' : card.back)
  }

  if (deck.isLoading) return <PageLoading />
  if (deck.isError || !deck.data) {
    return (
      <div className="page">
        <Link to="/decks" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Flashcards</Link>
        <ErrorState message={errorMessage(deck.error, 'This deck couldn’t be found.')} onRetry={() => deck.refetch()} />
      </div>
    )
  }

  const d = deck.data
  const ready = d.due_count + d.new_count
  const flagged = d.cards.filter((c) => c.needs_review).length
  const mastery = d.card_count ? (d.mastered_count / d.card_count) * 100 : 0

  return (
    <Page>
      <Link to="/decks" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Flashcards</Link>

      <motion.section className="card" style={{ padding: 'var(--space-lg)', borderRadius: 24 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_OUT }}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 style={{ fontSize: 'clamp(1.5rem, 1.1rem + 1.2vw, 2rem)' }}>{d.name}</h1>
            <p className="page-header__sub">
              {d.card_count} cards, studied {relativeDate(d.last_studied)}
              {d.source_document_id && <>. <Link to={`/documents/${d.source_document_id}`} className="link">Open the source document</Link></>}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {ready > 0 && <Link to={`/decks/${d.id}/study`} className="btn btn--primary btn--lg"><PlayIcon aria-hidden="true" /> Study {ready} {ready === 1 ? 'card' : 'cards'}</Link>}
            {d.card_count > 0 && <Link to={`/decks/${d.id}/study?mode=all`} className={`btn ${ready ? '' : 'btn--primary'} btn--lg`}>Practise all</Link>}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-4" style={{ marginTop: 24 }}>
          {[
            ['Due now', d.due_count], ['Not studied yet', d.new_count], ['Mastered', d.mastered_count], ['Need checking', flagged],
          ].map(([label, value]) => (
            <div key={label as string}>
              <div className="stat__value" style={{ fontSize: '2rem', marginTop: 0 }}><CountUp value={value as number} /></div>
              <div className="small muted">{label}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 20 }}>
          <div className="flex justify-between small muted" style={{ marginBottom: 6 }}><span>Mastery</span><span className="figure-font">{Math.round(mastery)}%</span></div>
          <ProgressBar value={mastery} label="Deck mastery" />
        </div>
      </motion.section>

      <div className="flex flex-wrap items-center justify-between gap-3 section" style={{ marginBottom: 12 }}>
        <Segmented<Filter>
          label="Show cards"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: `All (${d.cards.length})` },
            { value: 'review', label: `To check (${flagged})` },
            { value: 'mastered', label: `Mastered (${d.mastered_count})` },
          ]}
        />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => openEditor('new')} icon={<PlusIcon />}>Add card</Button>
          <Button size="sm" variant="ghost" onClick={() => runExport('csv')} loading={exporting === 'csv'} disabled={!d.card_count} icon={<ArrowDownTrayIcon />}>CSV</Button>
          <Button size="sm" variant="ghost" onClick={() => runExport('anki')} loading={exporting === 'anki'} disabled={!d.card_count} icon={<ArrowDownTrayIcon />}>Anki</Button>
        </div>
      </div>

      {d.cards.length > 6 && <SearchBox id="card-search" label="Search cards" value={draft} onChange={(v) => { setDraft(v); setSearch(v) }} onSubmit={() => setSearch(draft)} />}

      {d.cards.length === 0 ? (
        <div className="card">
          <EmptyState icon={<PlusIcon />} title="This deck is empty" action={<Button variant="primary" onClick={() => openEditor('new')} icon={<PlusIcon />}>Add the first card</Button>}>
            Write your own cards, or make a deck from a document.
          </EmptyState>
        </div>
      ) : cards.length === 0 ? (
        <p className="muted" style={{ padding: '24px 0' }}>No cards match.</p>
      ) : (
        <Stagger className="grid gap-3" key={`${filter}-${search}`}>
          <AnimatePresence initial={false}>
            {cards.map((card) => (
              <Item key={card.id} className="card">
                <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" style={{ padding: 18 }}>
                  <div className="min-w-0">
                    <div className="tiny muted" style={{ marginBottom: 4 }}>Front</div>
                    <p className="row-title">{card.front}</p>
                  </div>
                  <div className="min-w-0">
                    <div className="tiny muted" style={{ marginBottom: 4 }}>Back</div>
                    <p style={{ whiteSpace: 'pre-line' }}>{card.back}</p>
                  </div>
                  <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2">
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" icon={<PencilSquareIcon aria-hidden="true" />} aria-label="Edit card" onClick={() => openEditor(card)} />
                      <Button size="sm" variant="ghost" icon={<TrashIcon aria-hidden="true" />} aria-label="Delete card" onClick={() => setDeleteCard(card)} />
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2" style={{ padding: '0 18px 14px' }}>
                  <span className="badge">{CARD_TYPE_LABEL[card.card_type] ?? card.card_type}</span>
                  {card.source_pages?.length ? <span className="badge" title={card.source_snippets?.[0] ?? undefined}>{pages(card.source_pages)}</span> : <span className="badge">Written by you</span>}
                  {card.is_mastered && <span className="badge badge--success">Mastered</span>}
                  {card.needs_review && <span className="badge badge--error"><ExclamationTriangleIcon /> Check against your notes</span>}
                </div>
              </Item>
            ))}
          </AnimatePresence>
        </Stagger>
      )}

      <div className="section flex flex-wrap gap-2">
        <Button size="sm" variant="ghost" icon={<PencilIcon />} onClick={() => { setName(d.name); setRenaming(true) }}>Rename deck</Button>
        <Button size="sm" variant="ghost" icon={<TrashIcon />} onClick={() => setDeleteDeck(true)}>Delete deck</Button>
      </div>

      <Dialog open={editing !== null} onClose={() => setEditing(null)} title={editing === 'new' ? 'Add a card' : 'Edit card'}>
        <form onSubmit={(e) => { e.preventDefault(); if (front.trim() && back.trim()) saveCard.mutate() }} className="grid gap-4">
          <Field label="Front" htmlFor="card-front" help="The question or prompt.">
            <textarea id="card-front" className="textarea" value={front} onChange={(e) => setFront(e.target.value)} data-autofocus />
          </Field>
          <Field label="Back" htmlFor="card-back" help="The answer.">
            <textarea id="card-back" className="textarea" value={back} onChange={(e) => setBack(e.target.value)} />
          </Field>
          {editing && editing !== 'new' && editing.source_snippets?.[0] && (
            <div className="notice"><span><strong className="row-title">From your notes, {pages(editing.source_pages).toLowerCase()}:</strong> “{editing.source_snippets[0]}”</span></div>
          )}
          <div className="dialog__actions">
            <Button onClick={() => setEditing(null)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={saveCard.isPending} disabled={!front.trim() || !back.trim()}>Save card</Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={renaming} onClose={() => setRenaming(false)} title="Rename deck">
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) renameDeck.mutate() }}>
          <Field label="Deck name" htmlFor="deck-rename">
            <input id="deck-rename" className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={255} data-autofocus />
          </Field>
          <div className="dialog__actions">
            <Button onClick={() => setRenaming(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={renameDeck.isPending} disabled={!name.trim()}>Save</Button>
          </div>
        </form>
      </Dialog>

      <ConfirmDialog open={!!deleteCard} title="Delete this card?" body={deleteCard?.front} confirmLabel="Delete card"
        loading={removeCard.isPending} onConfirm={() => deleteCard && removeCard.mutate(deleteCard.id)} onClose={() => setDeleteCard(null)} />
      <ConfirmDialog open={deleteDeck} title="Delete this deck?" body={`All ${d.card_count} cards and their review history will be deleted.`} confirmLabel="Delete deck"
        loading={removeDeck.isPending} onConfirm={() => removeDeck.mutate()} onClose={() => setDeleteDeck(false)} />
    </Page>
  )
}
