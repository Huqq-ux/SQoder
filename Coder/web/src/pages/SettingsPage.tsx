import { useState } from 'react'

const categories = [
  { key: 'general', label: '通用' },
  { key: 'model', label: '模型设置' },
  { key: 'skills', label: '技能管理' },
  { key: 'knowledge', label: '知识库' },
  { key: 'about', label: '关于' },
]

export function SettingsPage() {
  const [active, setActive] = useState('general')

  return (
    <div className="h-full flex overflow-hidden" style={{ background: 'var(--bg)' }}>
      {/* Left nav */}
      <div
        className="w-36 shrink-0 p-3 flex flex-col gap-0.5 border-r overflow-y-auto"
        style={{ borderColor: 'var(--border)' }}
      >
        {categories.map(({ key, label }) => (
          <div
            key={key}
            onClick={() => setActive(key)}
            className="px-3 py-2 rounded-lg cursor-pointer text-sm transition-all duration-150"
            style={{
              background: active === key ? 'var(--brand-bg-light)' : 'transparent',
              color: active === key ? 'var(--accent-glow)' : 'var(--text-dim)',
              fontWeight: active === key ? 600 : 400,
            }}
          >
            {label}
          </div>
        ))}
      </div>

      {/* Right content */}
      <div className="flex-1 p-6 overflow-y-auto">
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
    </div>
  )
}
