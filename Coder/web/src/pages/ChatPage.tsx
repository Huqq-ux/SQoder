import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { streamChat, stopGeneration } from '../api/chat'
import { ChatInput } from '../components/chat/ChatInput'
import { MessageList } from '../components/chat/MessageList'

interface ChatPageProps {
  courseId?: string;
}

export function ChatPage({ courseId }: ChatPageProps = {}) {
  const messages = useChatStore((s) => s.messages)
  const streaming = useChatStore((s) => s.streaming)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const addUserMessage = useChatStore((s) => s.addUserMessage)
  const appendAssistantPart = useChatStore((s) => s.appendAssistantPart)
  const createSession = useChatStore((s) => s.createSession)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const switchSession = useChatStore((s) => s.switchSession)
  const [input, setInput] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const activeCourseRef = useRef(courseId)

  // Track course switches: if courseId changes, abort old stream and reset
  useEffect(() => {
    if (activeCourseRef.current !== courseId) {
      abortRef.current?.abort()
      useChatStore.setState({ messages: [], streaming: false })
      activeCourseRef.current = courseId
    }
  }, [courseId])

  useEffect(() => {
    ;(async () => {
      await loadSessions(courseId)
      const state = useChatStore.getState()
      // If we already have messages for this course (came back mid-conversation), keep them
      if (state.messages.length > 0) return
      // Otherwise load the most recent session
      if (state.sessions.length > 0) {
        await switchSession(state.sessions[0].session_id)
      } else {
        await createSession(courseId)
      }
    })()
  }, [loadSessions, switchSession, createSession, courseId])

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
        controller.signal,
        courseId,
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
      loadSessions()
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
        <MessageList messages={messages} streaming={streaming} insideCourse={!!courseId} />
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onStop={handleStop}
          streaming={streaming}
        />
      </div>

    </div>
  )
}
