import { useEffect, useRef } from 'react'
import type { Message } from '@/types'
import { ChatMessage } from '@/components/ChatMessage'
import { EmptyState } from '@/components/shared/EmptyState'
import { MessageSquare, AlertTriangle } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  streaming: boolean
  insideCourse?: boolean
}

export function MessageList({ messages, streaming, insideCourse }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0 && !streaming) {
    return (
      <EmptyState
        icon={MessageSquare}
        title={insideCourse ? '基于课程教材提问，获得精准回答' : '输入你的问题开始对话'}
        description={insideCourse ? '回答将标注引用自哪本教材、哪个章节' : '当前为通用对话模式，回答不基于课程教材'}
      />
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 space-y-6">
      {!insideCourse && messages.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px]" style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          当前对话未关联课程，AI 回答基于通用知识。选择一个课程可获得基于教材的精准回答。
        </div>
      )}

      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex gap-2.5 max-w-[85%] animate-fade-in-up ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          style={{ animationDelay: `${Math.min(i * 50, 1000)}ms` }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-xs shrink-0"
            style={{
              background: msg.role === 'user'
                ? 'var(--card)'
                : 'linear-gradient(135deg, var(--brand), var(--gradient-to))',
            }}
          >
            {msg.role === 'user' ? '👤' : '✨'}
          </div>
          <div
            className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed"
            style={{
              background: msg.role === 'user'
                ? 'transparent'
                : 'var(--card)',
              backgroundImage: msg.role === 'user'
                ? 'var(--user-bubble-bg)'
                : 'none',
              border: msg.role === 'user'
                ? '1px solid var(--user-bubble-border)'
                : '1px solid var(--border)',
              borderTopRightRadius: msg.role === 'user' ? '4px' : undefined,
              borderTopLeftRadius: msg.role === 'assistant' ? '4px' : undefined,
              color: 'var(--text)',
            }}
          >
            {msg.role === 'user' ? (
              <p>{msg.content}</p>
            ) : (
              <ChatMessage parts={msg.parts} />
            )}
          </div>
        </div>
      ))}

      {streaming && (
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--accent-glow)' }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--accent-glow)' }} />
          CourseMate 正在回答...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
