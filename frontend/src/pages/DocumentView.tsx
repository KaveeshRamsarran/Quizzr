import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  DocumentIcon,
  ArrowLeftIcon,
  SparklesIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import { documentsApi } from '../lib/api'
import clsx from 'clsx'

export default function DocumentView() {
  const { id } = useParams<{ id: string }>()
  const documentId = parseInt(id || '0')

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsApi.get(documentId),
    enabled: !!documentId,
  })

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
        
        <div className="flex items-start justify-between">
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
      </div>

      {/* Actions */}
      {document.status === 'processed' && (
        <div className="grid md:grid-cols-2 gap-4">
          <Link
            to={`/upload?document=${document.id}&type=deck`}
            className="card p-6 hover:border-primary-500 hover:shadow-md transition-all"
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
              Create a new deck of flashcards from this document
            </p>
          </Link>

          <Link
            to={`/upload?document=${document.id}&type=quiz`}
            className="card p-6 hover:border-primary-500 hover:shadow-md transition-all"
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
              Create a new quiz from this document
            </p>
          </Link>
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
