import { useState } from 'react'
import { api } from '../api/client'
import type { OrchestratorResult } from '../types'

export function MultiAgentPage() {
  const [task, setTask] = useState('')
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<OrchestratorResult | null>(null)

  const handleExecute = async () => {
    if (!task.trim()) return
    setExecuting(true)
    setResult(null)
    try {
      const data = await api.post<OrchestratorResult>('/agent-orchestrator/execute', {
        task: task.trim(),
      })
      setResult(data)
    } catch (e) {
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0 })
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>🤖 智能任务协调者</h2>
        <p style={{ color: '#666', fontSize: 14, marginTop: 4 }}>
          Agent-as-Tool 架构 — 专家智能体按需调用，自动协调
        </p>
      </div>

      <div className="card">
        <h3>执行任务</h3>
        <div className="form-group">
          <label>任务描述</label>
          <textarea
            rows={3}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="描述你的任务，AI 将自动调用最适合的专家 Agent 执行..."
          />
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
              {result.success
                ? `✅ 任务执行成功 (耗时: ${result.duration_seconds?.toFixed(1)}s)`
                : `❌ 任务执行失败: ${result.error}`}
            </div>
            {result.answer && (
              <div className="card">
                <h3>📋 回答</h3>
                <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7 }}>
                  {result.answer}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
