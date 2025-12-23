import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DocumentArrowUpIcon,
  DocumentIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { documentsApi, generationApi } from '../lib/api'
import type { Document, GenerationJob } from '../types'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function Upload() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [uploadedDoc, setUploadedDoc] = useState<Document | null>(null)
  const [generationJob, setGenerationJob] = useState<GenerationJob | null>(null)
  const [generationType, setGenerationType] = useState<'deck' | 'quiz' | null>(null)

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: (doc) => {
      setUploadedDoc(doc)
      toast.success('Document uploaded successfully!')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Upload failed')
    },
  })

  // Generation mutation
  const generateDeckMutation = useMutation({
    mutationFn: (documentId: number) =>
      generationApi.generateDeck({ document_id: documentId }),
    onSuccess: (job) => {
      setGenerationJob(job)
      setGenerationType('deck')
      toast.success('Deck generation started!')
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Generation failed')
    },
  })

  const generateQuizMutation = useMutation({
    mutationFn: (documentId: number) =>
      generationApi.generateQuiz({ document_id: documentId }),
    onSuccess: (job) => {
      setGenerationJob(job)
      setGenerationType('quiz')
      toast.success('Quiz generation started!')
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Generation failed')
    },
  })

  // Poll for job status
  const { data: jobStatus } = useQuery({
    queryKey: ['generation-job', generationJob?.job_id],
    queryFn: () => generationApi.getJobStatus(generationJob!.job_id),
    enabled: !!generationJob && generationJob.status !== 'completed' && generationJob.status !== 'failed',
    refetchInterval: 2000,
  })

  // Poll for document processing status
  const { data: docStatus } = useQuery({
    queryKey: ['document', uploadedDoc?.id],
    queryFn: () => documentsApi.get(uploadedDoc!.id),
    enabled: !!uploadedDoc && uploadedDoc.status !== 'processed' && uploadedDoc.status !== 'error',
    refetchInterval: 2000,
  })

  const currentDoc = docStatus || uploadedDoc
  const currentJob = jobStatus || generationJob

  // Handle job completion
  if (currentJob?.status === 'completed' && currentJob.result_id) {
    const resultPath = generationType === 'deck' 
      ? `/decks/${currentJob.result_id}`
      : `/quizzes/${currentJob.result_id}`
    
    setTimeout(() => {
      navigate(resultPath)
    }, 1000)
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      uploadMutation.mutate(file)
    }
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    maxFiles: 1,
  })

  const resetUpload = () => {
    setUploadedDoc(null)
    setGenerationJob(null)
    setGenerationType(null)
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Document</h1>
        <p className="mt-2 text-gray-600">
          Upload a PDF and let AI generate flashcards and quizzes for you
        </p>
      </div>

      {!uploadedDoc ? (
        // Upload dropzone
        <div
          {...getRootProps()}
          className={clsx(
            'card p-12 border-2 border-dashed cursor-pointer transition-all',
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50',
            uploadMutation.isPending && 'opacity-50 cursor-not-allowed'
          )}
        >
          <input {...getInputProps()} disabled={uploadMutation.isPending} />
          <div className="text-center">
            {uploadMutation.isPending ? (
              <>
                <ArrowPathIcon className="w-16 h-16 mx-auto text-primary-500 animate-spin" />
                <p className="mt-4 text-lg font-medium text-gray-900">
                  Uploading...
                </p>
              </>
            ) : (
              <>
                <DocumentArrowUpIcon className="w-16 h-16 mx-auto text-gray-400" />
                <p className="mt-4 text-lg font-medium text-gray-900">
                  {isDragActive ? 'Drop your PDF here' : 'Drag & drop your PDF here'}
                </p>
                <p className="mt-2 text-sm text-gray-500">
                  or click to browse (max 50MB)
                </p>
              </>
            )}
          </div>
        </div>
      ) : (
        // Document uploaded - show status and options
        <div className="space-y-6">
          {/* Document status card */}
          <div className="card p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center">
                <DocumentIcon className="w-12 h-12 text-primary-500" />
                <div className="ml-4">
                  <h3 className="font-medium text-gray-900">
                    {currentDoc?.title || currentDoc?.filename}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {currentDoc?.page_count} pages • {((currentDoc?.file_size || 0) / 1024).toFixed(0)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={resetUpload}
                className="p-2 text-gray-400 hover:text-gray-500"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Processing status */}
            <div className="mt-4 flex items-center">
              {currentDoc?.status === 'pending' || currentDoc?.status === 'processing' ? (
                <>
                  <ArrowPathIcon className="w-5 h-5 text-primary-500 animate-spin mr-2" />
                  <span className="text-sm text-gray-600">Processing document...</span>
                </>
              ) : currentDoc?.status === 'processed' ? (
                <>
                  <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />
                  <span className="text-sm text-green-600">Document processed successfully</span>
                </>
              ) : (
                <>
                  <ExclamationCircleIcon className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-sm text-red-600">
                    {currentDoc?.error_message || 'Processing failed'}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Generation options */}
          {currentDoc?.status === 'processed' && !generationJob && (
            <div className="grid md:grid-cols-2 gap-4">
              <button
                onClick={() => generateDeckMutation.mutate(currentDoc.id)}
                disabled={generateDeckMutation.isPending || generateQuizMutation.isPending}
                className="card p-6 text-left hover:border-primary-500 hover:shadow-md transition-all disabled:opacity-50"
              >
                <div className="flex items-center mb-4">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <SparklesIcon className="w-6 h-6 text-purple-600" />
                  </div>
                  <h3 className="ml-3 text-lg font-semibold text-gray-900">
                    Generate Flashcards
                  </h3>
                </div>
                <p className="text-sm text-gray-600">
                  Create a deck of flashcards from key concepts in your document.
                  Perfect for spaced repetition study.
                </p>
              </button>

              <button
                onClick={() => generateQuizMutation.mutate(currentDoc.id)}
                disabled={generateDeckMutation.isPending || generateQuizMutation.isPending}
                className="card p-6 text-left hover:border-primary-500 hover:shadow-md transition-all disabled:opacity-50"
              >
                <div className="flex items-center mb-4">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <SparklesIcon className="w-6 h-6 text-green-600" />
                  </div>
                  <h3 className="ml-3 text-lg font-semibold text-gray-900">
                    Generate Quiz
                  </h3>
                </div>
                <p className="text-sm text-gray-600">
                  Create a quiz with multiple choice, true/false, and fill-in-the-blank
                  questions.
                </p>
              </button>
            </div>
          )}

          {/* Generation progress */}
          {currentJob && currentJob.status !== 'completed' && currentJob.status !== 'failed' && (
            <div className="card p-6">
              <div className="flex items-center mb-4">
                <ArrowPathIcon className="w-6 h-6 text-primary-500 animate-spin mr-3" />
                <h3 className="font-medium text-gray-900">
                  Generating {generationType === 'deck' ? 'Flashcards' : 'Quiz'}...
                </h3>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${currentJob.progress || 10}%` }}
                />
              </div>
              <p className="mt-2 text-sm text-gray-500">
                This may take a minute. We're extracting key concepts and generating content.
              </p>
            </div>
          )}

          {/* Generation complete */}
          {currentJob?.status === 'completed' && (
            <div className="card p-6 bg-green-50 border-green-200">
              <div className="flex items-center">
                <CheckCircleIcon className="w-6 h-6 text-green-500 mr-3" />
                <div>
                  <h3 className="font-medium text-green-900">
                    {generationType === 'deck' ? 'Flashcards' : 'Quiz'} Generated!
                  </h3>
                  <p className="text-sm text-green-700">
                    Redirecting you to your new content...
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Generation failed */}
          {currentJob?.status === 'failed' && (
            <div className="card p-6 bg-red-50 border-red-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <ExclamationCircleIcon className="w-6 h-6 text-red-500 mr-3" />
                  <div>
                    <h3 className="font-medium text-red-900">Generation Failed</h3>
                    <p className="text-sm text-red-700">
                      {currentJob.message || 'An error occurred during generation'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setGenerationJob(null)}
                  className="btn-secondary text-sm"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
