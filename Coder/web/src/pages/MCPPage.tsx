import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { MCPServer, MCPRegistryItem, MCPTool } from '../types'

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

  const [testResult, setTestResult] = useState<{ success: boolean; error: string; tools: MCPTool[] } | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  const [importMsg, setImportMsg] = useState('')

  const loadRegistry = useCallback(async () => {
    setRegistryLoading(true)
    try {
      const data = await api.get<{ servers: MCPRegistryItem[] }>(
        `/mcp/registry${registrySearch ? `?search=${encodeURIComponent(registrySearch)}` : ''}`
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
        `/mcp/servers/${server.id}/test`
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
      const data = await api.post<{ imported: number; skipped: number }>('/mcp/import', { config: parsed })
      setImportMsg(`Imported: ${data.imported}, Skipped: ${data.skipped}`)
      loadServers()
    } catch (e: any) {
      setImportMsg(`Import failed: ${e.message}`)
    }
  }

  return (
    <div className="mcp-page">
      <div className="page-header">
        <h2>MCP 管理</h2>
        <div className="tab-bar">
          <button
            className={`tab-btn ${tab === 'marketplace' ? 'active' : ''}`}
            onClick={() => setTab('marketplace')}
          >
            市场
          </button>
          <button
            className={`tab-btn ${tab === 'installed' ? 'active' : ''}`}
            onClick={() => setTab('installed')}
          >
            已安装
          </button>
        </div>
      </div>

      {tab === 'marketplace' && (
        <div className="mcp-marketplace">
          <div className="marketplace-toolbar">
            <input
              type="text"
              placeholder="搜索 MCP Server..."
              value={registrySearch}
              onChange={(e) => setRegistrySearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadRegistry()}
            />
            <button onClick={loadRegistry}>搜索</button>
          </div>
          {registryLoading ? (
            <p>加载中...</p>
          ) : registry.length === 0 ? (
            <p className="empty-hint">暂无可用 MCP Server</p>
          ) : (
            <div className="mcp-grid">
              {registry.map((item) => (
                <div key={item.id || item.name} className="mcp-card">
                  <h4>{item.name}</h4>
                  <p className="mcp-desc">{item.description}</p>
                  <span className="mcp-badge">{item.transport}</span>
                  {item.category && <span className="mcp-category">{item.category}</span>}
                  <button className="btn-primary" onClick={() => handleInstall(item)}>
                    安装
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'installed' && (
        <div className="mcp-installed">
          <div className="installed-toolbar">
            <button onClick={() => setShowAddForm(!showAddForm)}>
              {showAddForm ? '取消' : '＋ 手动添加'}
            </button>
            <button onClick={handleImportConfig}>导入配置</button>
            {importMsg && <span className="import-msg">{importMsg}</span>}
          </div>

          {showAddForm && (
            <div className="mcp-form">
              <label>
                Name:
                <input type="text" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </label>
              <label>
                Transport:
                <select value={formTransport} onChange={(e) => setFormTransport(e.target.value as 'stdio' | 'sse')}>
                  <option value="stdio">stdio</option>
                  <option value="sse">SSE</option>
                </select>
              </label>
              {formTransport === 'stdio' ? (
                <>
                  <label>
                    Command:
                    <input type="text" value={formCommand} onChange={(e) => setFormCommand(e.target.value)} placeholder="npx" />
                  </label>
                  <label>
                    Args (space-separated):
                    <input type="text" value={formArgs} onChange={(e) => setFormArgs(e.target.value)} placeholder="-y @scope/server" />
                  </label>
                </>
              ) : (
                <label>
                  URL:
                  <input type="text" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="https://..." />
                </label>
              )}
              {formError && <p className="form-error">{formError}</p>}
              <button onClick={handleAddManual} disabled={formSubmitting}>
                {formSubmitting ? '添加中...' : '添加'}
              </button>
            </div>
          )}

          {testing && <p>Testing {testing}...</p>}
          {testResult && (
            <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
              <p>{testResult.success ? 'Connection OK' : `Error: ${testResult.error}`}</p>
              {testResult.tools.length > 0 && (
                <ul>
                  {testResult.tools.map((t) => (
                    <li key={t.name}>{t.name}: {t.description}</li>
                  ))}
                </ul>
              )}
              <button onClick={() => setTestResult(null)}>关闭</button>
            </div>
          )}

          {serversLoading ? (
            <p>加载中...</p>
          ) : servers.length === 0 ? (
            <p className="empty-hint">暂无已安装的 MCP Server</p>
          ) : (
            <div className="mcp-server-list">
              {servers.map((s) => (
                <div key={s.id} className={`mcp-server-item status-${s.status}`}>
                  <div className="mcp-server-info">
                    <h4>{s.display_name}</h4>
                    <p>{s.description}</p>
                    <div className="mcp-server-meta">
                      <span className={`status-dot ${s.status}`} />
                      <span>{s.status}</span>
                      <span>{s.transport}</span>
                      <span>{s.tool_count} tools</span>
                    </div>
                    {s.last_error && <p className="mcp-error">Error: {s.last_error}</p>}
                  </div>
                  <div className="mcp-server-actions">
                    <button onClick={() => handleToggle(s)}>
                      {s.enabled ? '禁用' : '启用'}
                    </button>
                    <button onClick={() => handleTest(s)} disabled={testing === s.id}>
                      测试连接
                    </button>
                    {!s.is_local && (
                      <button className="btn-danger" onClick={() => handleDelete(s)}>
                        删除
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
