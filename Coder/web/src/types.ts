export interface ChatPart {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'content' | 'error' | 'done'
  content?: string
  name?: string
  args?: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  parts?: ChatPart[]
}

export interface Session {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  preview: string
}

export interface KnowledgeResult {
  content: string
  metadata: {
    filename: string
    section: string
    relevance_score: number
  }
}

export interface SkillMeta {
  name: string
  display_name: string
  description: string
  category: string
  tags: string[]
  version: string
  enabled: boolean
  author: string
  created_at: string
  updated_at: string
}

export interface OrchestratorResult {
  success: boolean
  answer: string
  error: string | null
  duration_seconds: number
}

export type NavPage = 'chat' | 'knowledge' | 'sop' | 'skills' | 'multi-agent'
