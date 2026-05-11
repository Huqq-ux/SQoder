import { useEffect } from 'react'
import { useChatStore } from '../stores/chatStore'
import type { NavPage } from '../types'

const navItems: { page: NavPage; icon: string; label: string }[] = [
  { page: 'chat', icon: '💬', label: '对话' },
  { page: 'knowledge', icon: '📚', label: '知识库' },
  { page: 'sop', icon: '📋', label: 'SOP 管理' },
  { page: 'skills', icon: '🔧', label: 'Skill 管理' },
  { page: 'multi-agent', icon: '🤖', label: '多智能体' },
]

export function Sidebar() {
  const navPage = useChatStore((s) => s.navPage)
  const setNavPage = useChatStore((s) => s.setNavPage)
  const sessions = useChatStore((s) => s.sessions)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleNavClick = (page: NavPage) => {
    setNavPage(page)
    if (page === 'chat' && !currentSessionId) {
      createSession()
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>🤖 AI 编程助手</h1>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.page}
            className={`nav-item ${navPage === item.page ? 'active' : ''}`}
            onClick={() => handleNavClick(item.page)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {navPage === 'chat' && sessions.length > 0 && (
        <div className="sidebar-sessions">
          <h3>会话历史</h3>
          {sessions.map((s) => (
            <div
              key={s.session_id}
              className={`session-item ${s.session_id === currentSessionId ? 'active' : ''}`}
              onClick={() => switchSession(s.session_id)}
            >
              <span className="session-item-title" title={s.title}>
                {s.title}
              </span>
              <button
                className="session-item-del"
                onClick={(e) => {
                  e.stopPropagation()
                  deleteSession(s.session_id)
                }}
              >
                🗑
              </button>
            </div>
          ))}
          <button className="btn-new-session" onClick={createSession}>
            ＋ 新会话
          </button>
        </div>
      )}
    </aside>
  )
}
