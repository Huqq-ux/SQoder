import { useParams, Navigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { listSkills, uploadSkillFile, toggleSkill, deleteSkill } from '@/api/skills'
import { listServers, toggleServer, testServer } from '@/api/mcp'
import { notify } from '@/lib/toast'
import type { SkillMeta, MCPServer } from '@/types'
import { Upload, Trash2, RefreshCw, Plug } from 'lucide-react'

const validCategories = ['general', 'model', 'skills', 'knowledge', 'mcp', 'about']

export function SettingsPage() {
  const { category } = useParams<{ category?: string }>()
  const active = category && validCategories.includes(category) ? category : 'general'

  // Redirect bare /settings to /settings/general
  if (!category || !validCategories.includes(category)) {
    return <Navigate to="/settings/general" replace />
  }

  // Skills state
  const [skills, setSkills] = useState<SkillMeta[]>([])
  const [skillsLoading, setSkillsLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchSkills = () => {
    setSkillsLoading(true)
    listSkills().then(setSkills).catch(() => setSkills([])).finally(() => setSkillsLoading(false))
  }

  // MCP state
  const [servers, setServers] = useState<MCPServer[]>([])
  const [mcpLoading, setMcpLoading] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)

  const fetchServers = () => {
    setMcpLoading(true)
    listServers().then(setServers).catch(() => setServers([])).finally(() => setMcpLoading(false))
  }

  useEffect(() => { if (active === 'skills') fetchSkills() }, [active])
  useEffect(() => { if (active === 'mcp') fetchServers() }, [active])

  const handleToggleServer = async (id: string, enabled: boolean) => {
    await toggleServer(id, !enabled)
    fetchServers()
  }

  const handleTestServer = async (id: string) => {
    setTestingId(id)
    try {
      const result = await testServer(id)
      if (result.success) {
        notify.success(`连接成功，${result.tools.length} 个工具可用`)
      } else {
        notify.error(`连接失败: ${result.error}`)
      }
    } catch (err: any) {
      notify.error(`测试失败: ${err?.message || '未知错误'}`)
    } finally {
      setTestingId(null)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadSkillFile(file)
      fetchSkills()
    } catch (err: any) {
      notify.error(`上传失败: ${err?.message || '未知错误'}`)
    }
  }

  const handleToggle = async (name: string, enabled: boolean) => {
    await toggleSkill(name, !enabled)
    fetchSkills()
  }

  const handleDelete = async (name: string) => {
    if (!window.confirm('确定删除该技能？')) return
    await deleteSkill(name)
    fetchSkills()
  }

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
      {active === 'general' && (
        <div className="max-w-md flex flex-col gap-4">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>通用设置</h2>
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text)' }}>界面语言</span>
            <select className="px-2.5 py-1 rounded-lg text-sm border" style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}>
              <option>简体中文</option>
              <option>English</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text)' }}>默认主题</span>
            <select className="px-2.5 py-1 rounded-lg text-sm border" style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}>
              <option>跟随系统</option>
              <option>暗色</option>
              <option>亮色</option>
            </select>
          </div>
        </div>
      )}

      {active === 'model' && (
        <div className="max-w-md">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>模型设置</h2>
          <p className="text-sm" style={{ color: 'var(--text-dim)' }}>模型配置由后端管理，请修改环境变量或服务器配置。</p>
        </div>
      )}

      {active === 'skills' && (
        <div className="max-w-xl flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>技能管理</h2>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90 flex items-center gap-1"
              style={{ background: 'var(--brand)' }}
            >
              <Upload className="h-3.5 w-3.5" />
              上传 Skill
            </button>
            <input ref={fileInputRef} type="file" accept=".md" className="hidden" onChange={handleUpload} />
          </div>
          <p className="text-xs" style={{ color: 'var(--text-dim)' }}>
            Skill 是扩展 AI 能力的自定义脚本，Agent 在对话中可动态调用。上传 .md 格式的技能定义文件。
          </p>

          {skillsLoading ? (
            <p className="text-xs" style={{ color: 'var(--text-dim)' }}>加载中...</p>
          ) : skills.length === 0 ? (
            <div className="rounded-xl p-8 text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <p className="text-sm" style={{ color: 'var(--text-dim)' }}>暂无技能</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-dim)' }}>点击上方按钮上传你的第一个 Skill</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {skills.map((s) => (
                <div key={s.name} className="rounded-xl p-3.5 flex items-center justify-between" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{s.display_name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md" style={{
                        background: s.enabled ? 'rgba(34,197,94,.1)' : 'rgba(148,163,184,.1)',
                        color: s.enabled ? 'var(--green)' : 'var(--text-dim)',
                      }}>
                        {s.enabled ? '已启用' : '已禁用'}
                      </span>
                      <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>v{s.version}</span>
                    </div>
                    <p className="text-[11px] mt-1 truncate" style={{ color: 'var(--text-dim)' }}>{s.description}</p>
                    <div className="flex gap-1 mt-1.5">
                      {s.tags?.map((t: string) => (
                        <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>{t}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    <button
                      onClick={() => handleToggle(s.name, s.enabled)}
                      className="text-[11px] px-2 py-1 rounded-md transition-colors"
                      style={{ color: s.enabled ? 'var(--amber)' : 'var(--green)' }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                    >
                      {s.enabled ? '禁用' : '启用'}
                    </button>
                    <button
                      onClick={() => handleDelete(s.name)}
                      className="p-1 rounded-md transition-colors"
                      style={{ color: 'var(--text-dim)' }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--red)' }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-dim)' }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {active === 'knowledge' && (
        <div className="max-w-md flex flex-col gap-4">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>知识库设置</h2>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm" style={{ color: 'var(--text)' }}>RAG 检索阈值</span>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>低于此相似度的文档片段不纳入回答</p>
            </div>
            <span className="text-sm font-semibold" style={{ color: 'var(--accent-glow)' }}>1.5</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm" style={{ color: 'var(--text)' }}>检索数量</span>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>每次问答返回的文档片段数</p>
            </div>
            <span className="text-sm font-semibold" style={{ color: 'var(--accent-glow)' }}>5</span>
          </div>
        </div>
      )}

      {active === 'mcp' && (
        <div className="max-w-xl flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>MCP 服务</h2>
            <button
              onClick={fetchServers}
              disabled={mcpLoading}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-opacity hover:opacity-90 flex items-center gap-1"
              style={{ background: 'var(--brand)', color: '#fff' }}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${mcpLoading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-dim)' }}>
            MCP (Model Context Protocol) 服务为 Agent 提供外部工具能力。启动时自动注册，支持动态热加载。
          </p>

          {mcpLoading ? (
            <p className="text-xs" style={{ color: 'var(--text-dim)' }}>加载中...</p>
          ) : servers.length === 0 ? (
            <div className="rounded-xl p-8 text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <Plug className="h-8 w-8 mx-auto mb-2" style={{ color: 'var(--text-dim)' }} />
              <p className="text-sm" style={{ color: 'var(--text-dim)' }}>暂无 MCP 服务</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-dim)' }}>通过 API 或内置服务注册 MCP 工具</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {servers.map((s) => (
                <div key={s.id} className="rounded-xl p-3.5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>{s.display_name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md shrink-0" style={{
                        background: s.status === 'connected' ? 'rgba(34,197,94,.1)'
                          : s.status === 'error' ? 'rgba(239,68,68,.1)'
                          : 'rgba(148,163,184,.1)',
                        color: s.status === 'connected' ? 'var(--green)'
                          : s.status === 'error' ? 'var(--red)'
                          : 'var(--text-dim)',
                      }}>
                        {s.status === 'connected' ? '已连接' : s.status === 'error' ? '异常' : '已禁用'}
                      </span>
                      <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>{s.tool_count} 个工具</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleTestServer(s.id)}
                        disabled={testingId === s.id}
                        className="text-[11px] px-2 py-1 rounded-md transition-colors"
                        style={{ color: 'var(--text-dim)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                      >
                        {testingId === s.id ? '测试中...' : '测试'}
                      </button>
                      <button
                        onClick={() => handleToggleServer(s.id, s.enabled)}
                        className="text-[11px] px-2 py-1 rounded-md transition-colors"
                        style={{ color: s.enabled ? 'var(--amber)' : 'var(--green)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                      >
                        {s.enabled ? '禁用' : '启用'}
                      </button>
                    </div>
                  </div>
                  <p className="text-[11px] mt-1 truncate" style={{ color: 'var(--text-dim)' }}>{s.description}</p>
                  {s.transport === 'stdio' && s.command && (
                    <p className="text-[10px] mt-1" style={{ color: 'var(--text-dim)' }}>
                      <code className="px-1 py-0.5 rounded" style={{ background: 'var(--card)' }}>{s.command} {((s.args as unknown) as string[])?.join(' ')}</code>
                    </p>
                  )}
                  {s.last_error && (
                    <p className="text-[10px] mt-1 truncate" style={{ color: 'var(--red)' }}>{s.last_error}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {active === 'about' && (
        <div className="max-w-md">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>关于 CourseMate</h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-dim)' }}>
            CourseMate — 围绕课程教材的 AI 学习伴侣。基于 LangChain + LangGraph 构建，
            聚焦高等教育场景，以课程知识库 + RAG 精准问答 + 学习路径追踪为核心。
          </p>
          <p className="text-xs mt-4" style={{ color: 'var(--text-dim)' }}>Version 0.1.0</p>
        </div>
      )}
    </div>
  )
}
