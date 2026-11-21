import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  ArrowLeftIcon, ArrowPathIcon, ExclamationCircleIcon, PencilIcon, QuestionMarkCircleIcon, RectangleStackIcon, TrashIcon,
} from '@heroicons/react/24/outline'
import { decksApi, documentsApi, errorMessage, generationApi, quizzesApi } from '../lib/api'
import { fileSize, shortDate } from '../lib/format'
import { Button, ConfirmDialog, Dialog, ErrorState, Field, PageLoading, SectionTitle, StatusBadge, Tabs } from '../components/ui'
import { EASE_OUT, Item, Page, ProgressBar, Stagger } from '../components/motion'
import GenerateDialog from '../components/GenerateDialog'

type Tab = 'sections' | 'text' | 'pdf'

export default function DocumentView() {
  const { id } = useParams()
  const documentId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as Tab) || 'sections'
  const make = params.get('make') as 'deck' | 'quiz' | null
  const lastKind = useRef<'deck' | 'quiz'>('deck')
  if (make) lastKind.current = make
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfError, setPdfError] = useState<string | null>(null)

  const doc = useQuery({
    queryKey: ['documents', documentId],
    queryFn: () => documentsApi.get(documentId),
    enabled: Number.isFinite(documentId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'processing' ? 1500 : false
    },
  })
  const decks = useQuery({ queryKey: ['decks', 'list', { document_id: documentId }], queryFn: () => decksApi.list({ document_id: documentId, limit: 100 }) })
  const quizzes = useQuery({ queryKey: ['quizzes', 'list', { document_id: documentId }], queryFn: () => quizzesApi.list({ document_id: documentId, limit: 100 }) })
  const jobs = useQuery({
    queryKey: ['jobs', { document_id: documentId }],
    queryFn: () => generationApi.listJobs({ document_id: documentId, limit: 10 }),
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === 'pending' || j.status === 'processing') ? 1000 : false),
  })

  const running = jobs.data?.filter((j) => j.status === 'pending' || j.status === 'processing') ?? []
  const prevRunning = useRef(0)
  useEffect(() => {
    if (prevRunning.current > running.length) {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      queryClient.invalidateQueries({ queryKey: ['quizzes'] })
    }
    prevRunning.current = running.length
  }, [running.length, queryClient])

  const setParam = (key: string, value: string | null) => {
    const p = new URLSearchParams(params)
    if (value) p.set(key, value)
    else p.delete(key)
    setParams(p, { replace: true })
  }

  useEffect(() => {
    if (tab !== 'pdf' || pdfUrl || !doc.data) return
    let url: string | null = null
    documentsApi.fileBlob(documentId)
      .then((blob) => { url = URL.createObjectURL(blob); setPdfUrl(url) })
      .catch((err) => setPdfError(errorMessage(err, 'The original PDF couldn’t be loaded.')))
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [tab, pdfUrl, doc.data, documentId])

  const remove = useMutation({
    mutationFn: () => documentsApi.delete(documentId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document deleted'); navigate('/documents') },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const reprocess = useMutation({
    mutationFn: () => documentsApi.reprocess(documentId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['documents', documentId] }); toast.success('Reading the document again') },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const rename = useMutation({
    mutationFn: () => documentsApi.update(documentId, { title: newTitle.trim() }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['documents'] }); setRenaming(false) },
    onError: (err) => toast.error(errorMessage(err)),
  })

  if (doc.isLoading) return <PageLoading />
  if (doc.isError || !doc.data) {
    return (
      <div className="page">
        <Link to="/documents" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Documents</Link>
        <ErrorState message={errorMessage(doc.error, 'This document couldn’t be found.')} onRetry={() => doc.refetch()} />
      </div>
    )
  }

  const d = doc.data
  const title = d.title || d.original_filename
  const ready = d.status === 'processed'
  const busy = d.status === 'pending' || d.status === 'processing'

  return (
    <Page>
      <Link to="/documents" className="back-link"><ArrowLeftIcon aria-hidden="true" /> Documents</Link>
      <header className="page-header">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="min-w-0">{title}</h1>
            <StatusBadge status={d.status} />
          </div>
          <p className="page-header__sub">{d.page_count} {d.page_count === 1 ? 'page' : 'pages'}, {fileSize(d.file_size)}, uploaded {shortDate(d.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" icon={<PencilIcon />} onClick={() => { setNewTitle(title); setRenaming(true) }}>Rename</Button>
          <Button variant="ghost" size="sm" icon={<TrashIcon />} onClick={() => setConfirmDelete(true)}>Delete</Button>
        </div>
      </header>

      <AnimatePresence>
        {busy && (
          <motion.div className="card card--pad" style={{ marginBottom: 24 }} aria-live="polite" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <p className="row-title">Reading your PDF…</p>
            <div style={{ marginTop: 12 }}><ProgressBar value={d.status === 'processing' ? 70 : 30} label="Processing progress" /></div>
          </motion.div>
        )}
      </AnimatePresence>
      {d.status === 'error' && (
        <div className="notice notice--error items-center" role="alert" style={{ marginBottom: 24 }}>
          <ExclamationCircleIcon aria-hidden="true" />
          <span className="flex-1">{d.error_message || 'This PDF couldn’t be read.'}</span>
          <Button size="sm" onClick={() => reprocess.mutate()} loading={reprocess.isPending} icon={<ArrowPathIcon />}>Try again</Button>
        </div>
      )}

      {ready && (
        <Stagger className="grid gap-3 sm:grid-cols-2" >
          {([
            ['deck', RectangleStackIcon, 'Make flashcards', 'Definitions and fill-the-gap cards to review over time.'],
            ['quiz', QuestionMarkCircleIcon, 'Make a quiz', 'Multiple choice, true or false and short answers.'],
          ] as const).map(([kind, Icon, label, text]) => (
            <Item key={kind}>
              <button type="button" className={`card card-link text-left w-full ${kind === 'deck' ? 'card--accent' : ''}`} style={{ padding: 22, border: 0, cursor: 'pointer', height: '100%' }} onClick={() => setParam('make', kind)}>
                <div className="flex items-center gap-4">
                  <div className="icon-tile" style={kind === 'deck' ? { background: 'color-mix(in oklab, var(--color-accent-ink) 20%, transparent)', color: 'var(--color-accent-ink)' } : undefined}><Icon aria-hidden="true" /></div>
                  <div>
                    <h3 style={kind === 'deck' ? { color: 'var(--color-accent-ink)' } : undefined}>{label}</h3>
                    <p className="small" style={{ opacity: kind === 'deck' ? 0.85 : 1, color: kind === 'deck' ? undefined : 'var(--color-muted)' }}>{text}</p>
                  </div>
                </div>
              </button>
            </Item>
          ))}
        </Stagger>
      )}

      <AnimatePresence>
        {running.length > 0 && (
          <motion.div className="card card--pad section" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {running.map((j) => (
              <div key={j.job_id}>
                <p className="small"><strong className="row-title">{j.job_type === 'quiz_generation' ? 'Quiz' : 'Flashcards'}</strong> <span className="muted">{j.step || 'Queued'}…</span></p>
                <div style={{ marginTop: 8 }}><ProgressBar value={j.progress ?? 5} label="Generation progress" /></div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-x-8 lg:grid-cols-[minmax(0,1fr)_320px] section">
        <section aria-label="Document contents" className="min-w-0">
          <Tabs<Tab>
            label="Document views"
            value={tab}
            onChange={(v) => setParam('tab', v === 'sections' ? null : v)}
            options={[
              { value: 'sections', label: <>Sections <span className="badge" style={{ height: 20 }}>{d.chunks.length}</span></> },
              { value: 'text', label: 'Text' },
              { value: 'pdf', label: 'Original PDF' },
            ]}
          />
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2, ease: EASE_OUT }}>
              {tab === 'sections' && (
                d.chunks.length === 0 ? (
                  <p className="muted">{busy ? 'Sections appear here once the text has been read.' : 'No readable text was found.'}</p>
                ) : (
                  <Stagger className="grid gap-3">
                    {d.chunks.map((c) => (
                      <Item key={c.id} className="card" >
                        <div style={{ padding: 18 }}>
                          <div className="flex items-start justify-between gap-3">
                            <h3 className="min-w-0">{c.heading_context || `Section ${c.chunk_index + 1}`}</h3>
                            <span className="badge">{c.start_page === c.end_page ? `Page ${c.start_page}` : `Pages ${c.start_page} to ${c.end_page}`}</span>
                          </div>
                          <p className="small muted" style={{ marginTop: 6 }}>{c.content.replace(/^# .*$/gm, '').replace(/\s+/g, ' ').trim().slice(0, 180)}…</p>
                          {!!c.key_terms?.length && (
                            <div className="chips" style={{ marginTop: 10 }}>
                              {c.key_terms.slice(0, 5).map((t) => <span key={t} className="badge badge--accent">{t}</span>)}
                            </div>
                          )}
                        </div>
                      </Item>
                    ))}
                  </Stagger>
                )
              )}

              {tab === 'text' && (
                <div className="card card--pad">
                  {d.pages.length ? d.pages.map((p) => (
                    <article key={p.id} className="reader-page" aria-label={`Page ${p.page_number}`}>
                      <span className="badge" style={{ marginBottom: 10 }}>Page {p.page_number}{p.used_ocr ? ', read by OCR' : ''}</span>
                      <p className="reader-page__text">{p.text_content?.trim() || 'No text on this page.'}</p>
                    </article>
                  )) : <p className="muted">No text yet.</p>}
                </div>
              )}

              {tab === 'pdf' && (
                pdfError ? <ErrorState message={pdfError} onRetry={() => { setPdfError(null); setPdfUrl(null) }} />
                  : pdfUrl ? <iframe title={`${title} (PDF)`} src={pdfUrl} className="pdf-frame" />
                  : <div className="skeleton" style={{ height: 480, borderRadius: 18 }} aria-label="Loading PDF" />
              )}
            </motion.div>
          </AnimatePresence>
        </section>

        <aside className="min-w-0">
          <SectionTitle title="Made from this document" />
          {(decks.data?.decks.length || quizzes.data?.quizzes.length) ? (
            <Stagger className="card list">
              {decks.data?.decks.map((deck) => (
                <Item key={`d${deck.id}`} className="list-row list-row--link" onClick={() => navigate(`/decks/${deck.id}`)}>
                  <RectangleStackIcon aria-hidden="true" style={{ width: 20, height: 20, flex: 'none', color: 'var(--color-accent-text)' }} />
                  <Link to={`/decks/${deck.id}`} className="row-title truncate flex-1 small" onClick={(e) => e.stopPropagation()}>{deck.name}</Link>
                  <span className="tiny muted">{deck.card_count} cards</span>
                </Item>
              ))}
              {quizzes.data?.quizzes.map((q) => (
                <Item key={`q${q.id}`} className="list-row list-row--link" onClick={() => navigate(`/quizzes/${q.id}`)}>
                  <QuestionMarkCircleIcon aria-hidden="true" style={{ width: 20, height: 20, flex: 'none', color: 'var(--color-accent-text)' }} />
                  <Link to={`/quizzes/${q.id}`} className="row-title truncate flex-1 small" onClick={(e) => e.stopPropagation()}>{q.name}</Link>
                  <span className="tiny muted">{q.question_count} questions</span>
                </Item>
              ))}
            </Stagger>
          ) : (
            <div className="card card--soft" style={{ padding: 18 }}>
              <p className="small muted">Nothing yet. {ready ? 'Make flashcards or a quiz above.' : ''}</p>
            </div>
          )}
          {jobs.data?.some((j) => j.status === 'failed') && (
            <div className="section">
              <SectionTitle title="Didn’t work" />
              {jobs.data.filter((j) => j.status === 'failed').slice(0, 3).map((j) => (
                <div key={j.job_id} className="notice notice--error" style={{ marginBottom: 8 }}>
                  <ExclamationCircleIcon aria-hidden="true" /><span>{j.message}</span>
                </div>
              ))}
            </div>
          )}
          {ready && (
            <div className="section">
              <Button size="sm" variant="ghost" icon={<ArrowPathIcon />} onClick={() => reprocess.mutate()} loading={reprocess.isPending}>Read the PDF again</Button>
            </div>
          )}
        </aside>
      </div>

      {ready && (
        <GenerateDialog kind={make ?? lastKind.current} open={!!make} onClose={() => setParam('make', null)} documentId={documentId} documentTitle={title} />
      )}

      <Dialog open={renaming} onClose={() => setRenaming(false)} title="Rename document">
        <form onSubmit={(e) => { e.preventDefault(); if (newTitle.trim()) rename.mutate() }}>
          <Field label="Title" htmlFor="doc-title">
            <input id="doc-title" className="input" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} maxLength={255} data-autofocus />
          </Field>
          <div className="dialog__actions">
            <Button onClick={() => setRenaming(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={rename.isPending} disabled={!newTitle.trim()}>Save</Button>
          </div>
        </form>
      </Dialog>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this document?"
        body="The PDF and its text will be deleted. Flashcards and quizzes made from it are kept."
        confirmLabel="Delete document"
        loading={remove.isPending}
        onConfirm={() => remove.mutate()}
        onClose={() => setConfirmDelete(false)}
      />
    </Page>
  )
}
