import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  className?: string
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 text-center ${className || ''}`}>
      {Icon && <Icon className="h-12 w-12 text-slate-700 mb-4" />}
      <h3 className="text-sm font-medium text-slate-400">{title}</h3>
      {description && <p className="text-xs text-slate-600 mt-1">{description}</p>}
    </div>
  )
}
