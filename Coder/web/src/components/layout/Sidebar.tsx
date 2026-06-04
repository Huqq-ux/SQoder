import { NavLink } from 'react-router-dom'
import { useSidebar } from './SidebarContext'
import { MessageSquare, BookOpen, Wrench, Bot, Plug } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useChatStore } from '@/stores/chatStore'
import { useEffect } from 'react'

const navItems = [
  { to: '/chat', icon: MessageSquare, label: '对话' },
  { to: '/knowledge', icon: BookOpen, label: '知识库' },
  { to: '/skills', icon: Wrench, label: 'Skills' },
  { to: '/multi-agent', icon: Bot, label: '多智能体' },
  { to: '/mcp', icon: Plug, label: 'MCP' },
]

export function Sidebar() {
  const { collapsed } = useSidebar()
  const sessions = useChatStore((s) => s.sessions)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  return (
    <aside
      className={`${
        collapsed ? 'w-[52px]' : 'w-56'
      } bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 transition-all duration-200 overflow-hidden`}
    >
      <nav className="p-3 space-y-1 flex-1">
        {navItems.map(({ to, icon: Icon, label }) => {
          const link = (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-500/10 text-blue-400'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-300'
                } ${collapsed ? 'justify-center px-2' : ''}`
              }
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && <span className="whitespace-nowrap">{label}</span>}
            </NavLink>
          )

          if (collapsed) {
            return (
              <Tooltip key={to}>
                <TooltipTrigger>{link}</TooltipTrigger>
                <TooltipContent
                  side="right"
                  className="bg-slate-800 text-slate-200 border-slate-700"
                >
                  {label}
                </TooltipContent>
              </Tooltip>
            )
          }
          return link
        })}
      </nav>

      {!collapsed && (
        <div
          className="border-t border-slate-800 p-3 overflow-y-auto"
          style={{ maxHeight: '40vh' }}
        >
          <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 px-2 mb-2">
            会话历史
          </h3>
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => switchSession(s.session_id)}
              className={`px-3 py-1.5 rounded-md text-xs cursor-pointer flex items-center justify-between group mb-0.5 ${
                s.session_id === currentSessionId
                  ? 'bg-blue-500/10 text-blue-400'
                  : 'text-slate-400 hover:bg-slate-900'
              }`}
            >
              <span className="truncate">{s.title}</span>
              <button
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 text-xs shrink-0 ml-2"
                onClick={(e) => {
                  e.stopPropagation()
                  deleteSession(s.session_id)
                }}
              >
                &times;
              </button>
            </div>
          ))}
          <button
            onClick={createSession}
            className="w-full mt-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
          >
            ＋ 新会话
          </button>
        </div>
      )}
    </aside>
  )
}
