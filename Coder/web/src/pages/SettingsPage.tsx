import { useParams, Navigate } from 'react-router-dom'

const validCategories = ['general', 'model', 'skills', 'knowledge', 'about']

export function SettingsPage() {
  const { category } = useParams<{ category?: string }>()
  const active = category && validCategories.includes(category) ? category : 'general'

  // Redirect bare /settings to /settings/general
  if (!category || !validCategories.includes(category)) {
    return <Navigate to="/settings/general" replace />
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
        <div className="max-w-md">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>技能管理</h2>
          <p className="text-sm" style={{ color: 'var(--text-dim)' }}>技能管理功能即将在此页面集成。</p>
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
