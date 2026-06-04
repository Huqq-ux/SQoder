import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import type { SkillMeta } from '../types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { EmptyState } from '@/components/shared/EmptyState'
import { Wrench } from 'lucide-react'

interface SkillUploadResult {
  status: string
  name: string
  display_name: string
  description: string
  category: string
  version: string
  tags: string[]
  parameters: { name: string; type: string; required: boolean; description: string }[]
  code_ok: boolean
  code_msg: string
  has_code: boolean
}

export function SkillsPage() {
  const [tab, setTab] = useState<'list' | 'upload'>('list')
  const [skills, setSkills] = useState<SkillMeta[]>([])
  const [loading, setLoading] = useState(true)

  const [mdFile, setMdFile] = useState<File | null>(null)
  const [mdUploading, setMdUploading] = useState(false)
  const [mdResult, setMdResult] = useState<SkillUploadResult | null>(null)
  const [mdError, setMdError] = useState('')
  const uploadFormRef = useRef<HTMLFormElement>(null)

  const [jsonInput, setJsonInput] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')
  const [uploadErr, setUploadErr] = useState(false)

  const [detailSkill, setDetailSkill] = useState<Record<string, unknown> | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const loadSkills = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ skills: SkillMeta[] }>('/skills/')
      setSkills(data.skills)
    } catch {
      setSkills([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSkills()
  }, [loadSkills])

  const handleMdUpload = async () => {
    if (!mdFile) return
    setMdUploading(true)
    setMdResult(null)
    setMdError('')

    const formData = new FormData()
    formData.append('file', mdFile)

    try {
      const res = await fetch('/api/skills/upload-file', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) {
        setMdError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      } else {
        setMdResult(data as SkillUploadResult)
        setMdFile(null)
        if (uploadFormRef.current) uploadFormRef.current.reset()
        loadSkills()
      }
    } catch (e) {
      setMdError(String(e))
    } finally {
      setMdUploading(false)
    }
  }

  const handleJsonUpload = async () => {
    try {
      JSON.parse(jsonInput)
      await api.post('/skills/upload', { skill_json: JSON.parse(jsonInput) })
      setUploadMsg('上传成功')
      setUploadErr(false)
      setJsonInput('')
      loadSkills()
    } catch {
      setUploadMsg('JSON 格式错误')
      setUploadErr(true)
    }
  }

  const handleToggle = async (name: string, enabled: boolean) => {
    await api.put(`/skills/${name}/toggle`, { enabled: !enabled })
    loadSkills()
  }

  const handleDelete = async (name: string) => {
    await api.del(`/skills/${name}`)
    loadSkills()
  }

  const handleViewDetail = async (name: string) => {
    const detail = await api.get<Record<string, unknown>>(`/skills/${name}`)
    setDetailSkill(detail)
    setSheetOpen(true)
  }

  if (loading) {
    return <div className="p-6 text-slate-500 dark:text-slate-400 text-sm">加载中...</div>
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-6 text-slate-900 dark:text-slate-100">Skills</h2>

      <div className="flex gap-2 mb-6 border-b border-slate-200 dark:border-slate-800">
        {(['list', 'upload'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              tab === t
                ? 'text-blue-600 dark:text-blue-400 border-blue-400'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border-transparent'
            }`}
          >
            {t === 'list' ? '已安装' : '上传 Skill'}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <div className="space-y-6 max-w-2xl">
          <Card>
            <CardContent className="p-5 space-y-4">
              <h3 className="text-sm font-medium">上传 Markdown 文件</h3>
              <form ref={uploadFormRef}>
                <Input
                  type="file"
                  accept=".md"
                  onChange={(e) => setMdFile(e.target.files?.[0] || null)}
                  className="text-sm file:bg-slate-200 dark:file:bg-slate-800 file:text-slate-700 dark:file:text-slate-300 file:border-0 file:mr-3 file:px-3 file:py-1 file:rounded file:cursor-pointer"
                />
              </form>
              {mdFile && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  已选择: {mdFile.name} ({(mdFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
              <Button
                onClick={handleMdUpload}
                disabled={!mdFile || mdUploading}
                className="bg-blue-600 hover:bg-blue-500"
              >
                {mdUploading ? '解析中...' : '上传并解析'}
              </Button>

              {mdError && (
                <div className="text-xs px-3 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
                  {mdError}
                </div>
              )}

              {mdResult && (
                <div className="space-y-3 mt-4 p-4 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800">
                  <div className="text-xs px-3 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Skill "{mdResult.display_name}" {mdResult.status === 'updated' ? '已覆盖更新' : '已成功安装'}
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-slate-100 dark:bg-slate-900 rounded-lg p-3 text-center">
                      <div className="text-lg font-bold text-blue-500 dark:text-blue-400">{mdResult.name}</div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500">名称</div>
                    </div>
                    <div className="bg-slate-100 dark:bg-slate-900 rounded-lg p-3 text-center">
                      <div className="text-lg font-bold text-blue-500 dark:text-blue-400">{mdResult.category}</div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500">分类</div>
                    </div>
                    <div className="bg-slate-100 dark:bg-slate-900 rounded-lg p-3 text-center">
                      <div className="text-lg font-bold text-blue-500 dark:text-blue-400">{mdResult.version || '1.0.0'}</div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500">版本</div>
                    </div>
                  </div>
                  {mdResult.description && (
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                      <strong>描述</strong>: {mdResult.description}
                    </p>
                  )}
                  {mdResult.tags && mdResult.tags.length > 0 && (
                    <div className="flex gap-1 flex-wrap">
                      {mdResult.tags.map((t: string) => (
                        <Badge key={t} variant="secondary" className="text-[10px]">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {mdResult.has_code && (
                    <div
                      className={`text-xs px-3 py-2 rounded-lg ${
                        mdResult.code_ok
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}
                    >
                      {mdResult.code_ok ? '代码验证通过' : `代码验证未通过: ${mdResult.code_msg}`}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5 space-y-4">
              <h3 className="text-sm font-medium">或粘贴 JSON</h3>
              <Textarea
                rows={10}
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder='{"name": "my_skill", "display_name": "My Skill", ...}'
                className="text-sm font-mono resize-none"
              />
              <Button onClick={handleJsonUpload} className="bg-blue-600 hover:bg-blue-500">
                上传 JSON
              </Button>
              {uploadMsg && (
                <div
                  className={`text-xs px-3 py-2 rounded-lg ${
                    uploadErr
                      ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  }`}
                >
                  {uploadMsg}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === 'list' &&
        (skills.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title="暂无已安装的 Skill"
            description="请先上传一个 Skill"
          />
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {skills.map((s) => (
              <Card
                key={s.name}
                className={!s.enabled ? 'opacity-50' : ''}
              >
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold">
                        {s.display_name}{' '}
                        <code className="text-[11px] text-slate-400 dark:text-slate-500">({s.name})</code>
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-500 mt-1">{s.description}</p>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-[10px] shrink-0 ${
                        s.enabled
                          ? 'border-emerald-500/30 text-emerald-400'
                          : 'border-slate-300 dark:border-slate-700 text-slate-500'
                      }`}
                    >
                      {s.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    <Badge variant="secondary" className="text-[10px]">
                      {s.category}
                    </Badge>
                    {s.tags.map((t) => (
                      <Badge key={t} variant="secondary" className="text-[10px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs h-7 hover:bg-slate-100 dark:hover:bg-slate-700"
                      onClick={() => handleViewDetail(s.name)}
                    >
                      详情
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs h-7 hover:bg-slate-100 dark:hover:bg-slate-700"
                      onClick={() => handleToggle(s.name, s.enabled)}
                    >
                      {s.enabled ? '禁用' : '启用'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs h-7 text-red-400 hover:text-red-300 hover:bg-red-500/10 ml-auto"
                      onClick={() => handleDelete(s.name)}
                    >
                      删除
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ))}

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[400px] sm:max-w-[400px]">
          <SheetHeader>
            <SheetTitle>Skill 详情</SheetTitle>
          </SheetHeader>
          <pre className="mt-6 text-xs text-slate-600 dark:text-slate-400 whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(detailSkill, null, 2)}
          </pre>
        </SheetContent>
      </Sheet>
    </div>
  )
}
