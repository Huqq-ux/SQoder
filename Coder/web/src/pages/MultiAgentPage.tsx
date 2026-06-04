import { useState } from 'react'
import { api } from '../api/client'
import type { OrchestratorResult } from '../types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle, XCircle } from 'lucide-react'

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
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-2 text-slate-900 dark:text-slate-100">智能任务协调者</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Agent-as-Tool 架构 — 专家智能体按需调用，自动协调
      </p>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="text-sm">执行任务</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            rows={3}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="描述你的任务，AI 将自动调用最适合的专家 Agent 执行..."
            className="text-sm resize-none"
          />
          <Button
            onClick={handleExecute}
            disabled={!task.trim() || executing}
            className="bg-blue-600 hover:bg-blue-500"
          >
            <Bot className="h-4 w-4 mr-2" />
            {executing ? '执行中...' : '执行任务'}
          </Button>

          {result && (
            <div className="mt-4 space-y-4">
              <div
                className={`flex items-center gap-2 text-sm ${
                  result.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                }`}
              >
                {result.success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {result.success
                  ? `执行成功 (耗时: ${result.duration_seconds.toFixed(1)}s)`
                  : `执行失败: ${result.error}`}
              </div>
              {result.answer && (
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {result.answer}
                    </p>
                  </CardContent>
                </Card>
              )}
              <div className="flex gap-2 flex-wrap">
                <Badge variant="secondary" className="text-[10px]">
                  Coder Agent
                </Badge>
                <Badge variant="secondary" className="text-[10px]">
                  Searcher Agent
                </Badge>
                <Badge variant="secondary" className="text-[10px]">
                  Ops Agent
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
