import type { ChatPart } from '../types'

const BASE = '/api'

export async function* streamChat(
  message: string,
  threadId: string,
  signal: AbortSignal,
): AsyncGenerator<ChatPart> {
  const response = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Chat stream failed: ${response.status}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ')) {
        const data = JSON.parse(trimmed.slice(6))
        if (data.type === 'done') return
        yield data as ChatPart
      }
    }
  }
}

export async function stopGeneration(threadId: string) {
  const res = await fetch(`${BASE}/chat/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId }),
  })
  return res.json()
}
