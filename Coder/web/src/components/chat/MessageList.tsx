import { useEffect, useRef } from 'react'
import type { Message } from '@/types'
import { ChatMessage } from '@/components/ChatMessage'
import { EmptyState } from '@/components/shared/EmptyState'
import { MessageSquare } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  streaming: boolean
}

export function MessageList({ messages, streaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0 && !streaming) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="输入你的问题，Qbot 将为你提供帮助"
        description="支持代码生成、知识库检索、多智能体协作"
      />
    )
  }

  return (
    <div className="flex-1 overflow-y-auto pr-4 space-y-6">
      {messages.map((msg, i) => (
        <div key={i} className={msg.role === 'user' ? 'flex justify-end' : ''}>
          {msg.role === 'user' ? (
            <div className="max-w-[75%] bg-blue-500/15 border border-blue-500/20 rounded-2xl rounded-br-md px-4 py-3">
              <p className="text-sm text-blue-50">{msg.content}</p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Qbot
              </p>
              <ChatMessage parts={msg.parts} />
            </div>
          )}
        </div>
      ))}

      {streaming && (
        <div className="flex items-center gap-2 text-sm text-blue-400">
          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
          Qbot 正在生成回答...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
