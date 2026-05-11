import { useRef, useState, useEffect, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { streamChat, stopGeneration } from '../api/chat'
import { ChatMessage } from '../components/ChatMessage'

export function ChatPage() {
  const messages = useChatStore((s) => s.messages)
  const streaming = useChatStore((s) => s.streaming)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const addUserMessage = useChatStore((s) => s.addUserMessage)
  const appendAssistantPart = useChatStore((s) => s.appendAssistantPart)
  const createSession = useChatStore((s) => s.createSession)

  const [input, setInput] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    if (!currentSessionId) {
      createSession()
    }
  }, [currentSessionId, createSession])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming || !currentSessionId) return

    setInput('')
    addUserMessage(text)

    const controller = new AbortController()
    abortRef.current = controller
    setStreaming(true)

    try {
      for await (const event of streamChat(text, currentSessionId, controller.signal)) {
        appendAssistantPart(event)
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        appendAssistantPart({ type: 'content', content: '\n\n[回答已停止]' })
      } else {
        appendAssistantPart({ type: 'error', content: String(err) })
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleStop = async () => {
    abortRef.current?.abort()
    if (currentSessionId) {
      await stopGeneration(currentSessionId)
    }
    setStreaming(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h2>💬 AI 编程助手</h2>
        <div className="chat-subtitle">
          会话: {currentSessionId?.slice(0, 8) ?? 'N/A'} |
          消息: {messages.length} 条
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 && !streaming && (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <p>输入你的问题，AI 助手将为你提供帮助</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-role">
              {msg.role === 'user' ? '👤 用户' : '🤖 助手'}
            </div>
            {msg.role === 'assistant' ? (
              <ChatMessage parts={msg.parts} />
            ) : (
              <div className="msg-content">{msg.content}</div>
            )}
          </div>
        ))}

        {streaming && (
          <div className="streaming-indicator">
            <span className="pulse" />
            智能体正在生成回答...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
          disabled={streaming}
          rows={1}
        />
        {streaming ? (
          <button className="btn-stop" onClick={handleStop}>
            停止
          </button>
        ) : (
          <button
            className="btn-send"
            onClick={handleSend}
            disabled={!input.trim()}
          >
            发送
          </button>
        )}
      </div>
    </div>
  )
}
