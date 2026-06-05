import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatPart } from '../types'
import { ToolCallAccordion } from './chat/ToolCallAccordion'
import { useDocxPreviewStore } from '../stores/docxPreviewStore'
import { FileText } from 'lucide-react'

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

function DocxPreviewButtons({ parts }: { parts: ChatPart[] }) {
  const open = useDocxPreviewStore((s) => s.open)

  // 从所有类型的 part 中提取 .docx 文件名（支持中文、路径）
  const allText = parts.map((p) => p.content || '').join(' ')
  const matches = allText.match(/([^\s\\\/:*?"<>|]+\.docx)/gi)
  if (!matches) return null
  const unique = [...new Set(matches)]

  return (
    <div className="flex gap-2 flex-wrap mt-2">
      {unique.map((fn) => (
        <button
          key={fn}
          onClick={() => open(fn)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
        >
          <FileText className="h-3.5 w-3.5" />
          预览 {fn}
        </button>
      ))}
    </div>
  )
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

      {merged.length > 0 && <DocxPreviewButtons parts={merged} />}

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
