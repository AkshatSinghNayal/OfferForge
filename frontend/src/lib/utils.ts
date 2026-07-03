import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Combines clsx + tailwind-merge for conflict-free class composition. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
