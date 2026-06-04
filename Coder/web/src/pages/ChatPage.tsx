import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { streamChat, stopGeneration } from '../api/chat'
import { ChatInput } from '../components/chat/ChatInput'
import { MessageList } from '../components/chat/MessageList'
import { CanvasPanel } from '../components/chat/CanvasPanel'
import { PanelRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ChatPage() {
  const messages = useChatStore((s) => s.messages)
  const streaming = useChatStore((s) => s.streaming)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const addUserMessage = useChatStore((s) => s.addUserMessage)
  const appendAssistantPart = useChatStore((s) => s.appendAssistantPart)
  const createSession = useChatStore((s) => s.createSession)
  const canvasOpen = useChatStore((s) => s.canvasOpen)
  const setCanvasOpen = useChatStore((s) => s.setCanvasOpen)

  const [input, setInput] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!currentSessionId) createSession()
  }, [currentSessionId, createSession])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming || !currentSessionId) return
    setInput('')
    addUserMessage(text)

    const controller = new AbortController()
    abortRef.current = controller
    setStreaming(true)

    try {
      for await (const event of streamChat(
        text,
        currentSessionId,
        controller.signal
      )) {
        appendAssistantPart(event)
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        appendAssistantPart({
          type: 'content',
          content: '\n\n[回答已停止]',
        })
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
    if (currentSessionId) await stopGeneration(currentSessionId)
    setStreaming(false)
  }

  return (
    <div className="absolute inset-0 flex">
      <div className="flex-1 flex flex-col p-6">
        <MessageList messages={messages} streaming={streaming} />
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onStop={handleStop}
          streaming={streaming}
        />
      </div>

      {!canvasOpen && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
          onClick={() => setCanvasOpen(true)}
        >
          <PanelRight className="h-4 w-4" />
        </Button>
      )}

      <CanvasPanel />
    </div>
  )
}
