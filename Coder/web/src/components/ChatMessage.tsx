import type { ChatPart } from '../types'
import { ToolCallAccordion } from './chat/ToolCallAccordion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText } from 'lucide-react'

export function ChatMessage({ parts }: { parts?: ChatPart[] }) {
  if (!parts || parts.length === 0) {
    return <span className="text-sm italic" style={{ color: 'var(--text-dim)' }}>空回复</span>
  }

  return (
    <div className="space-y-2">
      {parts.map((p, i) => {
        if (p.type === 'content' && p.content) {
          return (
            <div key={i} className="prose prose-sm max-w-none" style={{ color: 'var(--text)' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {p.content}
              </ReactMarkdown>
            </div>
          )
        }
        if (p.type === 'tool_call') {
          return <ToolCallAccordion key={i} name={p.name || ''} args={p.args || ''} />
        }
        if (p.type === 'tool_result' && p.content) {
          // Show citations for RAG search results
          const citationKeywords = ['retrieve', 'search', 'knowledge', 'rag', 'course']
          const isCitation = p.name && citationKeywords.some(k => p.name?.toLowerCase().includes(k))
          if (isCitation) {
            try {
              const data = JSON.parse(p.content)
              const refs = Array.isArray(data) ? data : (data.results || [])
              if (refs.length > 0) {
                return (
                  <div key={i} className="flex flex-col gap-1">
                    {refs.slice(0, 3).map((ref: any, j: number) => (
                      <div
                        key={j}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px]"
                        style={{ background: 'var(--brand-bg-light)', color: 'var(--accent-glow)' }}
                      >
                        <FileText className="h-3 w-3 shrink-0" />
                        <span>{ref.metadata?.filename || ref.filename || ref.source || '课程教材'}</span>
                        {ref.metadata?.section && (
                          <span style={{ color: 'var(--text-dim)' }}>· {ref.metadata.section}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )
              }
            } catch { /* not JSON, skip citation display */ }
          }
          return null // Hide non-citation tool results
        }
        if (p.type === 'error') {
          return (
            <div key={i} className="text-sm p-2 rounded-lg" style={{ color: 'var(--red)', background: 'rgba(239,68,68,.08)' }}>
              {p.content}
            </div>
          )
        }
        return null
      })}
    </div>
  )
}
