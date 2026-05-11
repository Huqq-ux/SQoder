import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatPart } from '../types'

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

  const toolParts: ChatPart[] = []
  const contentParts: ChatPart[] = []
  const errorParts: ChatPart[] = []

  for (const p of merged) {
    if (p.type === 'content') {
      contentParts.push(p)
    } else if (p.type === 'error') {
      errorParts.push(p)
    } else if (p.type === 'tool_call' || p.type === 'tool_result') {
      toolParts.push(p)
    }
  }

  return (
    <div>
      {contentParts.map((part, i) => (
        <div key={i} className="msg-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {part.content || ''}
          </ReactMarkdown>
        </div>
      ))}

      {errorParts.map((part, i) => (
        <div key={i} className="alert alert-error">
          ❌ {part.content}
        </div>
      ))}

      {toolParts.length > 0 && (
        <details className="tool-summary">
          <summary>🔧 {toolParts.length} 次工具调用</summary>
          {toolParts.map((part, i) => (
            part.type === 'tool_call' ? (
              <div key={i} className="tool-item tool-call-item">
                <span className="tool-tag">调用</span>
                <code>{part.name}</code>
                {part.args && <pre className="tool-detail">{part.args}</pre>}
              </div>
            ) : (
              <div key={i} className="tool-item tool-result-item">
                <span className="tool-tag">结果</span>
                <code>{part.name}</code>
                <pre className="tool-detail">{part.content}</pre>
              </div>
            )
          ))}
        </details>
      )}
    </div>
  )
}
