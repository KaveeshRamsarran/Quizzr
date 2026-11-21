import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ArrowUpTrayIcon, DocumentTextIcon, MagnifyingGlassIcon, TrashIcon } from '@heroicons/react/24/outline'
import { documentsApi, errorMessage } from '../lib/api'
import { fileSize, relativeDate } from '../lib/format'
import { Button, ConfirmDialog, EmptyState, ErrorState, PageHeader, SkeletonRows, StatusBadge } from '../components/ui'
import { Item, Page, Stagger } from '../components/motion'
import type { Document } from '../types'
import SearchBox from '../components/SearchBox'

const PAGE_SIZE = 20

export default function Documents() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const search = params.get('q') ?? ''
  const page = Number(params.get('page') ?? 1)
  const [draft, setDraft] = useState(search)
  const [toDelete, setToDelete] = useState<Document | null>(null)

  const query = useQuery({
    queryKey: ['documents', 'list', { search, page }],
    queryFn: () => documentsApi.list({ search: search || undefined, page, limit: PAGE_SIZE }),
    refetchInterval: (q) => (q.state.data?.documents.some((d) => d.status === 'pending' || d.status === 'processing') ? 2000 : false),
  })

  const remove = useMutation({
    mutationFn: (id: number) => documentsApi.delete(id),
    onSuccess: () => {
      toast.success('Document deleted')
      setToDelete(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const setQuery = (next: Record<string, string | null>) => {
    const p = new URLSearchParams(params)
    Object.entries(next).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)))
    setParams(p, { replace: true })
  }

  const data = query.data

  return (
    <Page>
      <PageHeader
        title="Documents"
        sub={data ? `${data.total} ${data.total === 1 ? 'document' : 'documents'} uploaded` : 'Your uploaded PDFs'}
        actions={<Link to="/upload" className="btn btn--primary"><ArrowUpTrayIcon aria-hidden="true" /> Upload a PDF</Link>}
      />

      {(data?.total || search) ? (
        <SearchBox id="doc-search" label="Search documents" value={draft} onChange={setDraft} onSubmit={() => setQuery({ q: draft.trim() || null, page: null })} />
      ) : null}

      {query.isLoading ? (
        <SkeletonRows rows={5} />
      ) : query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : !data?.documents.length ? (
        <div className="card">
          {search ? (
            <EmptyState icon={<MagnifyingGlassIcon />} title={`Nothing matches “${search}”`} action={<Button onClick={() => { setDraft(''); setQuery({ q: null }) }}>Clear search</Button>} />
          ) : (
            <EmptyState icon={<DocumentTextIcon />} title="No documents yet" action={<Link to="/upload" className="btn btn--primary"><ArrowUpTrayIcon aria-hidden="true" /> Upload a PDF</Link>}>
              Upload a lecture PDF to make flashcards and quizzes from it.
            </EmptyState>
          )}
        </div>
      ) : (
        <>
          <Stagger className="card list" key={`${search}-${page}`}>
            {data.documents.map((doc) => (
              <Item key={doc.id} className="list-row list-row--link" onClick={() => navigate(`/documents/${doc.id}`)}>
                <div className="icon-tile"><DocumentTextIcon aria-hidden="true" /></div>
                <div className="min-w-0 flex-1">
                  <Link to={`/documents/${doc.id}`} className="row-title truncate block" onClick={(e) => e.stopPropagation()}>{doc.title || doc.original_filename}</Link>
                  <div className="row-meta truncate">
                    {doc.page_count ? `${doc.page_count} ${doc.page_count === 1 ? 'page' : 'pages'}, ` : ''}{fileSize(doc.file_size)}, uploaded {relativeDate(doc.created_at)}
                  </div>
                </div>
                <StatusBadge status={doc.status} />
                <Button
                  size="sm"
                  variant="ghost"
                  icon={<TrashIcon aria-hidden="true" />}
                  aria-label={`Delete ${doc.title || doc.original_filename}`}
                  onClick={(e) => { e.stopPropagation(); setToDelete(doc) }}
                />
              </Item>
            ))}
          </Stagger>
          {data.pages > 1 && (
            <nav className="flex items-center justify-center gap-3" style={{ marginTop: 24 }} aria-label="Pages">
              <Button size="sm" disabled={page <= 1} onClick={() => setQuery({ page: String(page - 1) })}>Previous</Button>
              <span className="muted small">Page {page} of {data.pages}</span>
              <Button size="sm" disabled={page >= data.pages} onClick={() => setQuery({ page: String(page + 1) })}>Next</Button>
            </nav>
          )}
        </>
      )}

      <ConfirmDialog
        open={!!toDelete}
        title="Delete this document?"
        body={<>“{toDelete?.title || toDelete?.original_filename}” will be deleted. Flashcards and quizzes made from it are kept.</>}
        confirmLabel="Delete document"
        loading={remove.isPending}
        onConfirm={() => toDelete && remove.mutate(toDelete.id)}
        onClose={() => setToDelete(null)}
      />
    </Page>
  )
}
