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
    } else if (p.type === 'thinking' && last.type === 'thinking') {
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

  return (
    <div>
      {merged.map((part, i) => {
        switch (part.type) {
          case 'thinking':
            return (
              <div key={i} className="thinking-block">
                <details>
                  <summary>💭 思考过程</summary>
                  <pre>{part.content}</pre>
                </details>
              </div>
            )

          case 'tool_call':
            return (
              <div key={i} className="tool-call">
                🔧 <strong>调用工具</strong>: <code>{part.name}</code>
                {part.args && <div>📋 参数: {part.args}</div>}
              </div>
            )

          case 'tool_result':
            return (
              <div key={i} className="tool-result">
                <details>
                  <summary>📤 工具结果 - {part.name}</summary>
                  <pre>{part.content}</pre>
                </details>
              </div>
            )

          case 'error':
            return (
              <div key={i} className="alert alert-error">
                ❌ {part.content}
              </div>
            )

          case 'content':
            return (
              <div key={i} className="msg-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {part.content || ''}
                </ReactMarkdown>
              </div>
            )

          default:
            return null
        }
      })}
    </div>
  )
}
