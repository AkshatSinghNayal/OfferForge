/**
 * Resumes page.
 *
 * Upload: uses real /resumes/upload endpoint (multipart/form-data).
 * PDF bytes are stored by the backend in PostgreSQL; storage credentials and
 * the optional Gemini key are never exposed to the browser.
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
import { Upload, FileText, Star, Trash2, ExternalLink, Sparkles, History, Target } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { EmptyState } from '@/components/shared/EmptyState'
import { JobMatchDialog } from '@/components/resumes/JobMatchDialog'
import { JobMatchResultsDialog } from '@/components/resumes/JobMatchResultsDialog'
import { resumesApi, type JobMatchAnalysis, type ResumePublic } from '@/api/resumes'
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
  const [matchResume, setMatchResume] = useState<ResumePublic | null>(null)
  const [matchResult, setMatchResult] = useState<JobMatchAnalysis | null>(null)

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
    onSuccess: resume => {
      toast.success('Resume uploaded — add a job description to check your match')
      qc.invalidateQueries({ queryKey: ['resumes'] })
      setUploadOpen(false)
      setSelectedFile(null)
      reset()
      setMatchResume(resume)
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

  const historyMutation = useMutation({
    mutationFn: (resumeId: string) => resumesApi.listJobMatches(resumeId),
    onSuccess: data => {
      if (data.items.length === 0) {
        toast.info('No previous job match analyses for this resume')
        return
      }
      setMatchResult(data.items[0])
    },
    onError: () => toast.error('Could not load the latest job match'),
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {data?.items.map(r => (
            <Card
              key={r.id}
              className={`relative overflow-hidden transition-all duration-300 group hover:shadow-2xl hover:shadow-indigo-500/10 ${
                r.is_active
                  ? 'bg-slate-900/90 border-indigo-500/50 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/20'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700/80 hover:bg-slate-900/80'
              }`}
            >
              {r.is_active && (
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400" />
              )}

              <CardContent className="p-5">
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/15 to-violet-500/15 text-indigo-400 border border-indigo-500/25 shrink-0 group-hover:scale-105 transition-transform">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold text-slate-100 truncate group-hover:text-indigo-300 transition-colors" title={r.version_label}>
                        {r.version_label}
                      </h3>
                      <p className="text-xs text-slate-400">
                        Uploaded {format(new Date(r.created_at), 'MMM d, yyyy')}
                      </p>
                    </div>
                  </div>

                  {r.is_active && (
                    <Badge className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1.5 shrink-0 shadow-[0_0_10px_rgba(16,185,129,0.15)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Active
                    </Badge>
                  )}
                </div>

                {/* General Readiness Progress */}
                <div className="space-y-2 my-4 p-3 rounded-xl bg-slate-950/40 border border-slate-800/60">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-medium">
                      General readiness
                    </span>
                    <span className="text-slate-200 font-bold">{r.readiness_score.toFixed(0)}%</span>
                  </div>
                  <Progress value={r.readiness_score} className="h-2 bg-slate-800" />
                </div>

                {/* Latest Job Match Card Badge */}
                {r.latest_match_score !== undefined && r.latest_match_score !== null && (
                  <div className="mb-4 p-3 rounded-xl bg-slate-950/70 border border-indigo-500/20 hover:border-indigo-500/40 transition-all flex items-center justify-between gap-3 shadow-inner">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-1.5 rounded-lg bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 shrink-0">
                        <Target className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Last Job Match</p>
                        <p className="text-xs font-semibold text-slate-200 truncate" title={r.latest_job_title || 'Recent Job'}>
                          {r.latest_job_title || 'Recent Job'}
                        </p>
                      </div>
                    </div>
                    <div className={`px-2.5 py-1 rounded-lg border text-xs font-bold shrink-0 shadow-sm ${
                      r.latest_match_score >= 70
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-emerald-500/10'
                        : r.latest_match_score >= 50
                        ? 'bg-amber-500/15 text-amber-400 border-amber-500/30 shadow-amber-500/10'
                        : 'bg-rose-500/15 text-rose-400 border-rose-500/30 shadow-rose-500/10'
                    }`}>
                      {r.latest_match_score}% Match
                    </div>
                  </div>
                )}

                {/* Primary Action Button */}
                <Button
                  size="sm"
                  className="w-full text-xs font-semibold h-9 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-md shadow-indigo-500/20 hover:shadow-indigo-500/35 border border-indigo-400/20 transition-all duration-200 active:scale-[0.99]"
                  onClick={() => setMatchResume(r)}
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5 text-indigo-200 animate-pulse" /> Match to a job
                </Button>

                {/* Secondary Action Toolbar */}
                <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-800/80 text-xs">
                  {!r.is_active && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="flex-1 text-xs h-8 text-slate-400 hover:text-amber-300 hover:bg-amber-500/10 px-2"
                      onClick={() => activateMutation.mutate(r.id)}
                      disabled={activateMutation.isPending}
                    >
                      <Star className="h-3.5 w-3.5 mr-1" /> Set Active
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="flex-1 text-xs h-8 text-slate-300 hover:text-white hover:bg-slate-800 px-2"
                    onClick={() => openPdf(r.id)}
                    disabled={pdfLoading}
                  >
                    <FileText className="h-3.5 w-3.5 mr-1 text-indigo-400" /> {pdfLoading ? 'Loading…' : 'View PDF'}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="flex-1 text-xs h-8 text-slate-300 hover:text-white hover:bg-slate-800 px-2"
                    onClick={() => historyMutation.mutate(r.id)}
                    disabled={historyMutation.isPending}
                  >
                    <History className="h-3.5 w-3.5 mr-1 text-violet-400" /> Last match
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 shrink-0 rounded-lg"
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
            <iframe
              src={pdfUrl ?? ''}
              title="Resume Preview"
              className="w-full h-full rounded border border-[var(--border)]"
            />
          </div>
        </DialogContent>
      </Dialog>

      <JobMatchDialog
        resume={matchResume}
        open={!!matchResume}
        onOpenChange={open => { if (!open) setMatchResume(null) }}
        onAnalyzed={analysis => {
          setMatchResult(analysis)
          qc.invalidateQueries({ queryKey: ['resumes'] })
          qc.refetchQueries({ queryKey: ['resumes'] })
          toast.success(`Job match analysis complete: ${analysis.overall_score}%`)
        }}
      />

      <JobMatchResultsDialog
        analysis={matchResult}
        open={!!matchResult}
        onOpenChange={open => { if (!open) setMatchResult(null) }}
      />

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
