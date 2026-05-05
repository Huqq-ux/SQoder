import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { AgentInfo, MultiAgentResult, MultiAgentHistoryItem } from '../types'

type Tab = 'overview' | 'execute' | 'agents' | 'history'

export function MultiAgentPage() {
  const [tab, setTab] = useState<Tab>('overview')
  const [initialized, setInitialized] = useState(false)
  const [agentCount, setAgentCount] = useState(0)
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [history, setHistory] = useState<MultiAgentHistoryItem[]>([])
  const [task, setTask] = useState('')
  const [processType, setProcessType] = useState('hierarchical')
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<MultiAgentResult | null>(null)
  const [addName, setAddName] = useState('')
  const [addRole, setAddRole] = useState('coder')
  const [addMsg, setAddMsg] = useState('')

  const loadStatus = useCallback(async () => {
    const data = await api.get<{ initialized: boolean; agent_count: number }>('/multi-agent/status')
    setInitialized(data.initialized)
    setAgentCount(data.agent_count)
  }, [])

  const loadAgents = useCallback(async () => {
    const data = await api.get<{ agents: AgentInfo[] }>('/multi-agent/agents')
    setAgents(data.agents)
  }, [])

  const loadHistory = useCallback(async () => {
    const data = await api.get<{ history: MultiAgentHistoryItem[] }>('/multi-agent/history')
    setHistory(data.history)
  }, [])

  useEffect(() => {
    loadStatus()
    loadAgents()
    loadHistory()
  }, [loadStatus, loadAgents, loadHistory])

  const handleExecute = async () => {
    if (!task.trim()) return
    setExecuting(true)
    setResult(null)
    try {
      const data = await api.post<MultiAgentResult>('/multi-agent/execute', {
        task: task.trim(),
        process_type: processType,
      })
      setResult(data)
      loadHistory()
    } catch (e) {
      setResult({ success: false, result: null, error: String(e), duration_seconds: 0, agent_traces: [], sub_results: [] })
    } finally {
      setExecuting(false)
    }
  }

  const handleAddAgent = async () => {
    if (!addName.trim()) return
    try {
      await api.post('/multi-agent/add-agent', {
        name: addName.trim(),
        role: addRole,
        custom_prompt: '',
      })
      setAddMsg(`Agent "${addName}" 已添加`)
      setAddName('')
      loadAgents()
      loadStatus()
    } catch (e) {
      setAddMsg(`错误: ${e}`)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>🤖 多智能体系统</h2>
      </div>

      <div className="tabs">
        {(['overview', 'execute', 'agents', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {{ overview: '概览', execute: '执行任务', agents: 'Agent 管理', history: '执行历史' }[t]}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          <div className="metrics-row">
            <div className="metric">
              <div className="metric-value">{initialized ? '✅' : '❌'}</div>
              <div className="metric-label">系统状态</div>
            </div>
            <div className="metric">
              <div className="metric-value">{agentCount}</div>
              <div className="metric-label">Agent 数量</div>
            </div>
            <div className="metric">
              <div className="metric-value">{history.length}</div>
              <div className="metric-label">执行历史</div>
            </div>
          </div>
          <div className="card">
            <h3>活跃 Agent</h3>
            {agents.length === 0 ? (
              <div className="empty-state"><p>暂无 Agent</p></div>
            ) : (
              <div className="grid-2">
                {agents.map((a) => (
                  <div key={a.name} className="card" style={{ padding: 14 }}>
                    <h3>{a.name}</h3>
                    <div className="tag">{a.role}</div>
                    <div className="tag">{a.status}</div>
                    <div style={{ marginTop: 6 }}>
                      {a.capabilities.map((c) => (
                        <span key={c} className="tag">{c}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {tab === 'execute' && (
        <div className="card">
          <h3>执行任务</h3>
          <div className="form-group">
            <label>任务描述</label>
            <textarea
              rows={3}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="描述你的任务，AI 将自动分配 Agent 执行..."
            />
          </div>
          <div className="form-group">
            <label>执行模式</label>
            <select value={processType} onChange={(e) => setProcessType(e.target.value)}>
              <option value="hierarchical">层级式 (Supervisor 调度)</option>
              <option value="sequential">顺序式 (逐个执行)</option>
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleExecute}
            disabled={!task.trim() || executing}
          >
            {executing ? '执行中...' : '🚀 执行任务'}
          </button>

          {result && (
            <div style={{ marginTop: 20 }}>
              <div className={`alert ${result.success ? 'alert-success' : 'alert-error'}`}>
                {result.success ? `✅ 任务执行成功 (耗时: ${result.duration_seconds?.toFixed(1)}s)` : `❌ 任务执行失败: ${result.error}`}
              </div>
              {result.agent_traces && result.agent_traces.length > 0 && (
                <div className="alert alert-info">
                  <strong>Agent 调用链路:</strong> {result.agent_traces.join(' → ')}
                </div>
              )}
              {(() => {
                const r = result.result
                if (r === null || r === undefined) return null
                const text = typeof r === 'string' ? r : JSON.stringify(r, null, 2)
                return (
                  <div className="card">
                    <h3>执行结果</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{text}</pre>
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      )}

      {tab === 'agents' && (
        <div>
          <div className="card">
            <h3>添加 Agent</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Agent 名称</label>
                <input
                  type="text"
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  placeholder="coder / searcher / ops ..."
                />
              </div>
              <div className="form-group">
                <label>角色</label>
                <select value={addRole} onChange={(e) => setAddRole(e.target.value)}>
                  <option value="coder">Coder</option>
                  <option value="searcher">Searcher</option>
                  <option value="ops">Ops</option>
                  <option value="sop_executor">SOP Executor</option>
                  <option value="skill_executor">Skill Executor</option>
                </select>
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleAddAgent}>
              添加 Agent
            </button>
            {addMsg && (
              <div className={`alert ${addMsg.startsWith('错误') ? 'alert-error' : 'alert-success'}`} style={{ marginTop: 12 }}>
                {addMsg}
              </div>
            )}
          </div>

          <div className="card">
            <h3>已注册 Agent ({agents.length})</h3>
            {agents.map((a) => (
              <div key={a.name} style={{ marginBottom: 12, padding: 12, border: '1px solid var(--color-border)', borderRadius: 'var(--radius)' }}>
                <strong>{a.name}</strong>
                <span className="tag" style={{ marginLeft: 8 }}>{a.role}</span>
                <span className="tag">{a.status}</span>
                <div style={{ marginTop: 4 }}>
                  {a.capabilities.map((c) => <span key={c} className="tag">{c}</span>)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div className="card">
          <h3>执行历史</h3>
          {history.length === 0 ? (
            <div className="empty-state"><p>暂无执行记录</p></div>
          ) : (
            history.map((r, i) => (
              <div key={i} className={`alert ${r.success ? 'alert-success' : 'alert-error'}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{r.success ? '✅' : '❌'} 第 {history.length - i} 次执行</span>
                  <span>{r.duration_seconds?.toFixed(1)}s</span>
                </div>
                {r.agent_traces && r.agent_traces.length > 0 && (
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    链路: {r.agent_traces.join(' → ')}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
