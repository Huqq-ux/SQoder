import { api } from './client'
import type { MCPServer, MCPTool } from '../types'

export async function listServers(): Promise<MCPServer[]> {
  const data = await api.get<{ servers: MCPServer[] }>('/mcp/servers')
  return data.servers
}

export async function getServerTools(serverId: string): Promise<MCPTool[]> {
  const data = await api.get<{ tools: MCPTool[] }>(`/mcp/servers/${serverId}/tools`)
  return data.tools
}

export async function testServer(serverId: string): Promise<{ success: boolean; error: string; tools: MCPTool[] }> {
  return api.post(`/mcp/servers/${serverId}/test`)
}

export async function toggleServer(serverId: string, enabled: boolean): Promise<void> {
  await api.patch(`/mcp/servers/${serverId}`, { enabled })
}
