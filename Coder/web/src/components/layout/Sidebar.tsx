import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useSidebar } from './SidebarContext'
import { useChatStore } from '@/stores/chatStore'
import { api } from '@/api/client'
import { Plus, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CourseItem {
  slug: string
  name: string
  kp_total: number
  kp_mastered: number
}

export function Sidebar() {
  const { width, collapsed, setWidth } = useSidebar()
  const navigate = useNavigate()
  const location = useLocation()
  const sessions = useChatStore((s) => s.sessions)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)

  const [courses, setCourses] = useState<CourseItem[]>([])
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadSessions()
    api.get<{ courses: CourseItem[] }>('/courses').then((d) => setCourses(d.courses)).catch(() => {})
  }, [loadSessions])

  // --- Page context ---
  const pageContext = useMemo(() => {
    const path = location.pathname
    if (path.startsWith('/course/')) return 'course' as const
    if (path === '/knowledge') return 'knowledge' as const
    if (path === '/settings') return 'settings' as const
    if (path === '/chat') return 'chat' as const
    return 'home' as const
  }, [location.pathname])

  const activeCourse = useMemo(() => {
    const match = location.pathname.match(/^\/course\/([^/]+)/)
    return match ? decodeURIComponent(match[1]) : null
  }, [location.pathname])

  const activeSubNav = useMemo(() => {
    if (!activeCourse) return null
    if (location.pathname.endsWith('/notes')) return 'notes'
    if (location.pathname.endsWith('/graph')) return 'graph'
    if (location.pathname.endsWith('/wrong')) return 'wrong'
    return 'qa'
  }, [location.pathname, activeCourse])

  // --- Drag-to-resize ---
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)
  const [localW, setLocalW] = useState<number | null>(null)
  const displayW = localW ?? width

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startX.current = e.clientX
    startW.current = width
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'ew-resize'
  }, [width])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const delta = e.clientX - startX.current
      setLocalW(Math.min(400, Math.max(52, startW.current + delta)))
    }
    const onMouseUp = () => {
      if (dragging.current && localW !== null) {
        setWidth(localW)
        setLocalW(null)
      }
      dragging.current = false
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [localW, setWidth])

  // --- Course sub-nav ---
  const subNav = activeCourse
    ? [
        { key: 'qa' as const, label: '问答', path: `/course/${activeCourse}` },
        { key: 'notes' as const, label: '笔记', path: `/course/${activeCourse}/notes` },
        { key: 'graph' as const, label: '知识图谱', path: `/course/${activeCourse}/graph` },
        { key: 'wrong' as const, label: '错题本', path: `/course/${activeCourse}/wrong` },
      ]
    : []

  const filteredCourses = search
    ? courses.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : courses

  // ====== RENDER HELPERS ======

  const renderLogo = () => (
    <div className="flex items-center justify-between px-2">
      <span className="text-[15px] font-bold" style={{
        background: 'var(--logo-gradient)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      }}>
        CourseMate
      </span>
      <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: 'var(--green)' }} />
    </div>
  )

  const renderCourseList = (showSubNav: boolean) => (
    <div>
      <div className="flex items-center justify-between px-2 mb-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-dim)' }}>
          我的课程
        </span>
        <button
          onClick={() => navigate('/')}
          className="w-5 h-5 rounded flex items-center justify-center transition-colors"
          style={{ color: 'var(--text-dim)' }}
          title="新建课程"
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      {courses.length > 3 && (
        <div className="px-2 mb-2">
          <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-xs"
            style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>
            <Search className="h-3 w-3 shrink-0" />
            <input className="bg-transparent border-none outline-none flex-1 text-xs"
              placeholder="搜索课程..." value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ color: 'var(--text)' }} />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-0.5">
        {filteredCourses.map((c) => {
          const isActive = activeCourse === c.slug
          const pct = c.kp_total > 0 ? Math.round((c.kp_mastered / c.kp_total) * 100) : 0

          return (
            <div key={c.slug}>
              <div
                onClick={() => navigate(`/course/${c.slug}`)}
                className="px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 text-[13px]"
                style={{
                  background: isActive ? 'linear-gradient(135deg, var(--brand-bg), var(--brand-bg2))' : 'transparent',
                  color: isActive ? 'var(--text)' : 'var(--text-dim)',
                  border: isActive ? '1px solid var(--brand-border)' : '1px solid transparent',
                }}
              >
                <span className="font-medium">{c.name}</span>
                <div className="text-[11px] mt-0.5" style={{ color: isActive ? 'var(--accent-glow)' : 'var(--text-dim)' }}>
                  {c.kp_mastered}/{c.kp_total} 知识点 · {pct}%
                </div>
              </div>

              {showSubNav && isActive && (
                <div className="flex flex-col gap-0.5 mt-0.5 ml-2">
                  {subNav.map((item) => (
                    <div key={item.key}
                      onClick={() => navigate(item.path)}
                      className="px-3 py-1.5 rounded-md cursor-pointer text-xs transition-all duration-150"
                      style={{
                        color: activeSubNav === item.key ? 'var(--accent-glow)' : 'var(--text-dim)',
                        background: activeSubNav === item.key ? 'var(--brand-bg-light)' : 'transparent',
                      }}
                    >
                      {item.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
        {filteredCourses.length === 0 && (
          <p className="text-xs px-2 py-3" style={{ color: 'var(--text-dim)' }}>
            {courses.length === 0 ? '暂无课程' : '无匹配结果'}
          </p>
        )}
      </div>
    </div>
  )

  const renderSessionHistory = () => (
    <div>
      <h3 className="text-[10px] font-semibold uppercase tracking-wider px-2 mb-1" style={{ color: 'var(--text-dim)' }}>
        最近会话
      </h3>
      {sessions.slice(0, 5).map((s) => (
        <div key={s.session_id}
          onClick={() => switchSession(s.session_id)}
          className="px-3 py-1.5 rounded-md text-xs cursor-pointer flex items-center justify-between group/session"
          style={{
            color: s.session_id === currentSessionId ? 'var(--accent-glow)' : 'var(--text-dim)',
            background: s.session_id === currentSessionId ? 'var(--brand-bg-light)' : 'transparent',
          }}
        >
          <span className="truncate">{s.title}</span>
          <button
            className="opacity-0 group-hover/session:opacity-100 text-xs shrink-0 ml-1 transition-opacity"
            style={{ color: 'inherit' }}
            onClick={(e) => { e.stopPropagation(); deleteSession(s.session_id) }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#f87171' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'inherit' }}
          >
            ×
          </button>
        </div>
      ))}
      {sessions.length === 0 && (
        <p className="text-[10px] px-2 py-1" style={{ color: 'var(--text-dim)' }}>暂无会话</p>
      )}
      <Button onClick={createSession} size="sm"
        className="w-full mt-2 text-xs font-medium"
        style={{ background: 'var(--brand)', color: '#fff' }}>
        ＋ 新会话
      </Button>
    </div>
  )

  // ====== BODY BY PAGE CONTEXT ======

  const renderBody = () => {
    switch (pageContext) {
      case 'course':
        // Course page: course list with sub-nav + session history at bottom
        return (
          <>
            <div className="p-3 space-y-4 flex-1 overflow-y-auto">
              {renderLogo()}
              {renderCourseList(true)}
            </div>
            <div className="border-t p-3 overflow-y-auto flex flex-col gap-0.5"
              style={{ borderColor: 'var(--border)', maxHeight: '35vh', transition: 'border-color 0.4s' }}>
              {renderSessionHistory()}
            </div>
          </>
        )

      case 'chat':
        // Chat page: session history only — no course list
        return (
          <>
            <div className="p-3 space-y-4 flex-1 overflow-y-auto">
              {renderLogo()}
            </div>
            <div className="border-t p-3 overflow-y-auto flex flex-col gap-0.5"
              style={{ borderColor: 'var(--border)', maxHeight: '40vh', transition: 'border-color 0.4s' }}>
              {renderSessionHistory()}
            </div>
          </>
        )

      case 'home':
        // Home: course list (no sub-nav) only — no session history
        return (
          <div className="p-3 space-y-4 flex-1 overflow-y-auto">
            {renderLogo()}
            {renderCourseList(false)}
          </div>
        )

      case 'knowledge':
        // Knowledge: knowledge-specific actions — no course list
        return (
          <>
            <div className="p-3 space-y-4 flex-1 overflow-y-auto">
              {renderLogo()}
            </div>
            <div className="border-t p-3 flex flex-col gap-0.5"
              style={{ borderColor: 'var(--border)', transition: 'border-color 0.4s' }}>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 mb-1" style={{ color: 'var(--text-dim)' }}>
                知识库
              </span>
              <div className="px-3 py-1.5 rounded-md text-xs cursor-pointer transition-colors"
                style={{ color: 'var(--text-dim)' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}>
                📤 上传文档
              </div>
              <div className="px-3 py-1.5 rounded-md text-xs cursor-pointer transition-colors"
                style={{ color: 'var(--text-dim)' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--btn-hover-bg)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}>
                📋 文档列表
              </div>
            </div>
          </>
        )

      case 'settings':
        // Settings: logo only — category nav lives in SettingsPage itself
        return (
          <div className="p-3 space-y-4 flex-1 overflow-y-auto">
            {renderLogo()}
          </div>
        )
    }
  }

  return (
    <aside
      className="flex flex-col shrink-0 overflow-hidden relative group/sidebar"
      style={{
        width: displayW,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        transition: dragging.current ? 'none' : 'width 150ms ease-out, background 0.4s, border-color 0.4s',
      }}
    >
      <div
        className="absolute right-0 top-0 w-1.5 h-full cursor-ew-resize z-10 opacity-0 group-hover/sidebar:opacity-100 active:opacity-100 transition-opacity"
        style={{ background: 'rgba(99,102,241,0.2)' }}
        onMouseDown={onMouseDown}
      />

      {!collapsed && renderBody()}
    </aside>
  )
}
