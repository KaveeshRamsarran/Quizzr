import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DocumentIcon,
  TrashIcon,
  PlusIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { documentsApi } from '../lib/api'

export default function Documents() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['documents', { page: 1, limit: 50 }],
    queryFn: () => documentsApi.list({ page: 1, limit: 50 }),
    retry: false,
    staleTime: 15000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentsApi.delete(id),
    onSuccess: async () => {
      toast.success('Document deleted')
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Failed to delete document')
    },
  })

  const handleDelete = (id: number, title: string) => {
    if (deleteMutation.isPending) return
    const ok = window.confirm(`Delete "${title}"? This cannot be undone.`)
    if (!ok) return
    deleteMutation.mutate(id)
  }

  const documents = data?.documents ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-600 text-sm">
            {data ? `${data.total} total` : 'Your uploaded PDFs'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['documents'] })}
            className="btn-secondary"
            disabled={isLoading}
          >
            <ArrowPathIcon className="w-5 h-5 mr-2" />
            Refresh
          </button>
          <Link to="/upload" className="btn-primary">
            <PlusIcon className="w-5 h-5 mr-2" />
            Upload
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">All Documents</h2>
        </div>

        {isLoading ? (
          <div className="p-8 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-gray-600">
            Failed to load documents.
          </div>
        ) : documents.length === 0 ? (
          <div className="p-10 text-center text-gray-500">
            <DocumentIcon className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p className="font-medium text-gray-700">No documents yet</p>
            <p className="text-sm">Upload your first PDF to get started.</p>
            <Link to="/upload" className="btn-primary mt-4 inline-flex">
              <PlusIcon className="w-5 h-5 mr-2" />
              Upload Document
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center p-4 gap-3">
                <button
                  onClick={() => navigate(`/documents/${doc.id}`)}
                  className="flex items-center gap-3 min-w-0 flex-1 text-left"
                >
                  <DocumentIcon className="w-10 h-10 text-gray-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.title || doc.filename}
                    </p>
                    <p className="text-xs text-gray-500">
                      {doc.page_count ?? '—'} pages • {doc.status} •{' '}
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </button>

                <span
                  className={clsx(
                    'px-2 py-1 rounded-full text-xs font-medium shrink-0',
                    doc.status === 'processed'
                      ? 'bg-green-100 text-green-800'
                      : doc.status === 'processing'
                        ? 'bg-blue-100 text-blue-800'
                        : doc.status === 'pending'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                  )}
                >
                  {doc.status}
                </span>

                <button
                  onClick={() => handleDelete(doc.id, doc.title || doc.filename)}
                  className="p-2 rounded-lg text-red-600 hover:bg-red-50 disabled:opacity-50"
                  disabled={deleteMutation.isPending}
                  title="Delete"
                >
                  <TrashIcon className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500">
        Showing up to 50 most recent documents.
      </p>
    </div>
  )
}
