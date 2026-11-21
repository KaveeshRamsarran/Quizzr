import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { CheckCircleIcon, MagnifyingGlassIcon, PlusIcon, RectangleStackIcon } from '@heroicons/react/24/outline'
import { decksApi, errorMessage } from '../lib/api'
import { relativeDate } from '../lib/format'
import { Button, Dialog, EmptyState, ErrorState, Field, PageHeader, SkeletonRows } from '../components/ui'
import { Item, Page, ProgressBar, Stagger } from '../components/motion'
import SearchBox from '../components/SearchBox'

export default function Decks() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const search = params.get('q') ?? ''
  const [draft, setDraft] = useState(search)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')

  const query = useQuery({
    queryKey: ['decks', 'list', { search }],
    queryFn: () => decksApi.list({ search: search || undefined, limit: 100 }),
  })

  const create = useMutation({
    mutationFn: () => decksApi.create({ name: name.trim() }),
    onSuccess: (deck) => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      navigate(`/decks/${deck.id}`)
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const decks = query.data?.decks ?? []
  const totalReady = decks.reduce((n, d) => n + d.due_count + d.new_count, 0)

  return (
    <Page>
      <PageHeader
        title="Flashcards"
        sub={query.data ? `${decks.length} ${decks.length === 1 ? 'deck' : 'decks'}${totalReady ? `, ${totalReady} cards ready to study` : ''}` : 'Your decks'}
        actions={<Button onClick={() => { setName(''); setCreating(true) }} icon={<PlusIcon />}>New deck</Button>}
      />

      {(decks.length > 0 || search) && (
        <SearchBox id="deck-search" label="Search decks" value={draft} onChange={setDraft} onSubmit={() => setParams(draft.trim() ? { q: draft.trim() } : {}, { replace: true })} />
      )}

      {query.isLoading ? (
        <SkeletonRows rows={4} height={120} />
      ) : query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : !decks.length ? (
        <div className="card">
          {search ? (
            <EmptyState icon={<MagnifyingGlassIcon />} title={`No decks match “${search}”`} action={<Button onClick={() => { setDraft(''); setParams({}) }}>Clear search</Button>} />
          ) : (
            <EmptyState icon={<RectangleStackIcon />} title="No flashcards yet" action={<Link to="/documents" className="btn btn--primary">Choose a document</Link>}>
              Open a document and choose Make flashcards, or start an empty deck and write your own.
            </EmptyState>
          )}
        </div>
      ) : (
        <Stagger className="grid-cards" key={search}>
          {decks.map((deck) => {
            const ready = deck.due_count + deck.new_count
            const mastery = deck.card_count ? (deck.mastered_count / deck.card_count) * 100 : 0
            return (
              <Item key={deck.id}>
                <div className="card card-link" style={{ padding: 20, height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <Link to={`/decks/${deck.id}`} className="block flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div className="icon-tile"><RectangleStackIcon aria-hidden="true" /></div>
                      {ready > 0 ? <span className="badge badge--accent">{ready} to study</span> : deck.card_count ? <span className="badge badge--success"><CheckCircleIcon /> Caught up</span> : <span className="badge">Empty</span>}
                    </div>
                    <h3 style={{ marginTop: 14 }}>{deck.name}</h3>
                    <p className="row-meta">{deck.card_count} cards, studied {relativeDate(deck.last_studied)}</p>
                    <div className="flex items-center gap-3" style={{ marginTop: 14 }}>
                      <div className="flex-1"><ProgressBar value={mastery} label={`${deck.name} mastery`} className="progress--thin" /></div>
                      <span className="tiny muted figure-font">{Math.round(mastery)}%</span>
                    </div>
                  </Link>
                  <div className="flex gap-2" style={{ marginTop: 16 }}>
                    {ready > 0 ? (
                      <Link to={`/decks/${deck.id}/study`} className="btn btn--primary btn--sm flex-1">Study now</Link>
                    ) : deck.card_count > 0 ? (
                      <Link to={`/decks/${deck.id}/study?mode=all`} className="btn btn--sm flex-1">Practise all</Link>
                    ) : (
                      <Link to={`/decks/${deck.id}`} className="btn btn--sm flex-1">Add cards</Link>
                    )}
                  </div>
                </div>
              </Item>
            )
          })}
        </Stagger>
      )}

      <Dialog open={creating} onClose={() => setCreating(false)} title="New deck">
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate() }}>
          <Field label="Deck name" htmlFor="deck-name" help="You can add cards yourself once it's created.">
            <input id="deck-name" className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={255} data-autofocus />
          </Field>
          <div className="dialog__actions">
            <Button onClick={() => setCreating(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={create.isPending} disabled={!name.trim()}>Create deck</Button>
          </div>
        </form>
      </Dialog>
    </Page>
  )
}
