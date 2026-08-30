import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'
import { BrainCircuit, FileSearch, LockKeyhole, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { resumesApi, type JobMatchAnalysis, type ResumePublic } from '@/api/resumes'

const MIN_JD_LENGTH = 100
const MAX_JD_LENGTH = 50000

interface JobMatchDialogProps {
  resume: ResumePublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAnalyzed: (analysis: JobMatchAnalysis) => void
}

export function JobMatchDialog({ resume, open, onOpenChange, onAnalyzed }: JobMatchDialogProps) {
  const [jobTitle, setJobTitle] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [jobDescription, setJobDescription] = useState('')

  useEffect(() => {
    if (!open) {
      setJobTitle('')
      setCompanyName('')
      setJobDescription('')
    }
  }, [open])

  const analysisMutation = useMutation({
    mutationFn: () => resumesApi.analyzeJobMatch(resume!.id, {
      job_description: jobDescription.trim(),
      ...(jobTitle.trim() && { job_title: jobTitle.trim() }),
      ...(companyName.trim() && { company_name: companyName.trim() }),
    }),
    onSuccess: analysis => {
      onOpenChange(false)
      onAnalyzed(analysis)
    },
    onError: error => {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail
        : null
      toast.error(typeof message === 'string' ? message : 'Could not analyze this resume. Please try again.')
    },
  })

  const trimmedLength = jobDescription.trim().length
  const canSubmit = !!resume && trimmedLength >= MIN_JD_LENGTH && trimmedLength <= MAX_JD_LENGTH

  return (
    <Dialog open={open} onOpenChange={value => !analysisMutation.isPending && onOpenChange(value)}>
      <DialogContent className="max-w-2xl overflow-hidden p-0">
        <div className="border-b border-[var(--border)] bg-gradient-to-br from-[var(--accent)]/15 via-transparent to-violet-500/10 px-6 py-5">
          <DialogHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--accent)]/25 bg-[var(--accent)]/15 text-[var(--accent)]">
              <FileSearch className="h-5 w-5" />
            </div>
            <DialogTitle>Match resume to a job</DialogTitle>
            <DialogDescription>
              Gemini will compare <span className="font-medium text-[var(--text-primary)]">{resume?.version_label}</span> against the role and cite the evidence behind every match.
            </DialogDescription>
          </DialogHeader>
        </div>

        <form
          className="space-y-4 px-6 pb-6"
          onSubmit={event => {
            event.preventDefault()
            if (canSubmit) analysisMutation.mutate()
          }}
        >
          <div className="grid grid-cols-1 gap-4 pt-5 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="job-title">Job title <span className="font-normal text-[var(--text-muted)]">(optional)</span></Label>
              <Input id="job-title" value={jobTitle} maxLength={160} onChange={e => setJobTitle(e.target.value)} placeholder="Software Engineer" disabled={analysisMutation.isPending} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="company-name">Company <span className="font-normal text-[var(--text-muted)]">(optional)</span></Label>
              <Input id="company-name" value={companyName} maxLength={160} onChange={e => setCompanyName(e.target.value)} placeholder="Company name" disabled={analysisMutation.isPending} />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="job-description">Job description</Label>
              <span className={`text-[11px] ${trimmedLength > MAX_JD_LENGTH ? 'text-[var(--danger)]' : 'text-[var(--text-muted)]'}`}>
                {trimmedLength.toLocaleString()} / {MAX_JD_LENGTH.toLocaleString()}
              </span>
            </div>
            <Textarea
              id="job-description"
              className="min-h-52 resize-y leading-relaxed"
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              placeholder="Paste the complete job description, including responsibilities and required qualifications…"
              disabled={analysisMutation.isPending}
              aria-describedby="jd-help"
            />
            <p id="jd-help" className="text-xs text-[var(--text-muted)]">
              Include at least {MIN_JD_LENGTH} characters so the comparison has enough detail.
            </p>
          </div>

          <div className="flex gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)]/55 p-3">
            <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />
            <p className="text-xs leading-relaxed text-[var(--text-muted)]">
              Your resume and this job description are sent securely to Gemini for this analysis. The result is an evidence-based estimate, not a hiring prediction.
            </p>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="ghost" disabled={analysisMutation.isPending} onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={!canSubmit || analysisMutation.isPending} className="min-w-36">
              {analysisMutation.isPending ? (
                <><BrainCircuit className="animate-pulse" /> Analyzing…</>
              ) : (
                <><Sparkles /> Analyze match</>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
