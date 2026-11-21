import { useCallback, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowUpTrayIcon, CheckCircleIcon, DocumentTextIcon, ExclamationCircleIcon, QuestionMarkCircleIcon, RectangleStackIcon, XMarkIcon,
} from '@heroicons/react/24/outline'
import { documentsApi, errorMessage } from '../lib/api'
import { fileSize } from '../lib/format'
import { Button, PageHeader } from '../components/ui'
import { EASE_OUT, Page, ProgressBar } from '../components/motion'
import type { Document } from '../types'

const MAX_MB = 50

export default function Upload() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploaded, setUploaded] = useState<Document | null>(null)

  const doc = useQuery({
    queryKey: ['documents', uploaded?.id],
    queryFn: () => documentsApi.get(uploaded!.id),
    enabled: !!uploaded,
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'processed' || status === 'error' ? false : 1000
    },
  })

  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    setError(null)
    if (rejected.length) {
      const code = rejected[0].errors[0]?.code
      setError(code === 'file-too-large' ? `That file is over ${MAX_MB} MB.` : 'Only PDF files can be uploaded.')
      return
    }
    if (accepted[0]) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: MAX_MB * 1024 * 1024,
    multiple: false,
    noClick: true,
    disabled: uploading,
  })

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setProgress(0)
    try {
      const result = await documentsApi.upload(file, setProgress)
      setUploaded(result)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    } catch (err) {
      setError(errorMessage(err, 'The upload failed.'))
    } finally {
      setUploading(false)
    }
  }

  const reset = () => {
    setFile(null)
    setUploaded(null)
    setProgress(0)
    setError(null)
  }

  const current = doc.data ?? uploaded
  const status = current?.status
  const stage = !uploaded ? 'pick' : status === 'processed' ? 'done' : status === 'error' ? 'error' : 'reading'

  return (
    <Page className="page page--narrow">
      <PageHeader title="Upload a PDF" sub="Lecture notes, slides or a textbook chapter. PDFs need selectable text." />

      <AnimatePresence mode="wait">
        {stage === 'pick' && (
          <motion.div key="pick" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3, ease: EASE_OUT }}>
            {!file ? (
              <div
                {...getRootProps({
                  className: 'dropzone',
                  'data-active': isDragActive,
                  role: 'button',
                  tabIndex: 0,
                  'aria-label': 'Choose a PDF to upload',
                  onClick: open,
                  onKeyDown: (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open() } },
                })}
              >
                <input {...getInputProps({ name: 'file' })} />
                <motion.div className="dropzone__icon" animate={isDragActive ? { scale: 1.12, rotate: -6 } : { scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 400, damping: 18 }}>
                  <ArrowUpTrayIcon aria-hidden="true" />
                </motion.div>
                <div>
                  <h2 style={{ fontSize: 'var(--text-xl)' }}>{isDragActive ? 'Drop it here' : 'Drag your PDF here'}</h2>
                  <p className="muted" style={{ marginTop: 6 }}>or click to choose a file, up to {MAX_MB} MB</p>
                </div>
              </div>
            ) : (
              <motion.div className="card card--pad" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3, ease: EASE_OUT }}>
                <div className="flex items-center gap-4">
                  <div className="icon-tile" style={{ width: 52, height: 52 }}><DocumentTextIcon aria-hidden="true" /></div>
                  <div className="min-w-0 flex-1">
                    <p className="row-title truncate">{file.name}</p>
                    <p className="row-meta">{fileSize(file.size)}</p>
                  </div>
                  {!uploading && <Button variant="ghost" size="sm" icon={<XMarkIcon />} aria-label="Remove file" onClick={reset} />}
                </div>
                {uploading && (
                  <div style={{ marginTop: 20 }}>
                    <ProgressBar value={progress} label="Upload progress" />
                    <p className="small muted" style={{ marginTop: 8 }}>Uploading… {progress}%</p>
                  </div>
                )}
                <div className="flex flex-wrap gap-2" style={{ marginTop: 20 }}>
                  <Button variant="primary" size="lg" onClick={upload} loading={uploading}>Upload and read</Button>
                  {!uploading && <Button size="lg" onClick={open}>Choose another</Button>}
                </div>
                <input {...getInputProps({ name: 'file' })} />
              </motion.div>
            )}
            {error && (
              <motion.div className="notice notice--error" role="alert" style={{ marginTop: 16 }} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: [0, -6, 6, -3, 0] }} transition={{ duration: 0.4 }}>
                <ExclamationCircleIcon aria-hidden="true" />{error}
              </motion.div>
            )}
          </motion.div>
        )}

        {stage === 'reading' && (
          <motion.div key="reading" className="card card--pad" aria-live="polite" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3, ease: EASE_OUT }}>
            <div className="flex items-center gap-4">
              <motion.div className="icon-tile" style={{ width: 52, height: 52 }} animate={{ scale: [1, 1.06, 1] }} transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}>
                <DocumentTextIcon aria-hidden="true" />
              </motion.div>
              <div className="min-w-0">
                <h2 style={{ fontSize: 'var(--text-xl)' }}>Reading your PDF…</h2>
                <p className="muted">Pulling out the text and splitting it into study sections.</p>
              </div>
            </div>
            <div style={{ marginTop: 20 }}><ProgressBar value={status === 'processing' ? 70 : 30} label="Processing progress" /></div>
          </motion.div>
        )}

        {stage === 'done' && current && (
          <motion.div key="done" className="card card--pad" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: 'spring', stiffness: 300, damping: 26 }}>
            <div className="flex items-center gap-4">
              <motion.div initial={{ scale: 0, rotate: -45 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 400, damping: 15, delay: 0.1 }}>
                <CheckCircleIcon aria-hidden="true" style={{ width: 52, height: 52, color: 'var(--color-success)' }} />
              </motion.div>
              <div className="min-w-0">
                <h2 style={{ fontSize: 'var(--text-xl)' }}>Ready to study</h2>
                <p className="muted truncate">{current.title || current.original_filename}, {current.page_count} {current.page_count === 1 ? 'page' : 'pages'}</p>
              </div>
            </div>
            <p style={{ marginTop: 20 }} className="label">What would you like to make?</p>
            <div className="grid gap-3 sm:grid-cols-2" style={{ marginTop: 10 }}>
              <button type="button" className="card card-link text-left" style={{ padding: 20, border: 0, cursor: 'pointer' }} onClick={() => navigate(`/documents/${current.id}?make=deck`)}>
                <div className="icon-tile"><RectangleStackIcon aria-hidden="true" /></div>
                <h3 style={{ marginTop: 12 }}>Flashcards</h3>
                <p className="row-meta">Definitions and fill-the-gap cards to review over time.</p>
              </button>
              <button type="button" className="card card-link text-left" style={{ padding: 20, border: 0, cursor: 'pointer' }} onClick={() => navigate(`/documents/${current.id}?make=quiz`)}>
                <div className="icon-tile"><QuestionMarkCircleIcon aria-hidden="true" /></div>
                <h3 style={{ marginTop: 12 }}>A quiz</h3>
                <p className="row-meta">Multiple choice, true or false and short answers.</p>
              </button>
            </div>
            <div style={{ marginTop: 16 }}><Button variant="ghost" onClick={reset}>Upload another PDF</Button></div>
          </motion.div>
        )}

        {stage === 'error' && current && (
          <motion.div key="error" className="card card--pad" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="notice notice--error" role="alert"><ExclamationCircleIcon aria-hidden="true" />{current.error_message || 'This PDF couldn’t be read.'}</div>
            <div className="flex flex-wrap gap-2" style={{ marginTop: 16 }}>
              <Button variant="primary" onClick={reset}>Try another file</Button>
              <Link to={`/documents/${current.id}`} className="btn">Open document</Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Page>
  )
}
