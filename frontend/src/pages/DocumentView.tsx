import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  DocumentIcon,
  ArrowLeftIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { documentsApi, generationApi } from '../lib/api'
import clsx from 'clsx'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useEffect, useMemo, useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import type { GenerationJob } from '../types'

export default function DocumentView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const documentId = parseInt(id || '0')

  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [showPdf, setShowPdf] = useState(false)
  const [generationType, setGenerationType] = useState<'deck' | 'quiz' | null>(null)
  const [generationJob, setGenerationJob] = useState<GenerationJob | null>(null)

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsApi.get(documentId),
    enabled: !!documentId,
  })

  const { data: jobStatus } = useQuery({
    queryKey: ['generation-job', generationJob?.job_id],
    queryFn: () => generationApi.getJobStatus(generationJob!.job_id),
    enabled: !!generationJob,
    refetchInterval: (query) => {
      const status = (query.state.data as GenerationJob | undefined)?.status ?? generationJob?.status
      return status && ['completed', 'failed'].includes(status) ? false : 2000
    },
  })

  const currentJob = jobStatus || generationJob

  useEffect(() => {
    if (currentJob?.status !== 'completed' || !currentJob.result_id) return
    const resultPath = generationType === 'deck'
      ? `/decks/${currentJob.result_id}`
      : `/quizzes/${currentJob.result_id}`
    const t = window.setTimeout(() => navigate(resultPath), 800)
    return () => window.clearTimeout(t)
  }, [currentJob?.status, currentJob?.result_id, generationType, navigate])

  const deleteMutation = useMutation({
    mutationFn: () => documentsApi.delete(documentId),
    onSuccess: async () => {
      toast.success('Document deleted')
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      navigate('/documents')
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Failed to delete document')
    },
  })

  const generateDeckMutation = useMutation({
    mutationFn: () => generationApi.generateDeck({ document_id: documentId, card_count: 10 }),
    onSuccess: (job) => {
      setGenerationType('deck')
      setGenerationJob(job)
      toast.success('Deck generation started')
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Deck generation failed')
    },
  })

  const generateQuizMutation = useMutation({
    mutationFn: () => generationApi.generateQuiz({ document_id: documentId, question_count: 10 }),
    onSuccess: (job) => {
      setGenerationType('quiz')
      setGenerationJob(job)
      toast.success('Quiz generation started')
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Quiz generation failed')
    },
  })

  const canGenerate = useMemo(() => {
    const status = (document as any)?.status
    return status === 'processed' || status === 'completed'
  }, [document])

  const loadPdf = async () => {
    if (!accessToken) {
      toast.error('Not authenticated')
      return
    }
    try {
      const res = await fetch(`/api/documents/${documentId}/file`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      if (!res.ok) {
        let detail = ''
        try {
          const contentType = res.headers.get('content-type') || ''
          if (contentType.includes('application/json')) {
            const data = (await res.json()) as { detail?: string }
            detail = data?.detail ? `: ${data.detail}` : ''
          } else {
            const text = await res.text()
            detail = text ? `: ${text}` : ''
          }
        } catch {
          // ignore parsing errors
        }
        throw new Error(`Failed to load PDF (${res.status})${detail}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setPdfUrl(url)
      setShowPdf(true)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load PDF')
    }
  }

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl)
    }
  }, [pdfUrl])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <DocumentIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900">Document not found</h2>
        <Link to="/dashboard" className="text-primary-600 mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    )
  }

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    processed: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>
        
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center">
            <DocumentIcon className="w-12 h-12 text-primary-500" />
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-gray-900">
                {document.title || document.filename}
              </h1>
              <p className="text-gray-500">
                {document.original_filename}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const ok = window.confirm('Delete this document? This cannot be undone.')
                if (!ok) return
                deleteMutation.mutate()
              }}
              disabled={deleteMutation.isPending}
              className="btn-secondary"
            >
              <TrashIcon className="w-5 h-5 mr-2 text-red-600" />
              Delete
            </button>
            <span
              className={clsx(
                'px-3 py-1 rounded-full text-sm font-medium',
                statusColors[document.status as keyof typeof statusColors]
              )}
            >
              {document.status}
            </span>
          </div>
        </div>
      </div>

      {/* Document info */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Document Details</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-gray-500">Pages</dt>
            <dd className="text-lg font-medium text-gray-900">
              {document.page_count || 'Unknown'}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">File Size</dt>
            <dd className="text-lg font-medium text-gray-900">
              {(document.file_size / 1024).toFixed(1)} KB
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Uploaded</dt>
            <dd className="text-lg font-medium text-gray-900">
              {new Date(document.created_at).toLocaleDateString()}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Type</dt>
            <dd className="text-lg font-medium text-gray-900">
              {document.mime_type}
            </dd>
          </div>
        </dl>

        {document.description && (
          <div className="mt-4 pt-4 border-t">
            <dt className="text-sm text-gray-500 mb-1">Description</dt>
            <dd className="text-gray-900">{document.description}</dd>
          </div>
        )}

        <div className="mt-6 pt-4 border-t flex items-center gap-3">
          <button
            onClick={() => {
              if (pdfUrl) {
                setShowPdf((v) => !v)
              } else {
                void loadPdf()
              }
            }}
            className="btn-secondary"
          >
            View PDF
          </button>
          {pdfUrl && (
            <button
              onClick={() => window.open(pdfUrl, '_blank', 'noopener,noreferrer')}
              className="btn-secondary"
            >
              Open in New Tab
            </button>
          )}
        </div>
      </div>

      {showPdf && pdfUrl && (
        <div className="card overflow-hidden mb-6">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">PDF Preview</h2>
            <button onClick={() => setShowPdf(false)} className="btn-secondary">
              Hide
            </button>
          </div>
          <div className="w-full" style={{ height: 800 }}>
            <iframe
              title="PDF Preview"
              src={pdfUrl}
              className="w-full h-full"
            />
          </div>
        </div>
      )}

      {/* Actions */}
      {canGenerate && !generationJob && (
        <div className="grid md:grid-cols-2 gap-4">
          <button
            onClick={() => generateDeckMutation.mutate()}
            disabled={generateDeckMutation.isPending || generateQuizMutation.isPending}
            className="card p-6 text-left hover:border-primary-500 hover:shadow-md transition-all disabled:opacity-50"
          >
            <div className="flex items-center mb-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <SparklesIcon className="w-5 h-5 text-purple-600" />
              </div>
              <h3 className="ml-3 font-semibold text-gray-900">
                Generate Flashcards
              </h3>
            </div>
            <p className="text-sm text-gray-600">
              Generate a deck directly from this document (fast mode).
            </p>
          </button>

          <button
            onClick={() => generateQuizMutation.mutate()}
            disabled={generateDeckMutation.isPending || generateQuizMutation.isPending}
            className="card p-6 text-left hover:border-primary-500 hover:shadow-md transition-all disabled:opacity-50"
          >
            <div className="flex items-center mb-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <SparklesIcon className="w-5 h-5 text-green-600" />
              </div>
              <h3 className="ml-3 font-semibold text-gray-900">
                Generate Quiz
              </h3>
            </div>
            <p className="text-sm text-gray-600">
              Generate a quiz directly from this document (fast mode).
            </p>
          </button>
        </div>
      )}

      {currentJob && currentJob.status !== 'completed' && currentJob.status !== 'failed' && (
        <div className="card p-6 mt-6">
          <div className="flex items-center mb-4">
            <div className="w-5 h-5 mr-3 animate-spin rounded-full border-b-2 border-primary-600" />
            <h3 className="font-medium text-gray-900">
              Generating {generationType === 'deck' ? 'Flashcards' : 'Quiz'}...
            </h3>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${currentJob.progress ?? 10}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Status: <span className="font-medium">{currentJob.status}</span>
            {typeof currentJob.progress === 'number' ? ` • ${currentJob.progress}%` : ''}
            {currentJob.job_id ? ` • Job #${currentJob.job_id}` : ''}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {currentJob.message || 'Working… this can take a bit depending on the PDF.'}
          </p>
        </div>
      )}

      {currentJob?.status === 'failed' && (
        <div className="card p-6 mt-6 bg-red-50 border-red-200">
          <h3 className="font-medium text-red-900">Generation Failed</h3>
          <p className="text-sm text-red-700 mt-1">{currentJob.message || 'An error occurred.'}</p>
          <button
            onClick={() => {
              setGenerationJob(null)
              setGenerationType(null)
            }}
            className="btn-secondary mt-4"
          >
            Try Again
          </button>
        </div>
      )}

      {document.status === 'error' && (
        <div className="card p-6 bg-red-50 border-red-200">
          <h3 className="font-medium text-red-900 mb-2">Processing Error</h3>
          <p className="text-red-700">{document.error_message}</p>
          <button
            onClick={() => documentsApi.reprocess(document.id)}
            className="btn-secondary mt-4"
          >
            Retry Processing
          </button>
        </div>
      )}
    </div>
  )
}
