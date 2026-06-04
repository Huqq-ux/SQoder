import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatPart } from '../types'
import { ToolCallAccordion } from './chat/ToolCallAccordion'

function mergeParts(parts: ChatPart[]): ChatPart[] {
  const merged: ChatPart[] = []
  for (const p of parts) {
    if (!merged.length) {
      merged.push({ ...p })
      continue
    }
    const last = merged[merged.length - 1]
    if (p.type === 'content' && last.type === 'content') {
      last.content = (last.content || '') + (p.content || '')
    } else {
      merged.push({ ...p })
    }
  }
  return merged
}

export function ChatMessage({ parts }: { parts?: ChatPart[] }) {
  if (!parts || parts.length === 0) return null

  const merged = mergeParts(parts)
  const contentParts = merged.filter((p) => p.type === 'content')
  const errorParts = merged.filter((p) => p.type === 'error')
  const toolParts = merged.filter(
    (p) => p.type === 'tool_call' || p.type === 'tool_result'
  )
  const text = contentParts.map((p) => p.content || '').join('')

  return (
    <div>
      {text && (
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
        </div>
      )}

      {errorParts.map((part, i) => (
        <div
          key={i}
          className="mt-2 px-3 py-2 rounded-lg border border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-400 text-xs"
        >
          {part.content}
        </div>
      ))}

      {toolParts.length > 0 && <ToolCallAccordion parts={toolParts} />}
    </div>
  )
}
