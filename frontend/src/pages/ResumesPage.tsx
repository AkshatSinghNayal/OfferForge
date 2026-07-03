/**
 * Resumes page.
 *
 * Upload: uses real /resumes/upload endpoint (multipart/form-data).
 * Cloudinary credentials are stored in the backend .env — the frontend
 * never touches them. If CLOUDINARY_CLOUD_NAME etc. are not set in the
 * backend .env, the upload call will succeed at the API layer but
 * Cloudinary will return an error which the backend propagates as 400.
 *
 * The drag-drop zone validates PDF-only + 5MB max client-side before
 * sending (matching the backend constraint) so the user sees an inline
 * error rather than a network failure.
 */
import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import axios from 'axios'
import { Upload, FileText, Star, Trash2, ExternalLink } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { EmptyState } from '@/components/shared/EmptyState'
import { resumesApi } from '@/api/resumes'
import { format } from 'date-fns'

const MAX_SIZE = 5 * 1024 * 1024 // 5MB

const uploadSchema = z.object({
  version_label: z.string().min(1, 'Label is required').max(80),
})
type UploadForm = z.infer<typeof uploadSchema>

export default function ResumesPage() {
  const qc = useQueryClient()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const dropRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState(false)

  // Revoke the blob URL when the modal closes to free memory
  const closePdf = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl)
    setPdfUrl(null)
  }

  const openPdf = async (resumeId: string) => {
    setPdfLoading(true)
    try {
      const blobUrl = await resumesApi.fetchPdfBlobUrl(resumeId)
      setPdfUrl(blobUrl)
    } catch {
      toast.error('Failed to load PDF')
    } finally {
      setPdfLoading(false)
    }
  }

  const { data, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: resumesApi.list,
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<UploadForm>({
    resolver: zodResolver(uploadSchema),
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, label }: { file: File; label: string }) =>
      resumesApi.upload(file, label),
    onSuccess: () => {
      toast.success('Resume uploaded')
      qc.invalidateQueries({ queryKey: ['resumes'] })
      setUploadOpen(false)
      setSelectedFile(null)
      reset()
    },
    onError: (err) => {
      if (axios.isAxiosError(err)) {
        toast.error(err.response?.data?.detail ?? 'Upload failed')
      } else {
        toast.error('Upload failed')
      }
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id: string) => resumesApi.activate(id),
    onSuccess: () => {
      toast.success('Resume set as active')
      qc.invalidateQueries({ queryKey: ['resumes'] })
    },
    onError: () => toast.error('Failed to activate resume'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumesApi.delete(id),
    onSuccess: () => {
      toast.success('Resume deleted')
      qc.invalidateQueries({ queryKey: ['resumes'] })
    },
    onError: () => toast.error('Failed to delete resume'),
  })

  const validateAndSetFile = (file: File) => {
    if (file.type !== 'application/pdf') {
      setFileError('Only PDF files are accepted')
      setSelectedFile(null)
      return
    }
    if (file.size > MAX_SIZE) {
      setFileError('File must be under 5MB')
      setSelectedFile(null)
      return
    }
    setFileError(null)
    setSelectedFile(file)
  }

  const onSubmit = (form: UploadForm) => {
    if (!selectedFile) { setFileError('Please select a PDF file'); return }
    uploadMutation.mutate({ file: selectedFile, label: form.version_label })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Resumes</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">{data?.items.length ?? 0} versions</p>
        </div>
        <Button size="sm" onClick={() => setUploadOpen(true)}>
          <Upload className="h-4 w-4 mr-1" /> Upload Resume
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="No resumes uploaded yet"
          description="Upload your first resume to start tracking readiness and keywords."
          actionLabel="Upload Resume"
          onAction={() => setUploadOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map(r => (
            <Card key={r.id} className={r.is_active ? 'border-[var(--accent)]/40' : ''}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="h-4 w-4 text-[var(--accent)] shrink-0" />
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {r.version_label}
                    </p>
                  </div>
                  {r.is_active && <Badge variant="success" className="text-[10px] shrink-0">Active</Badge>}
                </div>
                <p className="text-xs text-[var(--text-muted)] mb-3">
                  Uploaded {format(new Date(r.created_at), 'MMM d, yyyy')}
                </p>
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--text-muted)]">Readiness</span>
                    <span className="text-[var(--text-primary)]">{r.readiness_score.toFixed(0)}%</span>
                  </div>
                  <Progress value={r.readiness_score} className="h-1.5" />
                </div>
                <div className="flex gap-2 mt-3">
                  {!r.is_active && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 text-xs h-7"
                      onClick={() => activateMutation.mutate(r.id)}
                      disabled={activateMutation.isPending}
                    >
                      <Star className="h-3 w-3 mr-1" /> Set Active
                    </Button>
                  )}
                  <Button
                      size="sm"
                      variant="ghost"
                      className="flex-1 text-xs h-7"
                      onClick={() => openPdf(r.id)}
                      disabled={pdfLoading}
                    >
                      <FileText className="h-3 w-3 mr-1" /> {pdfLoading ? 'Loading…' : 'View PDF'}
                    </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 p-0 text-[var(--text-muted)] hover:text-[var(--danger)]"
                    onClick={() => deleteMutation.mutate(r.id)}
                    disabled={deleteMutation.isPending}
                    aria-label="Delete resume"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* PDF viewer dialog */}
      <Dialog open={!!pdfUrl} onOpenChange={v => { if (!v) closePdf() }}>
        <DialogContent className="max-w-4xl w-full h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-4 pt-4 pb-2 flex flex-row items-center justify-between">
            <DialogTitle className="text-sm">Resume Preview</DialogTitle>
            <a
              href={pdfUrl ?? ''}
              download="resume.pdf"
              className="flex items-center gap-1 text-xs text-[var(--accent)] hover:underline"
            >
              <ExternalLink className="h-3 w-3" /> Download
            </a>
          </DialogHeader>
          <div className="flex-1 px-4 pb-4">
            <object
              data={pdfUrl ?? ''}
              type="application/pdf"
              className="w-full h-full rounded border border-[var(--border)]"
            >
              <p className="text-sm text-[var(--text-muted)] p-4">
                Your browser cannot display this PDF inline.{' '}
                <a href={pdfUrl ?? ''} download className="text-[var(--accent)] underline">
                  Download instead
                </a>
              </p>
            </object>
          </div>
        </DialogContent>
      </Dialog>

      {/* Upload dialog */}
      <Dialog open={uploadOpen} onOpenChange={v => { if (!v) { setUploadOpen(false); setSelectedFile(null); setFileError(null); reset() } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Upload Resume</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-2">
            {/* Drag-drop zone */}
            <div
              ref={dropRef}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                dragging ? 'border-[var(--accent)] bg-[var(--accent)]/5' : 'border-[var(--border)]'
              }`}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => {
                e.preventDefault()
                setDragging(false)
                const file = e.dataTransfer.files[0]
                if (file) validateAndSetFile(file)
              }}
              onClick={() => document.getElementById('resume-file-input')?.click()}
            >
              <input
                id="resume-file-input"
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={e => {
                  const file = e.target.files?.[0]
                  if (file) validateAndSetFile(file)
                }}
              />
              <Upload className="h-6 w-6 text-[var(--text-muted)] mx-auto mb-2" />
              {selectedFile ? (
                <p className="text-sm text-[var(--text-primary)]">{selectedFile.name}</p>
              ) : (
                <p className="text-sm text-[var(--text-muted)]">
                  Drop PDF here or click to browse
                  <br />
                  <span className="text-xs">PDF only · Max 5MB</span>
                </p>
              )}
            </div>
            {fileError && <p className="text-xs text-[var(--danger)]">{fileError}</p>}

            <div className="space-y-1.5">
              <Label htmlFor="version_label">Version label</Label>
              <Input
                id="version_label"
                placeholder="e.g. Software Engineer v3"
                {...register('version_label')}
                aria-invalid={!!errors.version_label}
              />
              {errors.version_label && <p className="text-xs text-[var(--danger)]">{errors.version_label.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => { setUploadOpen(false); setSelectedFile(null); setFileError(null); reset() }}>
                Cancel
              </Button>
              <Button type="submit" disabled={uploadMutation.isPending}>
                {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
