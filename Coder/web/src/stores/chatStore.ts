import { create } from 'zustand'
import type { Message, Session } from '../types'
import * as sessionsApi from '../api/sessions'

interface CanvasContent {
  type: 'code' | 'tool'
  data: Record<string, unknown> | null
}

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null
  messages: Message[]
  streaming: boolean
  canvasOpen: boolean
  canvasContent: CanvasContent | null
  _creatingSession: boolean

  loadSessions: (courseId?: string) => Promise<void>
  createSession: (courseId?: string) => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  addUserMessage: (content: string) => void
  appendAssistantPart: (part: Message['parts'] extends (infer T)[] | undefined ? T : never) => void
  finalizeAssistantMessage: () => void
  setStreaming: (v: boolean) => void
  setCanvasOpen: (v: boolean) => void
  setCanvasContent: (c: CanvasContent | null) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  streaming: false,
  canvasOpen: false,
  canvasContent: null,
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
    if (part.type === 'thinking') {
      return
    }
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        const parts = [...(last.parts || []), part]
        const contentText = parts
          .filter((p) => p.type === 'content')
          .map((p) => p.content || '')
          .join('')
        msgs[msgs.length - 1] = { ...last, parts, content: contentText }
      } else {
        msgs.push({
          role: 'assistant',
          content: part.content || '',
          parts: [part],
        })
      }

      // Auto-open canvas on tool results with content
      if (part.type === 'tool_result' && part.content) {
        s.canvasOpen = true
        s.canvasContent = {
          type: 'code',
          data: { filename: part.name || 'output', content: part.content },
        }
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

  setCanvasOpen(v) {
    set({ canvasOpen: v })
  },

  setCanvasContent(c) {
    set({ canvasContent: c })
  },
}))
