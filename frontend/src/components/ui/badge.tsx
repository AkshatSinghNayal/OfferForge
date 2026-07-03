import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-xl border px-2.5 py-0.5 text-xs font-semibold transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-[var(--accent)] text-white',
        secondary:
          'border-transparent bg-[var(--card)] text-[var(--text-secondary)] border-[var(--border)]',
        success:
          'border-transparent bg-[var(--success)]/20 text-[var(--success)]',
        warning:
          'border-transparent bg-[var(--warning)]/20 text-[var(--warning)]',
        destructive:
          'border-transparent bg-[var(--danger)]/20 text-[var(--danger)]',
        outline:
          'border-[var(--border)] text-[var(--text-primary)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
