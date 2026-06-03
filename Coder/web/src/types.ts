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

export type NavPage = 'chat' | 'knowledge' | 'sop' | 'skills' | 'multi-agent' | 'mcp'

export interface MCPServer {
  id: string
  name: string
  display_name: string
  description: string
  transport: 'stdio' | 'sse'
  command: string | null
  args: string[]
  url: string | null
  env: Record<string, string>
  enabled: boolean
  is_local: boolean
  source: 'manual' | 'registry' | 'builtin'
  registry_id: string | null
  tools_allowlist: string[] | null
  last_error: string | null
  tool_count: number
  status: 'connected' | 'error' | 'disabled'
  created_at: string
  updated_at: string
}

export interface MCPRegistryItem {
  id: string
  name: string
  description: string
  transport: 'stdio' | 'sse'
  command?: string
  args?: string[]
  url?: string
  category?: string
}

export interface MCPTool {
  name: string
  description: string
  args_schema: string
}
