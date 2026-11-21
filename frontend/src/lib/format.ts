import { format, formatDistanceToNowStrict, isToday, isYesterday, parseISO } from 'date-fns'

/** Parse an API timestamp (UTC without a zone suffix) as UTC. */
export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`
  const date = parseISO(iso)
  return Number.isNaN(date.getTime()) ? null : date
}

export function relativeDate(value: string | null | undefined): string {
  const date = parseApiDate(value)
  if (!date) return 'never'
  if (isToday(date)) return `today, ${format(date, 'HH:mm')}`
  if (isYesterday(date)) return 'yesterday'
  return formatDistanceToNowStrict(date, { addSuffix: true })
}

export function shortDate(value: string | null | undefined): string {
  const date = parseApiDate(value)
  return date ? format(date, 'd MMM yyyy') : ''
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function duration(seconds: number | null | undefined): string {
  const s = Math.max(0, Math.round(seconds ?? 0))
  const m = Math.floor(s / 60)
  const r = s % 60
  if (m >= 60) return `${Math.floor(m / 60)}h ${m % 60}m`
  return m ? `${m}m ${r.toString().padStart(2, '0')}s` : `${r}s`
}

export function minutes(total: number): string {
  if (total < 60) return `${total}m`
  return `${Math.floor(total / 60)}h ${total % 60}m`
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}

export function pages(list: number[] | null | undefined): string {
  if (!list?.length) return ''
  const unique = Array.from(new Set(list)).sort((a, b) => a - b)
  if (unique.length === 1) return `Page ${unique[0]}`
  return `Pages ${unique[0]} to ${unique[unique.length - 1]}`
}

export const QUESTION_TYPE_LABEL: Record<string, string> = {
  mcq: 'Multiple choice',
  multi_select: 'Multiple answer',
  true_false: 'True or false',
  fill_blank: 'Fill in the blank',
  short_answer: 'Short answer',
  matching: 'Matching',
}

export const CARD_TYPE_LABEL: Record<string, string> = {
  basic: 'Question',
  definition: 'Definition',
  concept: 'Key idea',
  cloze: 'Fill the gap',
  process: 'Steps',
  formula: 'Formula',
  eli5: 'Plain words',
  diagram: 'Diagram',
}

export function initials(name?: string | null): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?'
}
