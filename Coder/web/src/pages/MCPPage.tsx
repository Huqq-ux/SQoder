import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { MCPServer, MCPRegistryItem, MCPTool } from '../types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { EmptyState } from '@/components/shared/EmptyState'
import { Plug, Search, Plus, Trash2, Power, PowerOff, RefreshCw } from 'lucide-react'

type Tab = 'marketplace' | 'installed'

export function MCPPage() {
  const [tab, setTab] = useState<Tab>('marketplace')
  const [registry, setRegistry] = useState<MCPRegistryItem[]>([])
  const [registryLoading, setRegistryLoading] = useState(true)
  const [registrySearch, setRegistrySearch] = useState('')

  const [servers, setServers] = useState<MCPServer[]>([])
  const [serversLoading, setServersLoading] = useState(true)

  const [showAddForm, setShowAddForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formTransport, setFormTransport] = useState<'stdio' | 'sse'>('stdio')
  const [formCommand, setFormCommand] = useState('')
  const [formArgs, setFormArgs] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [testResult, setTestResult] = useState<{
    success: boolean
    error: string
    tools: MCPTool[]
  } | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  const [importMsg, setImportMsg] = useState('')

  const loadRegistry = useCallback(async () => {
    setRegistryLoading(true)
    try {
      const data = await api.get<{ servers: MCPRegistryItem[] }>(
        `/mcp/registry${registrySearch ? `?search=${encodeURIComponent(registrySearch)}` : ''}`,
      )
      setRegistry(data.servers)
    } catch {
      setRegistry([])
    } finally {
      setRegistryLoading(false)
    }
  }, [registrySearch])

  const loadServers = useCallback(async () => {
    setServersLoading(true)
    try {
      const data = await api.get<{ servers: MCPServer[] }>('/mcp/servers')
      setServers(data.servers)
    } catch {
      setServers([])
    } finally {
      setServersLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === 'marketplace') loadRegistry()
    else loadServers()
  }, [tab, loadRegistry, loadServers])

  const handleInstall = async (item: MCPRegistryItem) => {
    try {
      await api.post('/mcp/servers', {
        name: item.name,
        display_name: item.name,
        description: item.description,
        transport: item.transport,
        command: item.command || null,
        args: item.args || [],
        url: item.url || null,
      })
      setTab('installed')
    } catch (e: any) {
      alert(`Install failed: ${e.message}`)
    }
  }

  const handleAddManual = async () => {
    if (!formName.trim()) {
      setFormError('Name is required')
      return
    }
    if (formTransport === 'stdio' && !formCommand.trim()) {
      setFormError('Command is required for stdio transport')
      return
    }
    if (formTransport === 'sse' && !formUrl.trim()) {
      setFormError('URL is required for SSE transport')
      return
    }

    setFormSubmitting(true)
    setFormError('')
    try {
      await api.post('/mcp/servers', {
        name: formName.trim(),
        display_name: formName.trim(),
        transport: formTransport,
        command: formTransport === 'stdio' ? formCommand.trim() : null,
        args: formArgs.trim() ? formArgs.trim().split(/\s+/) : [],
        url: formTransport === 'sse' ? formUrl.trim() : null,
      })
      setShowAddForm(false)
      setFormName('')
      setFormCommand('')
      setFormArgs('')
      setFormUrl('')
      setTab('installed')
    } catch (e: any) {
      setFormError(e.message)
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleToggle = async (server: MCPServer) => {
    await api.patch(`/mcp/servers/${server.id}`, { enabled: !server.enabled })
    loadServers()
  }

  const handleDelete = async (server: MCPServer) => {
    if (!confirm(`Delete "${server.display_name}"?`)) return
    await api.del(`/mcp/servers/${server.id}`)
    loadServers()
  }

  const handleTest = async (server: MCPServer) => {
    setTesting(server.id)
    try {
      const data = await api.post<{ success: boolean; error: string; tools: MCPTool[] }>(
        `/mcp/servers/${server.id}/test`,
      )
      setTestResult(data)
    } catch (e: any) {
      setTestResult({ success: false, error: e.message, tools: [] })
    } finally {
      setTesting(null)
    }
  }

  const handleImportConfig = async () => {
    const input = prompt('Paste Claude Desktop config JSON (the content of claude_desktop_config.json):')
    if (!input) return
    try {
      const parsed = JSON.parse(input)
      const data = await api.post<{ imported: number; skipped: number }>('/mcp/import', {
        config: parsed,
      })
      setImportMsg(`Imported: ${data.imported}, Skipped: ${data.skipped}`)
      loadServers()
    } catch (e: any) {
      setImportMsg(`Import failed: ${e.message}`)
    }
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-4">MCP 管理</h2>

      {/* Tab Bar */}
      <div className="flex items-center gap-2 mb-6 border-b border-slate-800">
        <button
          onClick={() => setTab('marketplace')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
            tab === 'marketplace'
              ? 'text-blue-400 border-blue-400'
              : 'text-slate-500 hover:text-slate-300 border-transparent'
          }`}
        >
          市场
        </button>
        <button
          onClick={() => setTab('installed')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
            tab === 'installed'
              ? 'text-blue-400 border-blue-400'
              : 'text-slate-500 hover:text-slate-300 border-transparent'
          }`}
        >
          已安装
        </button>
      </div>

      {/* Marketplace Tab */}
      {tab === 'marketplace' && (
        <div className="space-y-4">
          {/* Search bar */}
          <div className="flex gap-3">
            <Input
              value={registrySearch}
              onChange={(e) => setRegistrySearch(e.target.value)}
              placeholder="搜索 MCP Server..."
              className="flex-1 bg-slate-900 border-slate-700 text-sm"
              onKeyDown={(e) => e.key === 'Enter' && loadRegistry()}
            />
            <Button
              onClick={loadRegistry}
              className="bg-slate-700 hover:bg-slate-600"
            >
              <Search className="h-4 w-4 mr-2" />
              搜索
            </Button>
          </div>

          {registryLoading ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="h-4 w-4 animate-spin" />
              加载中...
            </div>
          ) : registry.length === 0 ? (
            <EmptyState
              icon={Plug}
              title="暂无可用 MCP Server"
              description="尝试搜索或手动添加"
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {registry.map((item) => (
                <Card
                  key={item.id || item.name}
                  className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <CardContent className="p-5 flex flex-col gap-3 h-full">
                    <div className="flex-1 space-y-2">
                      <h4 className="font-semibold text-sm text-slate-200">{item.name}</h4>
                      <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                        {item.description}
                      </p>
                      <div className="flex gap-2 flex-wrap">
                        <Badge variant="secondary" className="text-[10px]">
                          {item.transport}
                        </Badge>
                        {item.category && (
                          <Badge variant="outline" className="text-[10px] text-slate-400">
                            {item.category}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      onClick={() => handleInstall(item)}
                      size="sm"
                      className="bg-blue-600 hover:bg-blue-500 w-full mt-auto"
                    >
                      <Plus className="h-3.5 w-3.5 mr-1.5" />
                      安装
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Installed Tab */}
      {tab === 'installed' && (
        <div className="space-y-4">
          {/* Toolbar */}
          <div className="flex items-center gap-3">
            <Button
              onClick={() => setShowAddForm(!showAddForm)}
              className="bg-slate-700 hover:bg-slate-600"
            >
              <Plus className="h-4 w-4 mr-2" />
              {showAddForm ? '取消' : '手动添加'}
            </Button>
            <Button
              onClick={handleImportConfig}
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              导入配置
            </Button>
            {importMsg && (
              <span className="text-xs text-slate-400">{importMsg}</span>
            )}
          </div>

          {/* Add Form */}
          {showAddForm && (
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-5 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400">Name</label>
                  <Input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="my-mcp-server"
                    className="bg-slate-950 border-slate-700 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400">Transport</label>
                  <select
                    value={formTransport}
                    onChange={(e) => setFormTransport(e.target.value as 'stdio' | 'sse')}
                    className="w-full h-9 rounded-md bg-slate-950 border border-slate-700 text-sm text-slate-200 px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  >
                    <option value="stdio">stdio</option>
                    <option value="sse">SSE</option>
                  </select>
                </div>
                {formTransport === 'stdio' ? (
                  <>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-400">Command</label>
                      <Input
                        value={formCommand}
                        onChange={(e) => setFormCommand(e.target.value)}
                        placeholder="npx"
                        className="bg-slate-950 border-slate-700 text-sm"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-400">
                        Args (space-separated)
                      </label>
                      <Input
                        value={formArgs}
                        onChange={(e) => setFormArgs(e.target.value)}
                        placeholder="-y @scope/server"
                        className="bg-slate-950 border-slate-700 text-sm"
                      />
                    </div>
                  </>
                ) : (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400">URL</label>
                    <Input
                      value={formUrl}
                      onChange={(e) => setFormUrl(e.target.value)}
                      placeholder="https://..."
                      className="bg-slate-950 border-slate-700 text-sm"
                    />
                  </div>
                )}
                {formError && (
                  <p className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded-lg border border-red-500/20">
                    {formError}
                  </p>
                )}
                <Button
                  onClick={handleAddManual}
                  disabled={formSubmitting}
                  className="bg-blue-600 hover:bg-blue-500"
                >
                  {formSubmitting ? '添加中...' : '添加'}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Test progress */}
          {testing && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Testing {testing}...
            </div>
          )}

          {/* Test result */}
          {testResult && (
            <Card
              className={
                testResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/20'
                  : 'bg-red-500/10 border-red-500/20'
              }
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      testResult.success ? 'bg-emerald-400' : 'bg-red-400'
                    }`}
                  />
                  {testResult.success ? 'Connection OK' : `Error: ${testResult.error}`}
                </CardTitle>
              </CardHeader>
              {testResult.tools.length > 0 && (
                <CardContent className="pb-4">
                  <Separator className="mb-3 bg-slate-700/50" />
                  <ul className="space-y-1">
                    {testResult.tools.map((t) => (
                      <li key={t.name} className="text-xs text-slate-400">
                        <span className="text-slate-200 font-medium">{t.name}</span>
                        {t.description && `: ${t.description}`}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              )}
              <div className="px-5 pb-4">
                <Button
                  onClick={() => setTestResult(null)}
                  variant="outline"
                  size="sm"
                  className="border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  关闭
                </Button>
              </div>
            </Card>
          )}

          {/* Server list */}
          {serversLoading ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="h-4 w-4 animate-spin" />
              加载中...
            </div>
          ) : servers.length === 0 ? (
            <EmptyState
              icon={Plug}
              title="暂无已安装的 MCP Server"
              description="从市场安装或手动添加"
            />
          ) : (
            <div className="space-y-3">
              {servers.map((s) => (
                <Card
                  key={s.id}
                  className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-sm text-slate-200">
                            {s.display_name}
                          </h4>
                          <span
                            className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              s.status === 'connected'
                                ? 'bg-emerald-400'
                                : s.status === 'disabled'
                                ? 'bg-slate-600'
                                : 'bg-red-400'
                            }`}
                          />
                          <span className="text-[10px] text-slate-500">{s.status}</span>
                        </div>
                        {s.description && (
                          <p className="text-xs text-slate-400 line-clamp-2">{s.description}</p>
                        )}
                        <div className="flex gap-2 flex-wrap">
                          <Badge variant="secondary" className="text-[10px]">
                            {s.transport}
                          </Badge>
                          <Badge variant="secondary" className="text-[10px]">
                            {s.tool_count} tools
                          </Badge>
                        </div>
                        {s.last_error && (
                          <p className="text-xs text-red-400 bg-red-500/10 px-2 py-1 rounded">
                            Error: {s.last_error}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Button
                          onClick={() => handleToggle(s)}
                          size="sm"
                          variant="outline"
                          className="border-slate-700 text-slate-300 hover:bg-slate-800"
                        >
                          {s.enabled ? (
                            <PowerOff className="h-3.5 w-3.5" />
                          ) : (
                            <Power className="h-3.5 w-3.5" />
                          )}
                          <span className="ml-1.5">{s.enabled ? '禁用' : '启用'}</span>
                        </Button>
                        <Button
                          onClick={() => handleTest(s)}
                          disabled={testing === s.id}
                          size="sm"
                          variant="outline"
                          className="border-slate-700 text-slate-300 hover:bg-slate-800"
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5 ${testing === s.id ? 'animate-spin' : ''}`}
                          />
                          <span className="ml-1.5">测试连接</span>
                        </Button>
                        {!s.is_local && (
                          <Button
                            onClick={() => handleDelete(s)}
                            size="sm"
                            variant="outline"
                            className="border-red-800 text-red-400 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
