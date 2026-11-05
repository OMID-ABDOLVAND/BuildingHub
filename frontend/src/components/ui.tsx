import clsx from 'clsx'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

export function cn(...parts: Array<string | false | null | undefined>) {
  return clsx(parts)
}

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:opacity-50',
        variant === 'primary' && 'bg-brand-700 text-white hover:bg-brand-800 shadow-sm',
        variant === 'secondary' && 'bg-white text-ink border border-line hover:bg-slate-50',
        variant === 'ghost' && 'text-muted hover:bg-slate-100',
        variant === 'danger' && 'bg-danger text-white hover:bg-red-700',
        className,
      )}
      {...props}
    />
  )
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'w-full rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100',
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'w-full rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100 min-h-28',
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        'w-full rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100',
        className,
      )}
      {...props}
    />
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1.5 block text-sm font-medium text-slate-700">{children}</label>
}

export function Card({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('rounded-2xl border border-line bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]', className)}>
      {children}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between animate-fade-up">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  )
}

export function Badge({
  children,
  tone = 'slate',
}: {
  children: ReactNode
  tone?: 'slate' | 'teal' | 'green' | 'amber' | 'red' | 'blue'
}) {
  const map = {
    slate: 'bg-slate-100 text-slate-700',
    teal: 'bg-teal-50 text-teal-800',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-800',
    red: 'bg-red-50 text-red-700',
    blue: 'bg-sky-50 text-sky-800',
  }
  return (
    <span className={cn('inline-flex rounded-lg px-2.5 py-1 text-xs font-medium', map[tone])}>
      {children}
    </span>
  )
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <Card className="animate-fade-up">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-2 text-xl font-bold text-ink">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-400">{hint}</div> : null}
    </Card>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-white px-6 py-14 text-center">
      <div className="text-base font-semibold text-ink">{title}</div>
      {description ? <p className="mt-2 text-sm text-muted">{description}</p> : null}
    </div>
  )
}

export function LoadingScreen({ label = 'در حال بارگذاری…' }: { label?: string }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-muted">
      <div className="flex items-center gap-3">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        {label}
      </div>
    </div>
  )
}

export const LoadingSpinner = LoadingScreen

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-white">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  )
}

export function Th({ children }: { children?: ReactNode }) {
  return (
    <th className="bg-slate-50 px-4 py-3 text-right font-medium text-slate-600 whitespace-nowrap">
      {children}
    </th>
  )
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={cn('border-t border-line px-4 py-3 align-middle', className)}>{children}</td>
}

export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-label="بستن" />
      <div className="relative z-10 w-full max-w-3xl rounded-2xl bg-white p-5 shadow-xl animate-fade-up">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold">{title}</h3>
          <button type="button" onClick={onClose} className="text-muted hover:text-ink">
            بستن
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}