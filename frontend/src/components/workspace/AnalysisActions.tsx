import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ListPlus, Plus, BriefcaseBusiness } from 'lucide-react'
import { toast } from 'sonner'
import { workspaceApi } from '@/api/workspace'
import type { JobMatchAnalysis } from '@/api/resumes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export function AddGapTask({
  analysisId,
  index,
}: {
  analysisId: string
  index: number
}) {
  const qc = useQueryClient()
  const tasks = useQuery({
    queryKey: ['preparation-tasks'],
    queryFn: workspaceApi.tasks,
  })
  const saved = tasks.data?.some(
    (t) => t.source_analysis_id === analysisId && t.source_index === index,
  )
  const mutation = useMutation({
    mutationFn: () => workspaceApi.analysisTask(analysisId, index),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['preparation-tasks'] })
      toast.success('Added to your preparation plan', {
        description: 'Find it on Today. You can complete it when you’re ready.',
      })
    },
    onError: () => toast.error('Could not add this task. Please try again.'),
  })
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="mt-3"
      disabled={saved || mutation.isPending || tasks.isPending}
      onClick={() => mutation.mutate()}
    >
      {saved ? <Check /> : <ListPlus />}
      {saved ? 'In your plan' : mutation.isPending ? 'Adding…' : 'Add to plan'}
    </Button>
  )
}

export function SaveAnalyzedRole({ analysis }: { analysis: JobMatchAnalysis }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [company, setCompany] = useState(analysis.company_name ?? '')
  const [role, setRole] = useState(analysis.job_title ?? '')
  const [saved, setSaved] = useState(false)
  const create = useMutation({
    mutationFn: () =>
      workspaceApi.createApplication({
        company_name: company.trim(),
        role: role.trim(),
        stage: 'Saved',
        deadline: null,
        next_action: 'Review resume gaps and prepare this application',
        notes: analysis.summary,
        is_pinned: false,
        resume_id: analysis.resume_id,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['applications'] })
      setSaved(true)
      setEditing(false)
      toast.success('Role saved to Applications', {
        description: 'Your analyzed resume is attached.',
      })
    },
    onError: () =>
      toast.error('Could not save the role. Your draft is still here.'),
  })
  return (
    <div className="mt-5 border-t border-[var(--border)] pt-4">
      {!editing ? (
        <Button
          variant="outline"
          size="sm"
          disabled={saved}
          onClick={() => setEditing(true)}
        >
          {saved ? <Check /> : <BriefcaseBusiness />}
          {saved ? 'Saved to Applications' : 'Track this opportunity'}
        </Button>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate()
          }}
          className="space-y-3"
        >
          <p className="text-xs text-[var(--text-secondary)]">
            Review the extracted details before saving. Your resume will be
            attached.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="field-label">
              Company
              <Input
                required
                maxLength={160}
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </label>
            <label className="field-label">
              Role
              <Input
                required
                maxLength={160}
                value={role}
                onChange={(e) => setRole(e.target.value)}
              />
            </label>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              type="submit"
              disabled={create.isPending || !company.trim() || !role.trim()}
            >
              <Plus />
              {create.isPending ? 'Saving…' : 'Save opportunity'}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={create.isPending}
              onClick={() => setEditing(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
