# Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面翻新 Coder/web 前端，Tailwind CSS + shadcn/ui + React Router v6，默认深色主题支持浅色切换，顶栏+可折叠侧边栏，Qbot 品牌

**Architecture:** 自底向上迁移——先建立基础设施（Tailwind/shadcn），再构建布局外壳（Router/TopNav/Sidebar），然后逐个迁移页面，最后清理旧代码。API 层和 Zustand store 不动。

**Tech Stack:** Tailwind CSS v4, shadcn/ui (Radix UI), React Router v6, lucide-react, next-themes, Zustand (保留)

---

## Phase 1: 基础设施搭建

### Task 1: 安装 Tailwind CSS 和 PostCSS

**Files:**
- Create: `Coder/web/postcss.config.js`
- Modify: `Coder/web/package.json`
- Create: `Coder/web/src/index.css`

- [ ] **Step 1: 安装依赖**

```bash
cd /d/PyCharm/AI/Coder/web
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: 配置 Vite 插件**

修改 `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 index.css 替代 App.css**

创建 `Coder/web/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-sidebar: #0f172a;
  --color-sidebar-text: #94a3b8;
  --color-sidebar-active: #1e293b;
}

@layer base {
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    @apply bg-slate-950 text-slate-100 antialiased;
  }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { @apply bg-slate-700 rounded-md; }
  ::-webkit-scrollbar-thumb:hover { @apply bg-slate-600; }
}
```

- [ ] **Step 4: 替换 main.tsx 中的 CSS import**

修改 `Coder/web/src/main.tsx`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 5: 验证**

```bash
cd /d/PyCharm/AI/Coder/web && npm run dev
```

打开 http://localhost:5173，确认页面无样式错误（Tailwind 生效）。

- [ ] **Step 6: Commit**

```bash
git add Coder/web/vite.config.ts Coder/web/src/index.css Coder/web/src/main.tsx Coder/web/package.json
git commit -m "feat: add Tailwind CSS v4 with Vite plugin, replace App.css"
```

### Task 2: 安装 shadcn/ui CLI 并初始化

**Files:**
- Create: `Coder/web/components.json`
- Create: `Coder/web/src/lib/utils.ts`

- [ ] **Step 1: 安装 shadcn/ui**

```bash
cd /d/PyCharm/AI/Coder/web
npm install -D @types/node
npm install lucide-react next-themes class-variance-authority clsx tailwind-merge
npx shadcn@latest init -d
```

执行 init 时选择:
- Style: New York
- Base color: Slate
- CSS variables: Yes
- CSS file: src/index.css
- Component path: src/components/ui
- Utils path: src/lib/utils

- [ ] **Step 2: 验证 utils.ts 生成**

检查 `Coder/web/src/lib/utils.ts` 已创建且包含 `cn()` 函数。

- [ ] **Step 3: 添加基本 shadcn 组件**

```bash
cd /d/PyCharm/AI/Coder/web
npx shadcn@latest add button input textarea scroll-area accordion tooltip sheet separator badge card dropdown-menu
```

- [ ] **Step 4: Commit**

```bash
git add Coder/web/components.json Coder/web/src/lib/ Coder/web/src/components/ui/ Coder/web/package.json
git commit -m "feat: init shadcn/ui, add base component set"
```

---

## Phase 2: 布局外壳

### Task 3: 创建 SidebarContext 和布局框架

**Files:**
- Create: `Coder/web/src/components/layout/SidebarContext.tsx`
- Modify: `Coder/web/src/App.tsx`

- [ ] **Step 1: 创建 SidebarContext**

创建 `Coder/web/src/components/layout/SidebarContext.tsx`:

```typescript
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface SidebarContextType {
  collapsed: boolean
  toggle: () => void
}

const SidebarContext = createContext<SidebarContextType>({ collapsed: false, toggle: () => {} })

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => {
    const stored = localStorage.getItem('sidebar-collapsed')
    return stored === 'true'
  })

  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', String(collapsed))
  }, [collapsed])

  const toggle = () => setCollapsed((v) => !v)

  return (
    <SidebarContext.Provider value={{ collapsed, toggle }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  return useContext(SidebarContext)
}
```

- [ ] **Step 2: 更新 App.tsx 为布局框架**

修改 `Coder/web/src/App.tsx`:

```typescript
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import { SidebarProvider } from './components/layout/SidebarContext'

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <BrowserRouter>
        <SidebarProvider>
          <AppLayout />
        </SidebarProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <div className="text-slate-400 text-sm">Loading...</div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/components/layout/SidebarContext.tsx Coder/web/src/App.tsx
git commit -m "feat: add SidebarContext with localStorage persistence, setup App shell"
```

### Task 4: 创建 TopNav 组件

**Files:**
- Create: `Coder/web/src/components/layout/TopNav.tsx`
- Modify: `Coder/web/src/App.tsx`

- [ ] **Step 1: 创建 TopNav**

创建 `Coder/web/src/components/layout/TopNav.tsx`:

```typescript
import { useSidebar } from './SidebarContext'
import { useTheme } from 'next-themes'
import { PanelLeft, Sun, Moon } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function TopNav() {
  const { collapsed, toggle } = useSidebar()
  const { theme, setTheme } = useTheme()

  return (
    <header className="h-14 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 flex items-center px-4 shrink-0 z-50">
      <Button variant="ghost" size="icon" onClick={toggle} className="text-slate-400 hover:text-slate-200 mr-2" title={collapsed ? '展开侧边栏' : '折叠侧边栏'}>
        <PanelLeft className="h-4 w-4" />
      </Button>

      <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">Qbot</span>

      <div className="flex-1 max-w-md mx-auto">
        <div className="flex items-center bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-500">
          <span>搜索...</span>
          <kbd className="ml-auto text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-600">⌘K</kbd>
        </div>
      </div>

      <div className="flex items-center gap-2 ml-4">
        <Button variant="ghost" size="icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="text-slate-400 hover:text-slate-200" title="切换主题">
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-xs font-bold text-white">
          U
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: 将 TopNav 集成到 AppLayout**

修改 `App.tsx` 中 `AppLayout`:

```typescript
import { TopNav } from './components/layout/TopNav'

function AppLayout() {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <div className="text-slate-400 text-sm">Sidebar placeholder</div>
        <main className="flex-1 overflow-hidden">Content placeholder</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/components/layout/TopNav.tsx Coder/web/src/App.tsx
git commit -m "feat: add TopNav with glass effect, theme toggle, Qbot branding"
```

### Task 5: 创建可折叠 Sidebar 组件

**Files:**
- Create: `Coder/web/src/components/layout/Sidebar.tsx`
- Modify: `Coder/web/src/App.tsx`

- [ ] **Step 1: 创建 Sidebar 组件**

创建 `Coder/web/src/components/layout/Sidebar.tsx`:

```typescript
import { NavLink } from 'react-router-dom'
import { useSidebar } from './SidebarContext'
import { MessageSquare, BookOpen, Wrench, Bot, Plug } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
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

  useEffect(() => { loadSessions() }, [loadSessions])

  return (
    <aside className={`${collapsed ? 'w-[52px]' : 'w-56'} bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 transition-all duration-200 overflow-hidden`}>
      <nav className="p-3 space-y-1 flex-1">
        {navItems.map(({ to, icon: Icon, label }) => {
          const link = (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                ${isActive ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-300'}
                ${collapsed ? 'justify-center px-2' : ''}`
              }
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && <span className="whitespace-nowrap">{label}</span>}
            </NavLink>
          )

          if (collapsed) {
            return (
              <Tooltip key={to} delayDuration={0}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right" className="bg-slate-800 text-slate-200 border-slate-700">
                  {label}
                </TooltipContent>
              </Tooltip>
            )
          }
          return link
        })}
      </nav>

      {!collapsed && (
        <div className="border-t border-slate-800 p-3 overflow-y-auto" style={{ maxHeight: '40vh' }}>
          <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 px-2 mb-2">会话历史</h3>
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => switchSession(s.session_id)}
              className={`px-3 py-1.5 rounded-md text-xs cursor-pointer flex items-center justify-between group mb-0.5
                ${s.session_id === currentSessionId ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-slate-900'}`}
            >
              <span className="truncate">{s.title}</span>
              <button
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 text-xs shrink-0 ml-2"
                onClick={(e) => { e.stopPropagation(); deleteSession(s.session_id) }}
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
```

- [ ] **Step 2: 在 AppLayout 中集成 Sidebar**

修改 `App.tsx` 的 `AppLayout`:

```typescript
import { Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'

function AppLayout() {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<div className="text-slate-400">Chat</div>} />
            <Route path="/knowledge" element={<div className="text-slate-400">Knowledge</div>} />
            <Route path="/skills" element={<div className="text-slate-400">Skills</div>} />
            <Route path="/multi-agent" element={<div className="text-slate-400">MultiAgent</div>} />
            <Route path="/mcp" element={<div className="text-slate-400">MCP</div>} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 启动验证**

```bash
cd /d/PyCharm/AI/Coder/web && npm run dev
```

验证: 顶栏显示 Qbot logo、折叠按钮可收起/展开侧边栏、主题切换按钮可用、导航链接可点击切换路由。

- [ ] **Step 4: Commit**

```bash
git add Coder/web/src/components/layout/Sidebar.tsx Coder/web/src/App.tsx
git commit -m "feat: add collapsible Sidebar with NavLink routing and session list"
```

---

## Phase 3: 共享组件

### Task 6: 创建 EmptyState 组件

**Files:**
- Create: `Coder/web/src/components/shared/EmptyState.tsx`

- [ ] **Step 1: 创建 EmptyState**

创建 `Coder/web/src/components/shared/EmptyState.tsx`:

```typescript
import { type LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  className?: string
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 text-center ${className || ''}`}>
      {Icon && <Icon className="h-12 w-12 text-slate-700 mb-4" />}
      <h3 className="text-sm font-medium text-slate-400">{title}</h3>
      {description && <p className="text-xs text-slate-600 mt-1">{description}</p>}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/components/shared/EmptyState.tsx
git commit -m "feat: add reusable EmptyState component"
```

---

## Phase 4: 对话页面（核心）

### Task 7: 重构 ChatMessage 组件

**Files:**
- Modify: `Coder/web/src/components/ChatMessage.tsx`
- Create: `Coder/web/src/components/chat/ToolCallAccordion.tsx`

- [ ] **Step 1: 创建 ToolCallAccordion 子组件**

创建 `Coder/web/src/components/chat/ToolCallAccordion.tsx`:

```typescript
import type { ChatPart } from '@/types'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Wrench } from 'lucide-react'

export function ToolCallAccordion({ parts }: { parts: ChatPart[] }) {
  return (
    <Accordion type="single" collapsible className="mt-3">
      <AccordionItem value="tools" className="border-none">
        <AccordionTrigger className="text-xs text-slate-500 hover:text-slate-400 py-1 no-underline">
          <span className="flex items-center gap-2">
            <Wrench className="h-3 w-3" />
            {parts.length} 次工具调用
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2 pl-2 border-l-2 border-slate-700 mt-2">
            {parts.map((part, i) =>
              part.type === 'tool_call' ? (
                <div key={i} className="bg-slate-900/80 rounded-lg px-3 py-2 text-xs">
                  <Badge variant="secondary" className="mr-2 text-[10px] bg-amber-500/10 text-amber-400 border-0">调用</Badge>
                  <code className="text-slate-400">{part.name}</code>
                  {part.args && <pre className="mt-1 text-[11px] text-slate-500 whitespace-pre-wrap">{part.args}</pre>}
                </div>
              ) : (
                <div key={i} className="bg-emerald-500/5 rounded-lg px-3 py-2 text-xs">
                  <Badge variant="secondary" className="mr-2 text-[10px] bg-emerald-500/10 text-emerald-400 border-0">结果</Badge>
                  <code className="text-slate-400">{part.name}</code>
                  <pre className="mt-1 text-[11px] text-slate-500 whitespace-pre-wrap max-h-24 overflow-y-auto">{part.content}</pre>
                </div>
              )
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
```

- [ ] **Step 2: 重写 ChatMessage 组件**

修改 `Coder/web/src/components/ChatMessage.tsx`:

```typescript
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatPart } from '../types'
import { ToolCallAccordion } from './chat/ToolCallAccordion'

function mergeParts(parts: ChatPart[]): ChatPart[] {
  const merged: ChatPart[] = []
  for (const p of parts) {
    if (!merged.length) { merged.push({ ...p }); continue }
    const last = merged[merged.length - 1]
    if (p.type === 'content' && last.type === 'content') {
      last.content = (last.content || '') + (p.content || '')
    } else { merged.push({ ...p }) }
  }
  return merged
}

export function ChatMessage({ parts }: { parts?: ChatPart[] }) {
  if (!parts || parts.length === 0) return null

  const merged = mergeParts(parts)
  const contentParts = merged.filter((p) => p.type === 'content')
  const errorParts = merged.filter((p) => p.type === 'error')
  const toolParts = merged.filter((p) => p.type === 'tool_call' || p.type === 'tool_result')
  const text = contentParts.map((p) => p.content || '').join('')

  return (
    <div>
      {text && (
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {text}
          </ReactMarkdown>
        </div>
      )}

      {errorParts.map((part, i) => (
        <div key={i} className="mt-2 px-3 py-2 rounded-lg border border-red-500/20 bg-red-500/5 text-red-400 text-xs">
          {part.content}
        </div>
      ))}

      {toolParts.length > 0 && <ToolCallAccordion parts={toolParts} />}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/components/ChatMessage.tsx Coder/web/src/components/chat/ToolCallAccordion.tsx
git commit -m "refactor: ChatMessage with shadcn Accordion for tool calls"
```

### Task 8: 拆分 ChatInput 和 MessageList

**Files:**
- Create: `Coder/web/src/components/chat/ChatInput.tsx`
- Create: `Coder/web/src/components/chat/MessageList.tsx`

- [ ] **Step 1: 创建 ChatInput**

创建 `Coder/web/src/components/chat/ChatInput.tsx`:

```typescript
import { useRef, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onStop: () => void
  streaming: boolean
}

export function ChatInput({ value, onChange, onSend, onStop, streaming }: ChatInputProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="border-t border-slate-800 pt-4">
      <div className="flex gap-3 items-end">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
          disabled={streaming}
          rows={1}
          className="flex-1 bg-slate-900 border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 resize-none min-h-[44px] max-h-[120px] focus-visible:ring-blue-500/30"
        />
        {streaming ? (
          <Button onClick={onStop} variant="destructive" size="icon" className="shrink-0 rounded-xl h-11 w-11">
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={onSend} disabled={!value.trim()} size="icon" className="shrink-0 rounded-xl h-11 w-11 bg-blue-600 hover:bg-blue-500">
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 创建 MessageList**

创建 `Coder/web/src/components/chat/MessageList.tsx`:

```typescript
import { useEffect, useRef } from 'react'
import type { Message } from '@/types'
import { ChatMessage } from '@/components/ChatMessage'
import { EmptyState } from '@/components/shared/EmptyState'
import { MessageSquare } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  streaming: boolean
}

export function MessageList({ messages, streaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0 && !streaming) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="输入你的问题，Qbot 将为你提供帮助"
        description="支持代码生成、知识库检索、多智能体协作"
      />
    )
  }

  return (
    <div className="flex-1 overflow-y-auto pr-4 space-y-6">
      {messages.map((msg, i) => (
        <div key={i} className={msg.role === 'user' ? 'flex justify-end' : ''}>
          {msg.role === 'user' ? (
            <div className="max-w-[75%] bg-blue-500/15 border border-blue-500/20 rounded-2xl rounded-br-md px-4 py-3">
              <p className="text-sm text-blue-50">{msg.content}</p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1">Qbot</p>
              <ChatMessage parts={msg.parts} />
            </div>
          )}
        </div>
      ))}

      {streaming && (
        <div className="flex items-center gap-2 text-sm text-blue-400">
          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
          Qbot 正在生成回答...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/components/chat/ChatInput.tsx Coder/web/src/components/chat/MessageList.tsx
git commit -m "feat: extract ChatInput and MessageList from ChatPage"
```

### Task 9: 创建 CanvasPanel 组件

**Files:**
- Create: `Coder/web/src/components/chat/CanvasPanel.tsx`

- [ ] **Step 1: 创建 CanvasPanel**

创建 `Coder/web/src/components/chat/CanvasPanel.tsx`:

```typescript
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/stores/chatStore'

export function CanvasPanel() {
  const canvasOpen = useChatStore((s) => s.canvasOpen)
  const canvasContent = useChatStore((s) => s.canvasContent)
  const setCanvasOpen = useChatStore((s) => s.setCanvasOpen)

  return (
    <div className={`${canvasOpen ? 'w-96' : 'w-0'} border-l border-slate-800 bg-slate-950 shrink-0 overflow-hidden transition-all duration-200`}>
      <div className="w-96 p-4 h-full overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-300">画布</h3>
          <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-500 hover:text-slate-300" onClick={() => setCanvasOpen(false)}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>

        {canvasContent ? (
          <div className="space-y-4">
            {canvasContent.type === 'code' && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-800">
                  <span className="text-xs text-slate-400">{canvasContent.data?.filename || 'code'}</span>
                </div>
                <pre className="p-3 text-[11px] leading-relaxed overflow-x-auto text-slate-400">
                  <code>{canvasContent.data?.content || ''}</code>
                </pre>
              </div>
            )}
            {canvasContent.type === 'tool' && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-medium text-slate-400 mb-2">工具调用详情</h4>
                <div className="text-[11px] text-slate-500 space-y-1">
                  {Object.entries(canvasContent.data || {}).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span>{k}</span>
                      <span className="text-slate-400">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-600 text-center mt-12">暂无内容</p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/components/chat/CanvasPanel.tsx
git commit -m "feat: add CanvasPanel for code/file preview in chat"
```

### Task 10: 重写 ChatPage

**Files:**
- Modify: `Coder/web/src/pages/ChatPage.tsx`
- Modify: `Coder/web/src/stores/chatStore.ts`
- Modify: `Coder/web/src/types.ts`

- [ ] **Step 1: 更新 chatStore 添加 canvas 状态**

修改 `Coder/web/src/stores/chatStore.ts`:

```typescript
import { create } from 'zustand'
import type { Message, Session } from '../types'
import * as sessionsApi from '../api/sessions'

interface CanvasContent {
  type: 'code' | 'tool'
  data: Record<string, unknown> | null
}

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null
  messages: Message[]
  streaming: boolean
  canvasOpen: boolean
  canvasContent: CanvasContent | null

  loadSessions: () => Promise<void>
  createSession: () => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  addUserMessage: (content: string) => void
  appendAssistantPart: (part: Message['parts'] extends (infer T)[] | undefined ? T : never) => void
  finalizeAssistantMessage: () => void
  setStreaming: (v: boolean) => void
  setCanvasOpen: (v: boolean) => void
  setCanvasContent: (c: CanvasContent | null) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  streaming: false,
  canvasOpen: false,
  canvasContent: null,

  // ... existing methods unchanged ...
  async loadSessions() {
    const sessions = await sessionsApi.listSessions()
    set({ sessions })
  },

  async createSession() {
    const session = await sessionsApi.createSession()
    set((s) => ({ sessions: [session, ...s.sessions], currentSessionId: session.session_id, messages: [] }))
  },

  async switchSession(id: string) {
    set({ currentSessionId: id, messages: [] })
    try {
      const messages = await sessionsApi.getMessages(id)
      set({ messages })
    } catch { set({ messages: [] }) }
  },

  async deleteSession(id: string) {
    await sessionsApi.deleteSession(id)
    set((s) => {
      const sessions = s.sessions.filter((ss) => ss.session_id !== id)
      const currentSessionId = s.currentSessionId === id ? (sessions[0]?.session_id ?? null) : s.currentSessionId
      return { sessions, currentSessionId, messages: currentSessionId === id ? [] : s.messages }
    })
  },

  addUserMessage(content: string) {
    set((s) => ({ messages: [...s.messages, { role: 'user', content }] }))
  },

  appendAssistantPart(part) {
    if (part.type === 'thinking') return
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        const parts = [...(last.parts || []), part]
        const contentText = parts.filter((p) => p.type === 'content').map((p) => p.content || '').join('')
        msgs[msgs.length - 1] = { ...last, parts, content: contentText }
      } else {
        msgs.push({ role: 'assistant', content: part.content || '', parts: [part] })
      }

      // Auto-open canvas on code/file tool calls
      if (part.type === 'tool_result' && part.content) {
        s.canvasOpen = true
        s.canvasContent = { type: 'code', data: { filename: part.name || 'output', content: part.content } }
      }

      return { messages: msgs }
    })
  },

  finalizeAssistantMessage() {},

  setStreaming(v) { set({ streaming: v }) },
  setCanvasOpen(v) { set({ canvasOpen: v }) },
  setCanvasContent(c) { set({ canvasContent: c }) },
}))
```

- [ ] **Step 2: 更新 types.ts 移除 NavPage**

修改 `Coder/web/src/types.ts`，删除 `NavPage` 类型:

```typescript
// 删除: export type NavPage = 'chat' | 'knowledge' | 'sop' | 'skills' | 'multi-agent' | 'mcp'
```

- [ ] **Step 3: 重写 ChatPage**

修改 `Coder/web/src/pages/ChatPage.tsx`:

```typescript
import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { streamChat, stopGeneration } from '../api/chat'
import { ChatInput } from '../components/chat/ChatInput'
import { MessageList } from '../components/chat/MessageList'
import { CanvasPanel } from '../components/chat/CanvasPanel'
import { PanelRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ChatPage() {
  const messages = useChatStore((s) => s.messages)
  const streaming = useChatStore((s) => s.streaming)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const addUserMessage = useChatStore((s) => s.addUserMessage)
  const appendAssistantPart = useChatStore((s) => s.appendAssistantPart)
  const createSession = useChatStore((s) => s.createSession)
  const canvasOpen = useChatStore((s) => s.canvasOpen)
  const setCanvasOpen = useChatStore((s) => s.setCanvasOpen)

  const [input, setInput] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!currentSessionId) createSession()
  }, [currentSessionId, createSession])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming || !currentSessionId) return
    setInput('')
    addUserMessage(text)

    const controller = new AbortController()
    abortRef.current = controller
    setStreaming(true)

    try {
      for await (const event of streamChat(text, currentSessionId, controller.signal)) {
        appendAssistantPart(event)
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        appendAssistantPart({ type: 'content', content: '\n\n[回答已停止]' })
      } else {
        appendAssistantPart({ type: 'error', content: String(err) })
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleStop = async () => {
    abortRef.current?.abort()
    if (currentSessionId) await stopGeneration(currentSessionId)
    setStreaming(false)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col p-6">
        <MessageList messages={messages} streaming={streaming} />
        <ChatInput value={input} onChange={setInput} onSend={handleSend} onStop={handleStop} streaming={streaming} />
      </div>

      {!canvasOpen && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 bg-slate-900 border border-slate-800"
          onClick={() => setCanvasOpen(true)}
        >
          <PanelRight className="h-4 w-4" />
        </Button>
      )}

      <CanvasPanel />
    </div>
  )
}
```

- [ ] **Step 4: 将 ChatPage 挂载到路由**

修改 `App.tsx` imports:

```typescript
import { ChatPage } from './pages/ChatPage'
```

将对应 route 替换为: `<Route path="/chat" element={<ChatPage />} />`

- [ ] **Step 5: Commit**

```bash
git add Coder/web/src/pages/ChatPage.tsx Coder/web/src/stores/chatStore.ts Coder/web/src/types.ts Coder/web/src/App.tsx
git commit -m "refactor: ChatPage with canvas layout, add canvas state to store"
```

---

## Phase 5: 其余页面迁移

### Task 11: 重写 KnowledgePage

**Files:**
- Modify: `Coder/web/src/pages/KnowledgePage.tsx`

- [ ] **Step 1: 用 Tailwind + shadcn 重写 KnowledgePage**

```typescript
import { useState, useCallback } from 'react'
import { api } from '../api/client'
import type { KnowledgeResult } from '../types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, Search, FileText } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'

type Tab = 'upload' | 'search'

export function KnowledgePage() {
  const [tab, setTab] = useState<Tab>('upload')
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<{ filename: string; chunks: number; status: string }[]>([])
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<KnowledgeResult[]>([])

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      const data = await api.uploadFiles<{ results: { filename: string; chunks: number; status: string }[] }>('/knowledge/upload', files)
      setUploadResults(data.results)
      setFiles([])
    } catch (e) {
      setUploadResults([{ filename: 'Error', chunks: 0, status: String(e) }])
    } finally { setUploading(false) }
  }, [files])

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const data = await api.post<{ results: KnowledgeResult[]; available: boolean }>('/knowledge/search', { query: query.trim(), k: 5 })
      setSearchResults(data.results)
    } catch { setSearchResults([]) } finally { setSearching(false) }
  }, [query])

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-6">知识库</h2>

      <div className="flex gap-2 mb-6 border-b border-slate-800">
        {(['upload', 'search'] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px]
              ${tab === t ? 'text-blue-400 border-blue-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}`}>
            {t === 'upload' ? '上传文档' : '检索测试'}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader><CardTitle className="text-sm">上传文档到知识库</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <label className="flex flex-col items-center gap-3 p-10 border-2 border-dashed border-slate-700 hover:border-slate-500 rounded-xl cursor-pointer transition-colors">
              <Upload className="h-8 w-8 text-slate-600" />
              <span className="text-sm text-slate-400">拖拽或点击选择文件</span>
              <span className="text-xs text-slate-600">支持 .txt .md .pdf .docx</span>
              <input type="file" multiple accept=".txt,.md,.pdf,.docx" className="hidden"
                onChange={(e) => setFiles(Array.from(e.target.files || []))} />
            </label>
            {files.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <FileText className="h-3.5 w-3.5" /> 已选择 {files.length} 个文件: {files.map((f) => f.name).join(', ')}
              </div>
            )}
            <Button onClick={handleUpload} disabled={files.length === 0 || uploading} className="bg-blue-600 hover:bg-blue-500">
              {uploading ? '导入中...' : '导入到知识库'}
            </Button>
            {uploadResults.length > 0 && uploadResults.map((r, i) => (
              <div key={i} className={`text-xs px-3 py-2 rounded-lg ${r.status === 'imported' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                {r.filename}: {r.status === 'imported' ? `${r.chunks} 个文档块已导入` : r.status}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === 'search' && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader><CardTitle className="text-sm">检索知识</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="输入检索关键词..."
                className="flex-1 bg-slate-950 border-slate-700 text-sm" onKeyDown={(e) => e.key === 'Enter' && handleSearch()} />
              <Button onClick={handleSearch} disabled={!query.trim() || searching} className="bg-blue-600 hover:bg-blue-500">
                {searching ? '检索中...' : '搜索'}
              </Button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-3">
                {searchResults.map((r, i) => (
                  <Card key={i} className="bg-slate-950 border-slate-800">
                    <CardContent className="p-4 space-y-2">
                      <div className="flex gap-2">
                        <Badge variant="secondary" className="text-[10px]">来源: {r.metadata.filename}</Badge>
                        <Badge variant="secondary" className="text-[10px]">章节: {r.metadata.section || '-'}</Badge>
                        <Badge variant="secondary" className="text-[10px]">相关度: {r.metadata.relevance_score}</Badge>
                      </div>
                      <pre className="text-xs text-slate-400 whitespace-pre-wrap">{r.content}</pre>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
            {searchResults.length === 0 && !searching && query && (
              <EmptyState title="未找到相关结果" />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 挂载路由**

```typescript
// In App.tsx:
import { KnowledgePage } from './pages/KnowledgePage'
// Replace route placeholder with: <Route path="/knowledge" element={<KnowledgePage />} />
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/pages/KnowledgePage.tsx Coder/web/src/App.tsx
git commit -m "refactor: KnowledgePage with Tailwind, drag-drop upload zone"
```

### Task 12: 重写 SkillsPage

**Files:**
- Modify: `Coder/web/src/pages/SkillsPage.tsx`

- [ ] **Step 1: 用 Tailwind + shadcn 重写 SkillsPage，用 Sheet 替代 alert()**

```typescript
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
import { Wrench, Upload } from 'lucide-react'

// ... keep existing interfaces SkillUploadResult, Tab ...

export function SkillsPage() {
  const [tab, setTab] = useState<'list' | 'upload'>('list')
  const [skills, setSkills] = useState<SkillMeta[]>([])
  const [loading, setLoading] = useState(true)
  // ... keep existing state for mdUpload, jsonInput etc ...
  const [mdFile, setMdFile] = useState<File | null>(null)
  const [mdUploading, setMdUploading] = useState(false)
  const [mdResult, setMdResult] = useState<SkillUploadResult | null>(null)
  const [mdError, setMdError] = useState('')
  const [jsonInput, setJsonInput] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')
  const [uploadErr, setUploadErr] = useState(false)
  const [detailSkill, setDetailSkill] = useState<Record<string, unknown> | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const uploadFormRef = useRef<HTMLFormElement>(null)

  const loadSkills = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ skills: SkillMeta[] }>('/skills/')
      setSkills(data.skills)
    } catch { setSkills([]) } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadSkills() }, [loadSkills])

  const handleMdUpload = async () => {
    if (!mdFile) return
    setMdUploading(true)
    setMdResult(null)
    setMdError('')
    const formData = new FormData()
    formData.append('file', mdFile)
    try {
      const res = await fetch('/api/skills/upload-file', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) setMdError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      else { setMdResult(data as SkillUploadResult); setMdFile(null); if (uploadFormRef.current) uploadFormRef.current.reset(); loadSkills() }
    } catch (e) { setMdError(String(e)) } finally { setMdUploading(false) }
  }

  const handleJsonUpload = async () => {
    try {
      const skillJson = JSON.parse(jsonInput)
      await api.post('/skills/upload', { skill_json: skillJson })
      setUploadMsg('上传成功'); setUploadErr(false); setJsonInput(''); loadSkills()
    } catch { setUploadMsg('JSON 格式错误'); setUploadErr(true) }
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

  if (loading) return <div className="p-6 text-slate-500 text-sm">加载中...</div>

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-6">Skills</h2>

      <div className="flex gap-2 mb-6 border-b border-slate-800">
        {(['list', 'upload'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px]
              ${tab === t ? 'text-blue-400 border-blue-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}`}>
            {t === 'list' ? '已安装' : '上传 Skill'}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <div className="space-y-6">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 space-y-3">
              <h3 className="text-sm font-medium">上传 Markdown 文件</h3>
              <form ref={uploadFormRef}>
                <Input type="file" accept=".md" onChange={(e) => setMdFile(e.target.files?.[0] || null)}
                  className="bg-slate-950 border-slate-700 text-sm file:bg-slate-800 file:text-slate-300 file:border-0 file:mr-3" />
              </form>
              {mdFile && <p className="text-xs text-slate-400">已选择: {mdFile.name} ({(mdFile.size / 1024).toFixed(1)} KB)</p>}
              <Button onClick={handleMdUpload} disabled={!mdFile || mdUploading} className="bg-blue-600 hover:bg-blue-500">
                {mdUploading ? '解析中...' : '上传并解析'}
              </Button>
              {mdError && <div className="text-xs px-3 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">{mdError}</div>}
              {mdResult && (
                <div className="space-y-3 mt-4">
                  <div className="text-xs px-3 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Skill "{mdResult.display_name}" 已成功安装</div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-slate-950 rounded-lg p-3 text-center"><div className="text-lg font-bold text-blue-400">{mdResult.name}</div><div className="text-[10px] text-slate-500">名称</div></div>
                    <div className="bg-slate-950 rounded-lg p-3 text-center"><div className="text-lg font-bold text-blue-400">{mdResult.category}</div><div className="text-[10px] text-slate-500">分类</div></div>
                    <div className="bg-slate-950 rounded-lg p-3 text-center"><div className="text-lg font-bold text-blue-400">{mdResult.version || '1.0.0'}</div><div className="text-[10px] text-slate-500">版本</div></div>
                  </div>
                  {mdResult.description && <p className="text-xs text-slate-400"><strong>描述</strong>: {mdResult.description}</p>}
                  {mdResult.tags && mdResult.tags.length > 0 && <div className="flex gap-1">{mdResult.tags.map((t: string) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}</div>}
                  {mdResult.has_code && <div className={`text-xs px-3 py-2 rounded-lg ${mdResult.code_ok ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>{mdResult.code_ok ? '代码验证通过' : `代码验证未通过: ${mdResult.code_msg}`}</div>}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 space-y-3">
              <h3 className="text-sm font-medium">或粘贴 JSON</h3>
              <Textarea rows={10} value={jsonInput} onChange={(e) => setJsonInput(e.target.value)}
                placeholder='{"name": "my_skill", ...}' className="bg-slate-950 border-slate-700 text-sm font-mono" />
              <Button onClick={handleJsonUpload} className="bg-blue-600 hover:bg-blue-500">上传 JSON</Button>
              {uploadMsg && (
                <div className={`text-xs px-3 py-2 rounded-lg ${uploadErr ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
                  {uploadMsg}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === 'list' && (
        skills.length === 0 ? (
          <EmptyState icon={Wrench} title="暂无已安装的 Skill" description="请先上传一个 Skill" />
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {skills.map((s) => (
              <Card key={s.name} className={`bg-slate-900 border-slate-800 ${!s.enabled ? 'opacity-50' : ''}`}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold">{s.display_name} <code className="text-[11px] text-slate-500">({s.name})</code></h4>
                      <p className="text-xs text-slate-500 mt-1">{s.description}</p>
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${s.enabled ? 'border-emerald-500/30 text-emerald-400' : 'border-slate-700 text-slate-500'}`}>
                      {s.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  <div className="flex gap-1.5">
                    <Badge variant="secondary" className="text-[10px]">{s.category}</Badge>
                    {s.tags.map((t) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="text-xs h-7 bg-slate-800 border-slate-700 hover:bg-slate-700" onClick={() => handleViewDetail(s.name)}>详情</Button>
                    <Button variant="outline" size="sm" className="text-xs h-7 bg-slate-800 border-slate-700 hover:bg-slate-700" onClick={() => handleToggle(s.name, s.enabled)}>{s.enabled ? '禁用' : '启用'}</Button>
                    <Button variant="ghost" size="sm" className="text-xs h-7 text-red-400 hover:text-red-300 hover:bg-red-500/10 ml-auto" onClick={() => handleDelete(s.name)}>删除</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="bg-slate-950 border-l border-slate-800 text-slate-200 w-[400px] sm:max-w-[400px]">
          <SheetHeader><SheetTitle className="text-slate-200">Skill 详情</SheetTitle></SheetHeader>
          <pre className="mt-6 text-xs text-slate-400 whitespace-pre-wrap overflow-x-auto">{JSON.stringify(detailSkill, null, 2)}</pre>
        </SheetContent>
      </Sheet>
    </div>
  )
}
```

- [ ] **Step 2: 挂载路由**

```typescript
import { SkillsPage } from './pages/SkillsPage'
// Replace: <Route path="/skills" element={<SkillsPage />} />
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/pages/SkillsPage.tsx Coder/web/src/App.tsx
git commit -m "refactor: SkillsPage with Tailwind card grid, Sheet detail view replacing alert"
```

### Task 13: 重写 MultiAgentPage 和 MCPPage

**Files:**
- Modify: `Coder/web/src/pages/MultiAgentPage.tsx`
- Modify: `Coder/web/src/pages/MCPPage.tsx`

- [ ] **Step 1: 用 Tailwind 重写 MultiAgentPage**

```typescript
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
      const data = await api.post<OrchestratorResult>('/agent-orchestrator/execute', { task: task.trim() })
      setResult(data)
    } catch (e) {
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0 })
    } finally { setExecuting(false) }
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-2">智能任务协调者</h2>
      <p className="text-sm text-slate-500 mb-6">Agent-as-Tool 架构 — 专家智能体按需调用，自动协调</p>

      <Card className="bg-slate-900 border-slate-800 max-w-2xl">
        <CardHeader><CardTitle className="text-sm">执行任务</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <Textarea rows={3} value={task} onChange={(e) => setTask(e.target.value)}
            placeholder="描述你的任务，AI 将自动调用最适合的专家 Agent 执行..."
            className="bg-slate-950 border-slate-700 text-sm resize-none" />
          <Button onClick={handleExecute} disabled={!task.trim() || executing} className="bg-blue-600 hover:bg-blue-500">
            {executing ? '执行中...' : '执行任务'}
          </Button>

          {result && (
            <div className="mt-4 space-y-4">
              <div className={`flex items-center gap-2 text-sm ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                {result.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {result.success ? `执行成功 (耗时: ${result.duration_seconds.toFixed(1)}s)` : `执行失败: ${result.error}`}
              </div>
              {result.answer && (
                <Card className="bg-slate-950 border-slate-800">
                  <CardContent className="p-4">
                    <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{result.answer}</p>
                  </CardContent>
                </Card>
              )}
              <div className="flex gap-2">
                <Badge variant="secondary" className="text-[10px]">Coder Agent</Badge>
                <Badge variant="secondary" className="text-[10px]">Searcher Agent</Badge>
                <Badge variant="secondary" className="text-[10px]">Ops Agent</Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: 用 Tailwind 重写 MCPPage**

```typescript
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { MCPServer, MCPRegistryItem, MCPTool } from '../types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { EmptyState } from '@/components/shared/EmptyState'
import { Plug, Search, Plus, Trash2, Power, PowerOff, RefreshCw } from 'lucide-react'

type Tab = 'marketplace' | 'installed'

export function MCPPage() {
  const [tab, setTab] = useState<Tab>('marketplace')
  const [registry, setRegistry] = useState<MCPRegistryItem[]>([])
  const [registryLoading, setRegistryLoading] = useState(true)
  const [registrySearch, setRegistrySearch] = useState('')
  const [servers, setServers] = useState<MCPServer[]>([])
  const [serversLoading, setServersLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formTransport, setFormTransport] = useState<'stdio' | 'sse'>('stdio')
  const [formCommand, setFormCommand] = useState('')
  const [formArgs, setFormArgs] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [testResult, setTestResult] = useState<{ success: boolean; error: string; tools: MCPTool[] } | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  const loadRegistry = useCallback(async () => {
    setRegistryLoading(true)
    try {
      const data = await api.get<{ servers: MCPRegistryItem[] }>(`/mcp/registry${registrySearch ? `?search=${encodeURIComponent(registrySearch)}` : ''}`)
      setRegistry(data.servers)
    } catch { setRegistry([]) } finally { setRegistryLoading(false) }
  }, [registrySearch])

  const loadServers = useCallback(async () => {
    setServersLoading(true)
    try {
      const data = await api.get<{ servers: MCPServer[] }>('/mcp/servers')
      setServers(data.servers)
    } catch { setServers([]) } finally { setServersLoading(false) }
  }, [])

  useEffect(() => {
    if (tab === 'marketplace') loadRegistry()
    else loadServers()
  }, [tab, loadRegistry, loadServers])

  const handleInstall = async (item: MCPRegistryItem) => {
    try {
      await api.post('/mcp/servers', { name: item.name, display_name: item.name, description: item.description, transport: item.transport, command: item.command || null, args: item.args || [], url: item.url || null })
      setTab('installed')
    } catch (e: any) { alert(`Install failed: ${e.message}`) }
  }

  const handleAdd = async () => {
    if (!formName.trim()) { setFormError('Name required'); return }
    setFormSubmitting(true)
    setFormError('')
    try {
      await api.post('/mcp/servers', { name: formName.trim(), display_name: formName.trim(), transport: formTransport, command: formTransport === 'stdio' ? formCommand.trim() : null, args: formArgs.trim() ? formArgs.trim().split(/\s+/) : [], url: formTransport === 'sse' ? formUrl.trim() : null })
      setShowForm(false); setFormName(''); setFormCommand(''); setFormArgs(''); setFormUrl('')
      setTab('installed')
    } catch (e: any) { setFormError(e.message) } finally { setFormSubmitting(false) }
  }

  const handleToggle = async (s: MCPServer) => {
    await api.patch(`/mcp/servers/${s.id}`, { enabled: !s.enabled })
    loadServers()
  }

  const handleDelete = async (s: MCPServer) => {
    if (!confirm(`Delete "${s.display_name}"?`)) return
    await api.del(`/mcp/servers/${s.id}`)
    loadServers()
  }

  const handleTest = async (s: MCPServer) => {
    setTesting(s.id)
    try {
      const data = await api.post<{ success: boolean; error: string; tools: MCPTool[] }>(`/mcp/servers/${s.id}/test`)
      setTestResult(data)
    } catch (e: any) { setTestResult({ success: false, error: e.message, tools: [] }) } finally { setTesting(null) }
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-6">MCP 管理</h2>

      <div className="flex gap-2 mb-6 border-b border-slate-800">
        {(['marketplace', 'installed'] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px]
              ${tab === t ? 'text-blue-400 border-blue-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}`}>
            {t === 'marketplace' ? '市场' : '已安装'}
          </button>
        ))}
      </div>

      {tab === 'marketplace' && (
        <>
          <div className="flex gap-3 mb-6">
            <Input value={registrySearch} onChange={(e) => setRegistrySearch(e.target.value)}
              placeholder="搜索 MCP Server..." className="max-w-sm bg-slate-900 border-slate-700 text-sm"
              onKeyDown={(e) => e.key === 'Enter' && loadRegistry()} />
            <Button variant="outline" onClick={loadRegistry} className="bg-slate-800 border-slate-700 hover:bg-slate-700">
              <Search className="h-3.5 w-3.5" />
            </Button>
          </div>
          {registryLoading ? <p className="text-sm text-slate-500">加载中...</p> :
           registry.length === 0 ? <EmptyState icon={Plug} title="暂无可用 MCP Server" /> : (
            <div className="grid grid-cols-3 gap-4">
              {registry.map((item) => (
                <Card key={item.id || item.name} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
                  <CardContent className="p-5 space-y-3">
                    <h4 className="text-sm font-semibold">{item.name}</h4>
                    <p className="text-xs text-slate-500 leading-relaxed">{item.description}</p>
                    <div className="flex gap-2">
                      <Badge variant="secondary" className="text-[10px]">{item.transport}</Badge>
                      {item.category && <Badge variant="secondary" className="text-[10px]">{item.category}</Badge>}
                    </div>
                    <Button onClick={() => handleInstall(item)} className="w-full bg-blue-600/80 hover:bg-blue-600 text-xs h-8" size="sm">安装</Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'installed' && (
        <>
          <div className="flex gap-3 mb-6">
            <Button variant="outline" onClick={() => setShowForm(!showForm)} className="bg-slate-800 border-slate-700 hover:bg-slate-700 text-sm">
              {showForm ? '取消' : <><Plus className="h-3.5 w-3.5 mr-1" /> 手动添加</>}
            </Button>
            <Button variant="outline" onClick={() => {}} className="bg-slate-800 border-slate-700 hover:bg-slate-700 text-sm">导入配置</Button>
          </div>

          {showForm && (
            <Card className="bg-slate-900 border-slate-800 mb-6">
              <CardContent className="p-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Input placeholder="Name" value={formName} onChange={(e) => setFormName(e.target.value)} className="bg-slate-950 border-slate-700 text-sm" />
                  <select value={formTransport} onChange={(e) => setFormTransport(e.target.value as 'stdio' | 'sse')}
                    className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200">
                    <option value="stdio">stdio</option>
                    <option value="sse">SSE</option>
                  </select>
                </div>
                {formTransport === 'stdio' ? (
                  <div className="grid grid-cols-2 gap-3">
                    <Input placeholder="Command" value={formCommand} onChange={(e) => setFormCommand(e.target.value)} className="bg-slate-950 border-slate-700 text-sm" />
                    <Input placeholder="Args (空格分隔)" value={formArgs} onChange={(e) => setFormArgs(e.target.value)} className="bg-slate-950 border-slate-700 text-sm" />
                  </div>
                ) : (
                  <Input placeholder="URL" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} className="bg-slate-950 border-slate-700 text-sm" />
                )}
                {formError && <p className="text-xs text-red-400">{formError}</p>}
                <Button onClick={handleAdd} disabled={formSubmitting} className="bg-blue-600 hover:bg-blue-500">{formSubmitting ? '添加中...' : '添加'}</Button>
              </CardContent>
            </Card>
          )}

          {testResult && (
            <Card className={`bg-slate-900 border mb-6 ${testResult.success ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
              <CardContent className="p-4 space-y-2">
                <p className={`text-sm ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                  {testResult.success ? 'Connection OK' : `Error: ${testResult.error}`}
                </p>
                {testResult.tools.length > 0 && <ul className="text-xs text-slate-400 space-y-1">{testResult.tools.map((t) => <li key={t.name}>{t.name}: {t.description}</li>)}</ul>}
                <Button variant="ghost" size="sm" onClick={() => setTestResult(null)} className="text-xs">关闭</Button>
              </CardContent>
            </Card>
          )}

          {serversLoading ? <p className="text-sm text-slate-500">加载中...</p> :
           servers.length === 0 ? <EmptyState icon={Plug} title="暂无已安装的 MCP Server" /> : (
            <div className="space-y-3">
              {servers.map((s) => (
                <Card key={s.id} className="bg-slate-900 border-slate-800">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold">{s.display_name}</h4>
                        <p className="text-xs text-slate-500">{s.description}</p>
                        <div className="flex gap-2 mt-2">
                          <span className={`inline-block w-1.5 h-1.5 rounded-full ${s.status === 'connected' ? 'bg-emerald-400' : s.status === 'error' ? 'bg-red-400' : 'bg-slate-600'}`} />
                          <span className="text-[11px] text-slate-500">{s.status}</span>
                          <span className="text-[11px] text-slate-500">{s.transport}</span>
                          <span className="text-[11px] text-slate-500">{s.tool_count} tools</span>
                        </div>
                        {s.last_error && <p className="text-[11px] text-red-400">{s.last_error}</p>}
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleToggle(s)}
                          className="text-xs h-7 bg-slate-800 border-slate-700 hover:bg-slate-700">
                          {s.enabled ? <PowerOff className="h-3 w-3" /> : <Power className="h-3 w-3" />}
                          {s.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleTest(s)} disabled={testing === s.id}
                          className="text-xs h-7 bg-slate-800 border-slate-700 hover:bg-slate-700">
                          <RefreshCw className="h-3 w-3" />
                        </Button>
                        {!s.is_local && (
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(s)}
                            className="text-xs h-7 text-red-400 hover:text-red-300 hover:bg-red-500/10">
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 挂载路由**

```typescript
import { MultiAgentPage } from './pages/MultiAgentPage'
import { MCPPage } from './pages/MCPPage'
// Replace placeholders with the real components
```

- [ ] **Step 4: Commit**

```bash
git add Coder/web/src/pages/MultiAgentPage.tsx Coder/web/src/pages/MCPPage.tsx Coder/web/src/App.tsx
git commit -m "refactor: MultiAgentPage and MCPPage with Tailwind + shadcn"
```

---

## Phase 6: 清理与收尾

### Task 14: 删除旧文件和清理

**Files:**
- Delete: `Coder/web/src/App.css`
- Delete: `Coder/web/src/pages/SOPPage.tsx`
- Modify: `Coder/web/src/App.tsx` (remove SOP import)
- Modify: `Coder/web/src/stores/chatStore.ts` (remove setNavPage if any)

- [ ] **Step 1: 删除旧 CSS 和 SOP 页面**

```bash
cd /d/PyCharm/AI/Coder/web
rm src/App.css
rm src/pages/SOPPage.tsx
```

- [ ] **Step 2: 确保 App.tsx 无残留引用**

检查 `App.tsx`:
- 无 `./App.css` import
- 无 `SOPPage` import
- 无 `navPage` 相关逻辑

- [ ] **Step 3: 删除 node_modules 并重新安装**

```bash
cd Coder/web && rm -rf node_modules && npm install
```

- [ ] **Step 4: 启动验证**

```bash
npm run dev
```

验证: 所有 5 个页面正常加载、路由跳转正常、侧边栏折叠/展开正常、主题切换正常、对话功能正常。

- [ ] **Step 5: Commit**

```bash
git add -u Coder/web/
git commit -m "chore: remove App.css, SOPPage, clean up old code"
```

### Task 15: 最终验证和构建测试

- [ ] **Step 1: TypeScript 类型检查**

```bash
cd Coder/web && npx tsc --noEmit
```

修复任何类型错误。

- [ ] **Step 2: 生产构建测试**

```bash
cd Coder/web && npm run build
```

确保构建成功，无错误。

- [ ] **Step 3: 完整手动测试**

- 对话页: 发送消息 → 查看 SSE 流式响应 → 工具调用折叠 → 画布面板展开
- 知识库: 上传文档 → 检索测试
- Skills: 上传 Markdown → 查看详情 Sheet → 启用/禁用/删除
- 多智能体: 输入任务 → 执行 → 查看结果
- MCP: 市场搜索 → 安装 → 已安装列表 → 测试连接
- 侧边栏: 折叠/展开 → 导航切换 → 会话切换/删除
- 主题: 深色/浅色切换 → 刷新后持久化

- [ ] **Step 4: Commit**

```bash
git add -A Coder/web/
git commit -m "chore: final TypeScript fixes and build verification"
```

---

## 依赖清单

安装完成后 `package.json` dependencies 应为:

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "zustand": "^5.0.0",
    "lucide-react": "^latest",
    "next-themes": "^latest",
    "class-variance-authority": "^latest",
    "clsx": "^latest",
    "tailwind-merge": "^latest"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/node": "^latest",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^6.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0"
  }
}
```
