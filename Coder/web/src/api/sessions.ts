import { api } from './client'
import type { Session, Message } from '../types'

export async function listSessions(courseId?: string): Promise<Session[]> {
  const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : ''
  const data = await api.get<{ sessions: Session[] }>(`/sessions/${query}`)
  return data.sessions
}

export async function createSession(title?: string, courseId?: string): Promise<Session> {
  const body: Record<string, string> = {}
  if (title) body.title = title
  if (courseId) body.course_id = courseId
  return api.post<Session>('/sessions/', body)
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const data = await api.get<{ messages: Message[] }>(`/sessions/${sessionId}/messages`)
  return data.messages
}

export async function deleteSession(sessionId: string) {
  return api.del(`/sessions/${sessionId}`)
}
