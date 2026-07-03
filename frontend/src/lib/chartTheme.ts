/**
 * Chart color helpers — all values are resolved from CSS custom properties
 * at runtime so they automatically follow the active theme (dark/light).
 *
 * Never use hard-coded hex values in chart configs; always call these
 * helpers or use the CSS variable name strings directly.
 */

/** Resolve a CSS custom property value from the document root. */
export function cssVar(name: string): string {
  if (typeof window === 'undefined') return '#000'
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** Standard chart palette using design tokens. */
export function chartColors() {
  return {
    accent: cssVar('--accent'),
    success: cssVar('--success'),
    warning: cssVar('--warning'),
    danger: cssVar('--danger'),
    muted: cssVar('--text-muted'),
    border: cssVar('--border'),
    card: cssVar('--card'),
    bg: cssVar('--bg'),
    textPrimary: cssVar('--text-primary'),
    textSecondary: cssVar('--text-secondary'),
    // Muted variants for secondary series
    accentMuted: cssVar('--accent') + '60',  // ~38% opacity via hex suffix
    successMuted: cssVar('--success') + '40',
    warningMuted: cssVar('--warning') + '40',
  }
}

/** A consistent sequence of colors for multi-series charts. */
export const CHART_SEQUENCE = [
  'var(--accent)',
  'var(--success)',
  'var(--warning)',
  'var(--danger)',
]

/** Recharts tooltip content wrapper style — uses design tokens. */
export const TOOLTIP_STYLE = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '12px',
  color: 'var(--text-primary)',
  fontSize: '12px',
}

/** Recharts axis tick style. */
export const AXIS_TICK_STYLE = {
  fill: 'var(--text-muted)',
  fontSize: 11,
}
