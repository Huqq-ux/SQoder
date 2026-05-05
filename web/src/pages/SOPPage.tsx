import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface SOPStep {
  index: number
  name: string
  description: string
}

interface SOPDetail {
  name: string
  description: string
  steps: SOPStep[]
}

interface Checkpoint {
  sop_name: string
  saved_at: string
  [key: string]: unknown
}

type Tab = 'list' | 'create' | 'execute' | 'history'

export function SOPPage() {
  const [tab, setTab] = useState<Tab>('list')
  const [sopNames, setSopNames] = useState<string[]>([])
  const [status, setStatus] = useState({ knowledge_connected: false, sop_count: 0 })
  const [loading, setLoading] = useState(true)

  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [createSteps, setCreateSteps] = useState('步骤1: 检查环境\n步骤2: 准备资源\n步骤3: 执行操作\n步骤4: 验证结果')
  const [createMsg, setCreateMsg] = useState('')
  const [createErr, setCreateErr] = useState(false)

  const [selectedSOP, setSelectedSOP] = useState('')
  const [sopDetail, setSopDetail] = useState<SOPDetail | null>(null)
  const [execMsg, setExecMsg] = useState('')

  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([])

  const loadSOPs = useCallback(async () => {
    setLoading(true)
    try {
      const [listData, statusData] = await Promise.all([
        api.get<{ sop_names: string[]; count: number }>('/sop/list'),
        api.get<{ knowledge_connected: boolean; sop_count: number }>('/sop/status'),
      ])
      setSopNames(listData.sop_names)
      setStatus(statusData)
    } catch {
      setSopNames([])
    } finally {
      setLoading(false)
    }
  }, [])

  const loadCheckpoints = useCallback(async () => {
    try {
      const data = await api.get<{ checkpoints: Checkpoint[] }>('/sop/checkpoints/list')
      setCheckpoints(data.checkpoints || [])
    } catch {
      setCheckpoints([])
    }
  }, [])

  useEffect(() => {
    loadSOPs()
    loadCheckpoints()
  }, [loadSOPs, loadCheckpoints])

  const handleCreate = async () => {
    if (!createName.trim()) {
      setCreateMsg('请输入 SOP 名称')
      setCreateErr(true)
      return
    }

    const steps: SOPStep[] = []
    const lines = createSteps.trim().split('\n')
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      let name = `步骤${i + 1}`
      let desc = line
      const sep = line.includes(':') ? ':' : line.includes('：') ? '：' : null
      if (sep) {
        const parts = line.split(sep, 2)
        name = parts[0].trim()
        desc = parts[1]?.trim() || ''
      }
      steps.push({ index: i, name, description: desc })
    }

    if (steps.length === 0) {
      setCreateMsg('至少需要一个步骤')
      setCreateErr(true)
      return
    }

    try {
      await api.post('/sop/create', {
        name: createName.trim(),
        description: createDesc.trim(),
        steps,
      })
      setCreateMsg(`SOP "${createName}" 创建成功！共 ${steps.length} 个步骤`)
      setCreateErr(false)
      setCreateName('')
      setCreateDesc('')
      setCreateSteps('步骤1: 检查环境\n步骤2: 准备资源\n步骤3: 执行操作\n步骤4: 验证结果')
      loadSOPs()
    } catch (e: unknown) {
      const err = e as { message?: string; response?: { detail?: string } }
      setCreateMsg(err?.message || '创建失败')
      setCreateErr(true)
    }
  }

  const handleDelete = async (name: string) => {
    await api.del(`/sop/${name}`)
    loadSOPs()
  }

  const handleSelectForExec = async (name: string) => {
    setSelectedSOP(name)
    try {
      const detail = await api.get<SOPDetail>(`/sop/${name}`)
      setSopDetail(detail)
    } catch {
      setSopDetail(null)
    }
  }

  const handleExecute = async () => {
    if (!selectedSOP) return
    try {
      const result = await api.post<{ total_steps?: number }>(`/sop/${selectedSOP}/execute`, {})
      setExecMsg(`SOP "${selectedSOP}" 开始执行，共 ${result.total_steps ?? '?'} 个步骤。请切换到对话页面与智能体交互。`)
    } catch (e: unknown) {
      const err = e as { message?: string }
      setExecMsg(err?.message || '启动执行失败')
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>📋 SOP 管理</h2>
      </div>

      <div className="tabs">
        {(['list', 'create', 'execute', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {{ list: 'SOP 列表', create: '创建 SOP', execute: '执行 SOP', history: '执行历史' }[t]}
          </button>
        ))}
      </div>

      {loading && <div className="empty-state"><p>加载中...</p></div>}

      {/* Tab: list */}
      {!loading && tab === 'list' && (
        <>
          <div className="metrics-row">
            <div className="metric">
              <div className="metric-value">{status.sop_count}</div>
              <div className="metric-label">已注册 SOP</div>
            </div>
            <div className="metric">
              <div className="metric-value">{status.knowledge_connected ? '✅' : '❌'}</div>
              <div className="metric-label">知识库连接</div>
            </div>
          </div>

          {sopNames.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <p>暂无 SOP，请创建或上传知识库文档</p>
            </div>
          ) : (
            <div>
              {sopNames.map((name) => (
                <div key={name} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>{name}</strong>
                  </div>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(name)}>
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab: create */}
      {!loading && tab === 'create' && (
        <div className="card">
          <h3>创建新 SOP</h3>
          <div className="form-group">
            <label>SOP 名称</label>
            <input
              type="text"
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              placeholder="例如: 代码审查流程"
            />
          </div>
          <div className="form-group">
            <label>描述</label>
            <textarea
              rows={2}
              value={createDesc}
              onChange={(e) => setCreateDesc(e.target.value)}
              placeholder="SOP 的简要描述..."
            />
          </div>
          <div className="form-group">
            <label>步骤列表（每行一个步骤，格式：步骤名称: 步骤描述）</label>
            <textarea
              rows={8}
              value={createSteps}
              onChange={(e) => setCreateSteps(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
          </div>
          <button className="btn btn-primary" onClick={handleCreate}>
            创建 SOP
          </button>
          {createMsg && (
            <div className={`alert ${createErr ? 'alert-error' : 'alert-success'}`} style={{ marginTop: 12 }}>
              {createMsg}
            </div>
          )}
        </div>
      )}

      {/* Tab: execute */}
      {!loading && tab === 'execute' && (
        <div className="card">
          <h3>执行 SOP</h3>
          {sopNames.length === 0 ? (
            <div className="empty-state"><p>暂无可执行的 SOP</p></div>
          ) : (
            <>
              <div className="form-group">
                <label>选择 SOP</label>
                <select value={selectedSOP} onChange={(e) => handleSelectForExec(e.target.value)}>
                  <option value="">-- 请选择 --</option>
                  {sopNames.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>

              {sopDetail && sopDetail.steps && (
                <div style={{ marginBottom: 16 }}>
                  <h4>步骤预览</h4>
                  {sopDetail.steps.map((step) => (
                    <div key={step.index} className="alert alert-info">
                      <strong>{step.name}</strong>: {step.description?.slice(0, 100)}
                    </div>
                  ))}
                </div>
              )}

              {selectedSOP && (
                <button className="btn btn-primary" onClick={handleExecute}>
                  开始执行
                </button>
              )}

              {execMsg && (
                <div className="alert alert-success" style={{ marginTop: 12 }}>
                  {execMsg}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab: history */}
      {!loading && tab === 'history' && (
        <div className="card">
          <h3>执行历史</h3>
          {checkpoints.length === 0 ? (
            <div className="empty-state"><p>暂无执行历史</p></div>
          ) : (
            checkpoints.map((cp, i) => (
              <details key={i} style={{ marginBottom: 8 }}>
                <summary>{cp.sop_name} - {cp.saved_at || '未知时间'}</summary>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, marginTop: 8 }}>
                  {JSON.stringify(cp, null, 2)}
                </pre>
              </details>
            ))
          )}
        </div>
      )}
    </div>
  )
}
