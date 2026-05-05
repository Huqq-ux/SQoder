import { api } from './client'
import type { Session, Message } from '../types'

export async function listSessions(): Promise<Session[]> {
  const data = await api.get<{ sessions: Session[] }>('/sessions/')
  return data.sessions
}

export async function createSession(title?: string): Promise<Session> {
  return api.post<Session>('/sessions/', title ? { title } : {})
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const data = await api.get<{ messages: Message[] }>(`/sessions/${sessionId}/messages`)
  return data.messages
}

export async function deleteSession(sessionId: string) {
  return api.del(`/sessions/${sessionId}`)
}
