import { create } from 'zustand'
import type { Message, Session } from '../types'
import * as sessionsApi from '../api/sessions'

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null
  messages: Message[]
  streaming: boolean
  _creatingSession: boolean

  loadSessions: (courseId?: string) => Promise<void>
  createSession: (courseId?: string) => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  addUserMessage: (content: string) => void
  appendAssistantPart: (part: Message['parts'] extends (infer T)[] | undefined ? T : never) => void
  finalizeAssistantMessage: () => void
  setStreaming: (v: boolean) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  streaming: false,
  _creatingSession: false,

  async loadSessions(courseId?: string) {
    const sessions = await sessionsApi.listSessions(courseId)
    set({ sessions })
  },

  async createSession(courseId?: string) {
    if (get()._creatingSession) return
    set({ _creatingSession: true })
    try {
      const session = await sessionsApi.createSession(undefined, courseId)
      set((s) => ({
        sessions: [session, ...s.sessions],
        currentSessionId: session.session_id,
        messages: [],
      }))
    } finally {
      set({ _creatingSession: false })
    }
  },

  async switchSession(id: string) {
    set({ currentSessionId: id, messages: [] })
    try {
      const messages = await sessionsApi.getMessages(id)
      set({ messages })
    } catch {
      set({ messages: [] })
    }
  },

  async deleteSession(id: string) {
    await sessionsApi.deleteSession(id)
    const state = get()
    const sessions = state.sessions.filter((ss) => ss.session_id !== id)
    const switched = state.currentSessionId === id
    const nextId = switched ? (sessions[0]?.session_id ?? null) : state.currentSessionId

    set({ sessions, currentSessionId: nextId, messages: switched ? [] : state.messages })

    // 如果切到了其他会话，加载其历史消息
    if (switched && nextId) {
      try {
        const messages = await sessionsApi.getMessages(nextId)
        set({ messages })
      } catch {
        set({ messages: [] })
      }
    }

    // 如果所有会话都被删了，自动创建新会话
    if (switched && !nextId) {
      await get().createSession()
    }
  },

  addUserMessage(content: string) {
    set((s) => ({
      messages: [...s.messages, { role: 'user', content }],
    }))
  },

  appendAssistantPart(part) {
    // Skip thinking and tool_call — user doesn't need to see every tool invocation
    if (part.type === 'thinking' || part.type === 'tool_call') {
      return
    }
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        const parts = [...(last.parts || [])]

        // Merge consecutive content parts to avoid per-chunk line breaks
        if (part.type === 'content' && part.content) {
          const prevIdx = parts.length - 1
          if (prevIdx >= 0 && parts[prevIdx].type === 'content') {
            // Immutable update: replace the last content part
            parts[prevIdx] = {
              ...parts[prevIdx],
              content: (parts[prevIdx].content || '') + part.content,
            }
          } else {
            parts.push({ ...part })
          }
        } else {
          parts.push({ ...part })
        }

        const contentText = parts
          .filter((p) => p.type === 'content')
          .map((p) => p.content || '')
          .join('')
        msgs[msgs.length - 1] = { ...last, parts, content: contentText }
      } else {
        msgs.push({
          role: 'assistant',
          content: part.content || '',
          parts: part.type === 'content' ? [{ ...part }] : [],
        })
      }

      return { messages: msgs }
    })
  },

  finalizeAssistantMessage() {
    // no-op: message is already finalized through appendAssistantPart
  },

  setStreaming(v) {
    set({ streaming: v })
  },
}))
