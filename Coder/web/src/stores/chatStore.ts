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

  loadSessions: () => Promise<void>
  createSession: () => Promise<void>
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

  async loadSessions() {
    const sessions = await sessionsApi.listSessions()
    set({ sessions })
  },

  async createSession() {
    if (get()._creatingSession) return
    set({ _creatingSession: true })
    try {
      const session = await sessionsApi.createSession()
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
    set((s) => {
      const sessions = s.sessions.filter((ss) => ss.session_id !== id)
      const currentSessionId = s.currentSessionId === id
        ? (sessions[0]?.session_id ?? null)
        : s.currentSessionId
      return { sessions, currentSessionId, messages: currentSessionId === id ? [] : s.messages }
    })
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
