import { useState } from 'react'
import { api } from '../api/client'
import type { OrchestratorResult, OrchestratorToolCall } from '../types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle, XCircle, Clock } from 'lucide-react'

export function MultiAgentPage() {
  const [task, setTask] = useState('')
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<OrchestratorResult | null>(null)
  const [streamContent, setStreamContent] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [toolCalls, setToolCalls] = useState<OrchestratorToolCall[]>([])
  const [useStream, setUseStream] = useState(true)

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
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0, tool_calls: [] })
    } finally {
      setExecuting(false)
    }
  }

  const handleStream = async () => {
    if (!task.trim()) return
    setStreaming(true)
    setResult(null)
    setStreamContent('')
    setToolCalls([])

    try {
      const res = await fetch('/api/agent-orchestrator/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task.trim() }),
      })
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''
      const toolCallMap = new Map<string, OrchestratorToolCall>()
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            switch (event.type) {
              case 'tool_call':
                toolCallMap.set(event.name, {
                  agent: event.name,
                  display_name: event.name,
                  task: typeof event.args === 'object' ? JSON.stringify(event.args) : String(event.args),
                  duration_ms: 0,
                  success: true,
                })
                setToolCalls([...toolCallMap.values()])
                break
              case 'tool_result':
                break
              case 'content':
                fullContent += event.content
                setStreamContent(fullContent)
                break
              case 'error':
                setResult({
                  success: false,
                  answer: '',
                  error: event.content,
                  duration_seconds: 0,
                  tool_calls: [...toolCallMap.values()],
                })
                break
              case 'done':
                setResult({
                  success: true,
                  answer: fullContent,
                  error: null,
                  duration_seconds: 0,
                  tool_calls: [...toolCallMap.values()],
                })
                break
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (e) {
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0, tool_calls: [] })
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-2 text-slate-900 dark:text-slate-100">智能任务协调者</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Agent-as-Tool — 专家智能体按需调用，自动协调
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
          <div className="flex items-center gap-4">
            <Button
              onClick={useStream ? handleStream : handleExecute}
              disabled={!task.trim() || executing || streaming}
              className="bg-blue-600 hover:bg-blue-500"
            >
              <Bot className="h-4 w-4 mr-2" />
              {executing || streaming ? '执行中...' : '执行任务'}
            </Button>
            <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
                className="rounded"
              />
              流式输出
            </label>
          </div>

          {(streaming || streamContent) && useStream && (
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {streamContent || '等待响应...'}
                </p>
              </CardContent>
            </Card>
          )}

          {result && !streaming && (
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
              {result.tool_calls.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {result.tool_calls.map((tc, i) => (
                    <Badge
                      key={i}
                      variant={tc.success ? 'secondary' : 'destructive'}
                      className="text-[10px] flex items-center gap-1"
                    >
                      {tc.success ? (
                        <CheckCircle className="h-3 w-3" />
                      ) : (
                        <XCircle className="h-3 w-3" />
                      )}
                      {tc.display_name}
                      <Clock className="h-3 w-3 ml-1" />
                      {(tc.duration_ms / 1000).toFixed(1)}s
                    </Badge>
                  ))}
                </div>
              )}
              {result.tool_calls.length === 0 && result.success && (
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-[10px]">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    编排器直接处理
                  </Badge>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
