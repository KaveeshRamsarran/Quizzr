import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MagnifyingGlassIcon, PlayIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline'
import { errorMessage, quizzesApi } from '../lib/api'
import { relativeDate } from '../lib/format'
import { Button, EmptyState, ErrorState, PageHeader, SkeletonRows } from '../components/ui'
import { Item, Page, Stagger } from '../components/motion'
import SearchBox from '../components/SearchBox'

export default function Quizzes() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const search = params.get('q') ?? ''
  const [draft, setDraft] = useState(search)

  const query = useQuery({
    queryKey: ['quizzes', 'list', { search }],
    queryFn: () => quizzesApi.list({ search: search || undefined, limit: 100 }),
  })
  const quizzes = query.data?.quizzes ?? []

  return (
    <Page>
      <PageHeader title="Quizzes" sub={query.data ? `${quizzes.length} ${quizzes.length === 1 ? 'quiz' : 'quizzes'}` : 'Test yourself'} />

      {(quizzes.length > 0 || search) && (
        <SearchBox id="quiz-search" label="Search quizzes" value={draft} onChange={setDraft} onSubmit={() => setParams(draft.trim() ? { q: draft.trim() } : {}, { replace: true })} />
      )}

      {query.isLoading ? (
        <SkeletonRows rows={4} />
      ) : query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : !quizzes.length ? (
        <div className="card">
          {search ? (
            <EmptyState icon={<MagnifyingGlassIcon />} title={`No quizzes match “${search}”`} action={<Button onClick={() => { setDraft(''); setParams({}) }}>Clear search</Button>} />
          ) : (
            <EmptyState icon={<QuestionMarkCircleIcon />} title="No quizzes yet" action={<Link to="/documents" className="btn btn--primary">Choose a document</Link>}>
              Open a document and choose Make a quiz.
            </EmptyState>
          )}
        </div>
      ) : (
        <Stagger className="card list" key={search}>
          {quizzes.map((quiz) => (
            <Item key={quiz.id} className="list-row list-row--link" onClick={() => navigate(`/quizzes/${quiz.id}`)}>
              <div className="icon-tile"><QuestionMarkCircleIcon aria-hidden="true" /></div>
              <div className="min-w-0 flex-1">
                <Link to={`/quizzes/${quiz.id}`} className="row-title truncate block" onClick={(e) => e.stopPropagation()}>{quiz.name}</Link>
                <div className="row-meta truncate">
                  {quiz.question_count} questions{quiz.time_limit_minutes ? `, ${quiz.time_limit_minutes} min` : ''}, created {relativeDate(quiz.created_at)}
                </div>
              </div>
              {quiz.average_score != null && <span className="badge figure-font hidden sm:inline-flex">Avg {Math.round(quiz.average_score)}%</span>}
              <Link to={`/quizzes/${quiz.id}/take`} className="btn btn--sm" onClick={(e) => e.stopPropagation()}>
                <PlayIcon aria-hidden="true" /> Start
              </Link>
            </Item>
          ))}
        </Stagger>
      )}
    </Page>
  )
}
