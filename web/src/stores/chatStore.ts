import { create } from 'zustand'
import type { Message, Session, NavPage } from '../types'
import * as sessionsApi from '../api/sessions'

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null
  messages: Message[]
  streaming: boolean
  navPage: NavPage

  loadSessions: () => Promise<void>
  createSession: () => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  addUserMessage: (content: string) => void
  appendAssistantPart: (part: Message['parts'] extends (infer T)[] | undefined ? T : never) => void
  finalizeAssistantMessage: () => void
  setStreaming: (v: boolean) => void
  setNavPage: (page: NavPage) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  streaming: false,
  navPage: 'chat',

  async loadSessions() {
    const sessions = await sessionsApi.listSessions()
    set({ sessions })
  },

  async createSession() {
    const session = await sessionsApi.createSession()
    set((s) => ({
      sessions: [session, ...s.sessions],
      currentSessionId: session.session_id,
      messages: [],
    }))
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
      return { messages: msgs }
    })
  },

  finalizeAssistantMessage() {
    // no-op: message is already finalized through appendAssistantPart
  },

  setStreaming(v) {
    set({ streaming: v })
  },

  setNavPage(page) {
    set({ navPage: page })
  },
}))
