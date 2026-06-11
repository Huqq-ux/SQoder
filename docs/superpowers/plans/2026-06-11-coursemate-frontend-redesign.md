# CourseMate 前端视觉重设计 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 CourseMate 前端从通用聊天工具升级为有质感、双主题、三栏布局的课程学习工作台。

**Architecture:** CSS 变量驱动主题系统（`[data-theme="light"]`），三栏布局（IconNav 52px + 可拖拽 Sidebar 260px + 主工作区），保留 shadcn/ui 组件库，删除 MultiAgent/MCP/Skills 独立页面。

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind CSS 4 + shadcn/ui + zustand + next-themes + react-router-dom v6 + lucide-react

---

## File Structure Map

```
Coder/web/src/
├── index.css                          [MODIFY] New theme variables + animations
├── App.tsx                            [MODIFY] Three-column layout, updated routes
├── main.tsx                           [NO CHANGE]
├── types.ts                           [MODIFY] Add course stats types
├── stores/
│   └── chatStore.ts                   [NO CHANGE]
├── api/
│   ├── client.ts                      [NO CHANGE]
│   ├── chat.ts                        [NO CHANGE]
│   └── sessions.ts                    [NO CHANGE]
├── components/
│   ├── layout/
│   │   ├── IconNav.tsx                [CREATE] Icon nav bar + theme toggle
│   │   ├── Sidebar.tsx                [MODIFY] Course-centric sidebar
│   │   ├── SidebarContext.tsx          [MODIFY] Support persistent width
│   │   └── TopNav.tsx                 [DELETE] Replaced by IconNav
│   ├── course/
│   │   ├── NotesView.tsx              [CREATE] Notes grid with search
│   │   └── WrongAnswersView.tsx       [CREATE] Wrong answers with add form
│   ├── chat/
│   │   ├── MessageList.tsx            [MODIFY] New bubble styling, citations
│   │   ├── ChatInput.tsx              [MODIFY] Updated styling
│   │   ├── ChatMessage.tsx            [MODIFY] Citation display
│   │   ├── CanvasPanel.tsx            [NO CHANGE]
│   │   └── ToolCallAccordion.tsx      [NO CHANGE]
│   ├── KnowledgeGraph.tsx             [MODIFY] Mastery-based node colors, legend
│   ├── ChatMessage.tsx                [MODIFY] Citation display
│   └── shared/
│       └── EmptyState.tsx             [NO CHANGE]
├── pages/
│   ├── HomePage.tsx                   [CREATE] Stats + course list
│   ├── CoursePage.tsx                 [MODIFY] New header layout, refactored tabs
│   ├── ChatPage.tsx                   [MODIFY] Updated styling for standalone use
│   ├── KnowledgePage.tsx              [MODIFY] Updated with new design
│   ├── SettingsPage.tsx               [CREATE] Category nav + settings form
│   ├── SkillsPage.tsx                 [DELETE] Merge into SettingsPage
│   ├── MultiAgentPage.tsx             [DELETE] Remove from app
│   └── MCPPage.tsx                    [DELETE] Remove from app
└── ui/                                [NO CHANGE] shadcn components
```

---

### Task 1: 主题系统 CSS 变量 + 动画

**Files:**
- Modify: `Coder/web/src/index.css`

- [ ] **Step 1: 用新的主题变量替换 CSS**

将 `Coder/web/src/index.css` 中的 `:root` 和 `.dark` 块替换为以下内容：

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@import "@fontsource-variable/geist";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --font-heading: var(--font-sans);
  --font-sans: 'Geist Variable', sans-serif;
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --color-foreground: var(--foreground);
  --color-background: var(--background);
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
  --radius-3xl: calc(var(--radius) * 2.2);
  --radius-4xl: calc(var(--radius) * 2.6);
}

@layer base {
  * {
    margin: 0; padding: 0; box-sizing: border-box;
    @apply border-border outline-ring/50;
  }
  body {
    font-family: 'Geist Variable', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    @apply antialiased;
    background: var(--bg);
    color: var(--text);
    transition: background 0.4s, color 0.4s;
  }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
  html { @apply font-sans; }
}

/* ====== Theme: Dark (default) ====== */
:root {
  --bg: #0a0a0f;
  --surface: #12121a;
  --card: #181825;
  --border: #232336;
  --text: #e4e4ec;
  --text-dim: #8888a0;
  --accent: #6366f1;
  --accent-glow: #818cf8;
  --gradient-to: #a78bfa;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
  --shadow: rgba(0,0,0,.4);
  --shadow-sm: rgba(0,0,0,.3);
  --accent-bg: rgba(99,102,241,.15);
  --accent-bg2: rgba(139,92,246,.1);
  --accent-border: rgba(99,102,241,.25);
  --accent-bg-light: rgba(99,102,241,.08);
  --tag-mastered: rgba(34,197,94,.12);
  --tag-learning: rgba(245,158,11,.12);
  --tag-new: rgba(99,102,241,.12);
  --user-bubble-bg: linear-gradient(135deg, rgba(99,102,241,.2), rgba(139,92,246,.15));
  --user-bubble-border: rgba(99,102,241,.25);
  --hover-border: rgba(99,102,241,.4);
  --logo-gradient: linear-gradient(135deg, var(--accent-glow), var(--gradient-to));
  --pct-gradient: linear-gradient(135deg, var(--accent-glow), var(--gradient-to));
  --shimmer-overlay: rgba(255,255,255,.4);
  --btn-hover-bg: var(--card);
  --tab-active-bg: var(--surface);
  --tab-active-shadow: 0 2px 8px rgba(0,0,0,.3);
  --icon-active-shadow: 0 0 16px rgba(99,102,241,.4);
  --kp-hover-shadow: 0 8px 32px rgba(0,0,0,.4);
}

/* ====== Theme: Light ====== */
[data-theme="light"] {
  --bg: #f5f5f7;
  --surface: #ffffff;
  --card: #f0f0f5;
  --border: #e5e5ea;
  --text: #1c1c1e;
  --text-dim: #8e8e93;
  --accent: #0d9488;
  --accent-glow: #14b8a6;
  --gradient-to: #22d3ee;
  --shadow: rgba(0,0,0,.08);
  --shadow-sm: rgba(0,0,0,.05);
  --accent-bg: rgba(13,148,136,.08);
  --accent-bg2: rgba(20,184,166,.05);
  --accent-border: rgba(13,148,136,.2);
  --accent-bg-light: rgba(13,148,136,.06);
  --tag-mastered: rgba(34,197,94,.1);
  --tag-learning: rgba(245,158,11,.1);
  --tag-new: rgba(13,148,136,.1);
  --user-bubble-bg: linear-gradient(135deg, rgba(13,148,136,.12), rgba(20,184,166,.08));
  --user-bubble-border: rgba(13,148,136,.2);
  --hover-border: rgba(13,148,136,.5);
  --shimmer-overlay: rgba(13,148,136,.15);
  --btn-hover-bg: #e8e8ed;
  --tab-active-bg: #ffffff;
  --tab-active-shadow: 0 2px 8px rgba(0,0,0,.08);
  --icon-active-shadow: 0 0 16px rgba(13,148,136,.25);
  --kp-hover-shadow: 0 8px 24px rgba(0,0,0,.08);
}

/* ====== Shadcn theme bridge (backwards compat) ====== */
:root {
  --background: var(--bg);
  --foreground: var(--text);
  --card: var(--surface);
  --card-foreground: var(--text);
  --popover: var(--surface);
  --popover-foreground: var(--text);
  --primary: var(--accent);
  --primary-foreground: #ffffff;
  --secondary: var(--card);
  --secondary-foreground: var(--text);
  --muted: var(--card);
  --muted-foreground: var(--text-dim);
  --accent: var(--card);
  --accent-foreground: var(--text);
  --destructive: var(--red);
  --border: var(--border);
  --input: var(--border);
  --ring: var(--accent-glow);
  --radius: 0.625rem;
  --sidebar: var(--surface);
  --sidebar-foreground: var(--text);
  --sidebar-primary: var(--accent);
  --sidebar-primary-foreground: #ffffff;
  --sidebar-accent: var(--card);
  --sidebar-accent-foreground: var(--text);
  --sidebar-border: var(--border);
  --sidebar-ring: var(--accent-glow);
}

/* ====== Animations ====== */
@keyframes shimmer {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 8px rgba(34,197,94,.3); }
  50% { box-shadow: 0 0 20px rgba(34,197,94,.7); }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-shimmer { animation: shimmer 2s infinite; }
.animate-pulse-dot { animation: pulse-dot 2s infinite; }
.animate-fade-in-up { animation: fadeInUp 0.4s ease-out both; }

/* Progress bar shimmer */
.progress-shimmer::after {
  content: "";
  position: absolute; right: 0; top: 0;
  width: 20px; height: 100%;
  background: linear-gradient(90deg, transparent, var(--shimmer-overlay));
  animation: shimmer 2s infinite;
}

/* KP card top bar */
.kp-card-top-bar {
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--gradient-to));
  transform: scaleX(0); transition: transform 0.35s;
}

/* mammoth .docx preview styles */
.docx-content h1 { font-size: 1.4rem; font-weight: 700; margin: 1.2rem 0 0.4rem; }
.docx-content h2 { font-size: 1.15rem; font-weight: 600; margin: 1rem 0 0.3rem; }
.docx-content h3 { font-size: 1.05rem; font-weight: 600; margin: 0.8rem 0 0.2rem; }
.docx-content p { margin: 0.4rem 0; line-height: 1.7; }
.docx-content ul, .docx-content ol { margin: 0.4rem 0; padding-left: 1.5rem; }
.docx-content li { margin: 0.15rem 0; }
.docx-content table {
  width: 100%; border-collapse: collapse; margin: 0.6rem 0; font-size: 0.8rem;
}
.docx-content th, .docx-content td {
  border: 1px solid #d1d5db; padding: 0.35rem 0.5rem; text-align: left;
}
.dark .docx-content th, .dark .docx-content td { border-color: #374151; }
.docx-content th { background: #f3f4f6; font-weight: 600; }
.dark .docx-content th { background: #1f2937; }
.docx-content img { max-width: 100%; height: auto; margin: 0.5rem 0; }
.docx-content blockquote {
  border-left: 3px solid #d1d5db; padding: 0.3rem 0 0.3rem 1rem;
  margin: 0.5rem 0; color: #6b7280;
}
```

- [ ] **Step 2: 验证前端能正常启动**

```bash
cd Coder/web && npm run dev
```

检查浏览器控制台是否有 CSS 报错。

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/index.css
git commit -m "feat: add dual-theme CSS variables and animations"
```

---

### Task 2: IconNav 图标导航栏 + 主题切换

**Files:**
- Create: `Coder/web/src/components/layout/IconNav.tsx`
- Modify: `Coder/web/src/components/layout/SidebarContext.tsx`
- Modify: `Coder/web/src/App.tsx`

- [ ] **Step 1: 创建 IconNav 组件**

```tsx
// Coder/web/src/components/layout/IconNav.tsx
import { NavLink, useLocation } from 'react-router-dom';
import { BookOpen, MessageSquare, FolderOpen, Wrench } from 'lucide-react';
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from '@/components/ui/tooltip';

const navItems = [
  { to: '/', icon: BookOpen, label: '课程' },
  { to: '/chat', icon: MessageSquare, label: '对话' },
  { to: '/knowledge', icon: FolderOpen, label: '知识库' },
  { to: '/settings', icon: Wrench, label: '设置' },
];

export function IconNav() {
  const location = useLocation();

  function toggleTheme() {
    const el = document.documentElement;
    const current = el.getAttribute('data-theme');
    el.setAttribute('data-theme', current === 'light' ? '' : 'light');
    localStorage.setItem('theme', current === 'light' ? 'dark' : 'light');
  }

  return (
    <nav
      className="flex flex-col items-center gap-1.5 py-3 shrink-0 border-r"
      style={{
        width: 52,
        background: 'var(--surface)',
        borderColor: 'var(--border)',
        transition: 'background 0.4s, border-color 0.4s',
      }}
    >
      {navItems.map(({ to, icon: Icon, label }) => {
        const isActive = to === '/'
          ? location.pathname === '/' || location.pathname.startsWith('/course/')
          : location.pathname.startsWith(to);

        const link = (
          <NavLink
            key={to}
            to={to}
            className="w-9 h-9 rounded-[10px] flex items-center justify-center transition-all duration-200"
            style={{
              color: isActive ? '#fff' : 'var(--text-dim)',
              background: isActive ? 'var(--accent)' : 'transparent',
              boxShadow: isActive ? 'var(--icon-active-shadow)' : 'none',
            }}
          >
            <Icon className="h-[18px] w-[18px]" />
          </NavLink>
        );

        if (!isActive) {
          return (
            <Tooltip key={to}>
              <TooltipTrigger asChild>{link}</TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          );
        }
        return link;
      })}

      {/* Theme toggle */}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={toggleTheme}
            className="w-11 h-6 rounded-xl border-[1.5px] relative transition-all duration-300 mt-auto mb-2"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
          >
            <div
              className="absolute top-[2px] w-[18px] h-[18px] rounded-full flex items-center justify-center text-[10px] transition-all duration-300"
              style={{ background: 'var(--accent)' }}
            />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">切换主题</TooltipContent>
      </Tooltip>
    </nav>
  );
}
```

注意：主题切换按钮的滑块位置需要通过 CSS 处理。在 `index.css` 末尾追加：

```css
[data-theme="light"] .theme-knob { left: 22px; }
```

并更新 IconNav 中滑块 div 添加 class `theme-knob`。

- [ ] **Step 2: 运行时从 localStorage 恢复主题**

在 `Coder/web/src/main.tsx` 中，在 `ReactDOM.createRoot` 之前添加：

```tsx
// 恢复主题
const saved = localStorage.getItem('theme');
if (saved === 'light') {
  document.documentElement.setAttribute('data-theme', 'light');
}
```

- [ ] **Step 3: 更新 SidebarContext 移除不需要的逻辑**

SidebarContext 不需要改动，保持现有拖拽功能。

- [ ] **Step 4: 更新 App.tsx 布局**

用 IconNav 替换 TopNav，删除 TopNav 的 import 和使用：

```tsx
// Coder/web/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { SidebarProvider } from './components/layout/SidebarContext'
import { IconNav } from './components/layout/IconNav'
import { Sidebar } from './components/layout/Sidebar'
import { ChatPage } from './pages/ChatPage'
import { CoursePage } from './pages/CoursePage'
import { KnowledgePage } from './pages/KnowledgePage'
import { HomePage } from './pages/HomePage'
import { SettingsPage } from './pages/SettingsPage'
import { DocxPreviewPanel } from './components/DocxPreviewPanel'

export default function App() {
  return (
    <TooltipProvider delay={0}>
      <BrowserRouter>
        <SidebarProvider>
          <AppLayout />
        </SidebarProvider>
      </BrowserRouter>
    </TooltipProvider>
  )
}

function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg)' }}>
      <IconNav />
      <Sidebar />
      <main className="flex-1 overflow-hidden relative" style={{ background: 'var(--bg)' }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/course/:slug" element={<CoursePage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
        <DocxPreviewPanel />
      </main>
    </div>
  )
}
```

删除以下 import 和使用：
- `ThemeProvider` from `next-themes`
- `TopNav`
- `SkillsPage`
- `MultiAgentPage`
- `MCPPage`
- `Navigate` (可选，如果不再需要 redirect)

- [ ] **Step 5: 删除旧文件**

```bash
rm Coder/web/src/components/layout/TopNav.tsx
rm Coder/web/src/pages/MultiAgentPage.tsx
rm Coder/web/src/pages/MCPPage.tsx
rm Coder/web/src/pages/SkillsPage.tsx
```

- [ ] **Step 6: 验证启动**

```bash
cd Coder/web && npm run dev
```

打开浏览器检查：三栏布局、图标导航、主题切换按钮（点击切换亮/暗）。

- [ ] **Step 7: Commit**

```bash
git add Coder/web/src/components/layout/IconNav.tsx Coder/web/src/components/layout/SidebarContext.tsx Coder/web/src/App.tsx Coder/web/src/main.tsx Coder/web/src/index.css
git rm Coder/web/src/components/layout/TopNav.tsx Coder/web/src/pages/MultiAgentPage.tsx Coder/web/src/pages/MCPPage.tsx Coder/web/src/pages/SkillsPage.tsx
git commit -m "feat: add IconNav with theme toggle, remove old TopNav and unused pages"
```

---

### Task 3: 课程侧栏重设计

**Files:**
- Modify: `Coder/web/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: 重写 Sidebar 组件为课程中心侧栏**

```tsx
// Coder/web/src/components/layout/Sidebar.tsx
import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSidebar } from './SidebarContext'
import { useChatStore } from '@/stores/chatStore'
import { api } from '@/api/client'
import { Plus, Search } from 'lucide-react'

interface CourseItem {
  slug: string
  name: string
  kp_total: number
  kp_mastered: number
}

export function Sidebar() {
  const { width, collapsed, setWidth } = useSidebar()
  const navigate = useNavigate()
  const sessions = useChatStore((s) => s.sessions)
  const currentSessionId = useChatStore((s) => s.currentSessionId)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)

  const [courses, setCourses] = useState<CourseItem[]>([])
  const [activeCourse, setActiveCourse] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showCourses, setShowCourses] = useState(true)

  useEffect(() => {
    loadSessions()
    api.get<{ courses: CourseItem[] }>('/courses/').then((d) => setCourses(d.courses)).catch(() => {})
  }, [loadSessions])

  // 从 URL 解析当前课程 slug
  useEffect(() => {
    const match = location.pathname.match(/^\/course\/([^/]+)/)
    setActiveCourse(match ? decodeURIComponent(match[1]) : null)
  }, [location.pathname])

  // 拖拽调整宽度
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
      setLocalW(Math.min(400, Math.max(52, startW.current + (e.clientX - startX.current))))
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

  const subNav = activeCourse
    ? [
        { key: 'qa', label: '问答', path: `/course/${activeCourse}` },
        { key: 'notes', label: '笔记', path: `/course/${activeCourse}/notes` },
        { key: 'graph', label: '知识图谱', path: `/course/${activeCourse}/graph` },
        { key: 'wrong', label: '错题本', path: `/course/${activeCourse}/wrong` },
      ]
    : []

  const filteredCourses = search
    ? courses.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : courses

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
      {/* 拖拽把手 */}
      <div
        className="absolute right-0 top-0 w-1.5 h-full cursor-ew-resize z-10 opacity-0 group-hover/sidebar:opacity-100 hover:bg-blue-400/30 active:bg-blue-500/40 transition-opacity"
        onMouseDown={onMouseDown}
      />

      <div className="p-3 space-y-4 flex-1 overflow-y-auto">
        {/* Logo */}
        <div className="flex items-center gap-2 px-2">
          <span
            className="text-[15px] font-bold"
            style={{
              background: 'var(--logo-gradient)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            CourseMate
          </span>
          <span
            className="w-2 h-2 rounded-full animate-pulse-dot"
            style={{ background: 'var(--green)' }}
          />
        </div>

        {/* 课程列表 */}
        <div>
          <div className="flex items-center justify-between px-2 mb-2">
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-dim)' }}
            >
              我的课程
            </span>
            <button
              onClick={() => navigate('/')}
              className="w-5 h-5 rounded flex items-center justify-center transition-colors"
              style={{ color: 'var(--text-dim)' }}
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* 搜索 */}
          {courses.length > 3 && (
            <div className="px-2 mb-2">
              <div
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-xs"
                style={{ background: 'var(--card)', color: 'var(--text-dim)' }}
              >
                <Search className="h-3 w-3" />
                <input
                  className="bg-transparent border-none outline-none flex-1 text-xs"
                  placeholder="搜索课程..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ color: 'var(--text)' }}
                />
              </div>
            </div>
          )}

          <div className="flex flex-col gap-0.5">
            {filteredCourses.map((c) => {
              const isActive = activeCourse === c.slug
              const masteryPct = c.kp_total > 0 ? Math.round((c.kp_mastered / c.kp_total) * 100) : 0

              return (
                <div key={c.slug}>
                  <div
                    onClick={() => navigate(`/course/${c.slug}`)}
                    className="px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 text-[13px]"
                    style={{
                      background: isActive
                        ? `linear-gradient(135deg, var(--accent-bg), var(--accent-bg2))`
                        : 'transparent',
                      color: isActive ? 'var(--text)' : 'var(--text-dim)',
                      border: isActive ? '1px solid var(--accent-border)' : '1px solid transparent',
                    }}
                  >
                    {c.name}
                    <div
                      className="text-[11px] mt-0.5"
                      style={{ color: isActive ? 'var(--accent-glow)' : 'var(--text-dim)' }}
                    >
                      {c.kp_mastered}/{c.kp_total} 知识点 · {masteryPct}%
                    </div>
                  </div>

                  {/* 子导航 */}
                  {isActive && (
                    <div className="flex flex-col gap-0.5 mt-0.5 ml-2">
                      {subNav.map((item) => {
                        const isSubActive = item.key === 'qa'
                          ? location.pathname === `/course/${activeCourse}`
                          : location.pathname === item.path
                        return (
                          <div
                            key={item.key}
                            onClick={() => navigate(item.path)}
                            className="px-3 py-1.5 rounded-md cursor-pointer text-xs transition-all duration-150"
                            style={{
                              color: isSubActive ? 'var(--accent-glow)' : 'var(--text-dim)',
                              background: isSubActive ? 'var(--accent-bg-light)' : 'transparent',
                            }}
                          >
                            {item.label}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* 底部链接 + 会话历史 */}
      {!collapsed && (
        <div
          className="border-t p-3 overflow-y-auto flex flex-col gap-0.5"
          style={{ borderColor: 'var(--border)', maxHeight: '30vh', transition: 'border-color 0.4s' }}
        >
          <div
            className="px-3 py-1.5 rounded-md text-xs cursor-pointer transition-colors"
            style={{ color: 'var(--text-dim)' }}
            onClick={() => navigate('/knowledge')}
          >
            知识库管理
          </div>
          <div
            className="px-3 py-1.5 rounded-md text-xs cursor-pointer transition-colors"
            style={{ color: 'var(--text-dim)' }}
            onClick={() => navigate('/settings')}
          >
            设置
          </div>

          {/* 会话历史 */}
          <div className="mt-3">
            <h3
              className="text-[10px] font-semibold uppercase tracking-wider px-2 mb-1"
              style={{ color: 'var(--text-dim)' }}
            >
              最近会话
            </h3>
            {sessions.slice(0, 5).map((s) => (
              <div
                key={s.session_id}
                onClick={() => switchSession(s.session_id)}
                className="px-3 py-1.5 rounded-md text-xs cursor-pointer flex items-center justify-between group/session"
                style={{
                  color: s.session_id === currentSessionId ? 'var(--accent-glow)' : 'var(--text-dim)',
                  background: s.session_id === currentSessionId ? 'var(--accent-bg-light)' : 'transparent',
                }}
              >
                <span className="truncate">{s.title}</span>
                <button
                  className="opacity-0 group-hover/session:opacity-100 text-xs shrink-0 ml-1 hover:text-red-400"
                  onClick={(e) => { e.stopPropagation(); deleteSession(s.session_id) }}
                >
                  &times;
                </button>
              </div>
            ))}
            <button
              onClick={createSession}
              className="w-full mt-1 px-3 py-1.5 rounded-lg text-white text-xs font-medium transition-colors"
              style={{ background: 'var(--accent)' }}
            >
              ＋ 新会话
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/components/layout/Sidebar.tsx
git commit -m "feat: redesign sidebar as course-centric navigation with sub-nav and session history"
```

---

### Task 4: 首页 HomePage

**Files:**
- Create: `Coder/web/src/pages/HomePage.tsx`

- [ ] **Step 1: 创建 HomePage 组件**

```tsx
// Coder/web/src/pages/HomePage.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Plus, BookOpen, FileText, AlertTriangle } from 'lucide-react'

interface CourseItem {
  slug: string
  name: string
  semester: string
  kp_total: number
  kp_mastered: number
}

interface HomeStats {
  course_count: number
  note_count: number
  wrong_count: number
  courses: CourseItem[]
}

export function HomePage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<HomeStats | null>(null)

  useEffect(() => {
    api.get<HomeStats>('/courses/stats').catch(() => null).then((d) => setStats(d))
  }, [])

  const statCards = [
    { label: '学习课程', value: stats?.course_count ?? '--', color: '#0d9488', icon: BookOpen },
    { label: '知识笔记', value: stats?.note_count ?? '--', color: '#6366f1', icon: FileText },
    { label: '待复习错题', value: stats?.wrong_count ?? '--', color: '#d97706', icon: AlertTriangle },
  ]

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
      <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text)' }}>我的课程</h2>
      <p className="text-xs mb-6" style={{ color: 'var(--text-dim)' }}>开始学习，追踪你的知识掌握度</p>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {statCards.map(({ label, value, color, icon: Icon }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{
              background: `linear-gradient(135deg, ${color}11, ${color}08)`,
              border: `1px solid ${color}26`,
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon className="h-3.5 w-3.5" style={{ color }} />
              <span className="text-[11px]" style={{ color: 'var(--text-dim)' }}>{label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* 课程列表 */}
      <div className="flex flex-col gap-2">
        {stats?.courses.map((c) => {
          const pct = c.kp_total > 0 ? Math.round((c.kp_mastered / c.kp_total) * 100) : 0
          return (
            <div
              key={c.slug}
              onClick={() => navigate(`/course/${c.slug}`)}
              className="rounded-xl p-4 cursor-pointer flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <div>
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{c.name}</h3>
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>
                  {c.semester || '未设置学期'} · {c.kp_mastered}/{c.kp_total} 知识点已掌握
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-20 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--card)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${pct}%`,
                      background: pct > 50 ? 'var(--accent)' : pct > 0 ? 'var(--amber)' : 'var(--text-dim)',
                    }}
                  />
                </div>
                <span className="text-sm font-semibold" style={{ color: pct > 0 ? 'var(--accent-glow)' : 'var(--text-dim)' }}>
                  {pct}%
                </span>
              </div>
            </div>
          )
        })}

        {(!stats?.courses || stats.courses.length === 0) && (
          <div className="text-center py-12" style={{ color: 'var(--text-dim)' }}>
            <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">还没有课程</p>
            <p className="text-xs mt-1">点击按钮创建你的第一门课程</p>
          </div>
        )}
      </div>

      {/* 新建课程 */}
      <div className="text-center mt-6">
        <button
          className="px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:opacity-90"
          style={{ background: 'var(--accent)' }}
        >
          ＋ 新建课程
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 后端添加 /api/courses/stats 端点（可选，前端可降级）**

如果后端还没有 `/api/courses/stats`，先用 `/api/courses/` 获取课程列表自行计算统计。

```tsx
// 如果后端没有 stats 端点，改用以下 useEffect:
useEffect(() => {
  api.get<{ courses: CourseItem[] }>('/courses/').then((d) => {
    setStats({
      course_count: d.courses.length,
      note_count: 0,
      wrong_count: 0,
      courses: d.courses,
    })
  }).catch(() => {})
}, [])
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/pages/HomePage.tsx
git commit -m "feat: add homepage with stats cards and course list"
```

---

### Task 5: CoursePage 重构 — 顶部栏 + 标签布局

**Files:**
- Modify: `Coder/web/src/pages/CoursePage.tsx`
- Create: `Coder/web/src/components/course/NotesView.tsx`
- Create: `Coder/web/src/components/course/WrongAnswersView.tsx`

- [ ] **Step 1: 创建 NotesView 组件**

```tsx
// Coder/web/src/components/course/NotesView.tsx
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Search, Plus } from 'lucide-react';

interface Note {
  id: string;
  title: string;
  content: string;
  source: string;
  created_at: string;
}

interface Props {
  slug: string;
}

export function NotesView({ slug }: Props) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  useEffect(() => {
    api.get<{ notes: Note[] }>(`/courses/${slug}/notes`)
      .then((d) => setNotes(d.notes))
      .catch(() => {});
  }, [slug]);

  const handleCreate = async () => {
    if (!title.trim() || !content.trim()) return;
    await api.post(`/courses/${slug}/notes`, { course_id: slug, title: title.trim(), content: content.trim() });
    setTitle('');
    setContent('');
    setShowCreate(false);
    const d = await api.get<{ notes: Note[] }>(`/courses/${slug}/notes`);
    setNotes(d.notes);
  };

  const filtered = search
    ? notes.filter((n) => n.title.toLowerCase().includes(search.toLowerCase()))
    : notes;

  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 flex-1 px-2.5 py-1.5 rounded-lg text-xs"
          style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>
          <Search className="h-3 w-3" />
          <input
            className="bg-transparent border-none outline-none flex-1 text-xs"
            placeholder="搜索笔记..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ color: 'var(--text)' }}
          />
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90"
          style={{ background: 'var(--accent)' }}
        >
          <Plus className="h-3.5 w-3.5 inline mr-1" />
          新建
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl p-3 flex flex-col gap-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <input
            className="px-2.5 py-1.5 rounded-lg text-xs border outline-none"
            style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
            placeholder="笔记标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="px-2.5 py-1.5 rounded-lg text-xs border outline-none resize-none"
            rows={3}
            style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
            placeholder="笔记内容..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1 rounded-md text-xs" style={{ color: 'var(--text-dim)' }}>取消</button>
            <button onClick={handleCreate} className="px-3 py-1 rounded-md text-xs text-white" style={{ background: 'var(--accent)' }}>保存</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 && (
          <p className="text-center text-xs py-8" style={{ color: 'var(--text-dim)' }}>
            {notes.length === 0 ? '暂无笔记，在问答中可一键生成' : '无匹配结果'}
          </p>
        )}
        <div className="grid grid-cols-2 gap-2.5">
          {filtered.map((n) => (
            <div
              key={n.id}
              className="rounded-xl p-3.5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <h4 className="text-[13px] font-semibold" style={{ color: 'var(--text)' }}>{n.title}</h4>
              <p className="text-[11px] mt-1.5 line-clamp-3" style={{ color: 'var(--text-dim)' }}>{n.content}</p>
              <div className="flex justify-between items-center mt-2.5">
                <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                  {n.created_at?.slice(0, 10)} · {n.source || '手动创建'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 WrongAnswersView 组件**

```tsx
// Coder/web/src/components/course/WrongAnswersView.tsx
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Plus } from 'lucide-react';

interface WrongAnswer {
  id: string;
  question: string;
  user_answer: string;
  correct_answer: string;
  knowledge_point?: string;
  created_at: string;
}

interface Props {
  slug: string;
}

export function WrongAnswersView({ slug }: Props) {
  const [items, setItems] = useState<WrongAnswer[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [question, setQuestion] = useState('');
  const [userAnswer, setUserAnswer] = useState('');
  const [correctAnswer, setCorrectAnswer] = useState('');

  useEffect(() => {
    api.get<{ wrong_answers: WrongAnswer[] }>(`/courses/${slug}/wrong-answers`)
      .then((d) => setItems(d.wrong_answers))
      .catch(() => {});
  }, [slug]);

  const handleAdd = async () => {
    if (!question.trim() || !userAnswer.trim() || !correctAnswer.trim()) return;
    await api.post(`/courses/${slug}/wrong-answers`, {
      course_id: slug,
      question: question.trim(),
      user_answer: userAnswer.trim(),
      correct_answer: correctAnswer.trim(),
    });
    setQuestion('');
    setUserAnswer('');
    setCorrectAnswer('');
    setShowAdd(false);
    const d = await api.get<{ wrong_answers: WrongAnswer[] }>(`/courses/${slug}/wrong-answers`);
    setItems(d.wrong_answers);
  };

  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex justify-end">
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90"
          style={{ background: 'var(--accent)' }}
        >
          <Plus className="h-3.5 w-3.5 inline mr-1" />
          添加错题
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl p-3 flex flex-col gap-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <input className="px-2.5 py-1.5 rounded-lg text-xs border outline-none" style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }} placeholder="题目" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <input className="px-2.5 py-1.5 rounded-lg text-xs border outline-none" style={{ background: 'var(--card)', borderColor: 'rgba(239,68,68,.3)', color: 'var(--text)' }} placeholder="你的错误答案" value={userAnswer} onChange={(e) => setUserAnswer(e.target.value)} />
          <input className="px-2.5 py-1.5 rounded-lg text-xs border outline-none" style={{ background: 'var(--card)', borderColor: 'rgba(34,197,94,.3)', color: 'var(--text)' }} placeholder="正确答案" value={correctAnswer} onChange={(e) => setCorrectAnswer(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowAdd(false)} className="px-3 py-1 rounded-md text-xs" style={{ color: 'var(--text-dim)' }}>取消</button>
            <button onClick={handleAdd} className="px-3 py-1 rounded-md text-xs text-white" style={{ background: 'var(--accent)' }}>保存</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col gap-2">
        {items.length === 0 && (
          <p className="text-center text-xs py-8" style={{ color: 'var(--text-dim)' }}>暂无错题</p>
        )}
        {items.map((w) => (
          <div key={w.id} className="rounded-lg p-3" style={{ background: 'var(--surface)', border: '1px solid rgba(239,68,68,.2)', borderLeft: '3px solid var(--red)' }}>
            <div className="flex justify-between items-start mb-1.5">
              {w.knowledge_point && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: 'rgba(239,68,68,.1)', color: 'var(--red)' }}>{w.knowledge_point}</span>
              )}
              <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>{w.created_at?.slice(0, 10)}</span>
            </div>
            <p className="text-xs font-semibold" style={{ color: 'var(--text)' }}>Q: {w.question}</p>
            <p className="text-[11px] mt-1" style={{ color: 'var(--red)' }}>✗ 你的答案: {w.user_answer}</p>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--green)' }}>✓ 正确答案: {w.correct_answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 更新 CoursePage 使用 NotesView 和 WrongAnswersView**

```tsx
// Coder/web/src/pages/CoursePage.tsx
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ChatPage } from './ChatPage';
import { KnowledgeGraph } from '@/components/KnowledgeGraph';
import { NotesView } from '@/components/course/NotesView';
import { WrongAnswersView } from '@/components/course/WrongAnswersView';
import { api } from '@/api/client';

interface ProgressData {
  total_points: number;
  tracked_points: number;
  mastered_points: number;
  overall_mastery: number;
}

export function CoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const [courseName, setCourseName] = useState('');
  const [progress, setProgress] = useState<ProgressData | null>(null);

  // 从 URL 推断当前 Tab
  const tabFromPath = (): 'qa' | 'notes' | 'graph' | 'wrong' => {
    if (location.pathname.endsWith('/notes')) return 'notes';
    if (location.pathname.endsWith('/graph')) return 'graph';
    if (location.pathname.endsWith('/wrong')) return 'wrong';
    return 'qa';
  };

  const activeTab = tabFromPath();

  useEffect(() => {
    if (!slug) return;
    api.get<{ course: { name: string } }>(`/courses/${slug}`).then((d) => setCourseName(d.course.name)).catch(() => {});
    api.get<ProgressData>(`/courses/${slug}/progress`).then(setProgress).catch(() => {});
  }, [slug]);

  if (!slug) {
    return <div className="p-8" style={{ color: 'var(--text-dim)' }}>请选择一个课程</div>;
  }

  const tabs = [
    { key: 'qa' as const, label: '问答' },
    { key: 'notes' as const, label: '笔记' },
    { key: 'graph' as const, label: '图谱' },
    { key: 'wrong' as const, label: '错题' },
  ];

  const switchTab = (key: string) => {
    const base = `/course/${slug}`;
    if (key === 'qa') navigate(base);
    else navigate(`${base}/${key}`);
  };

  return (
    <div className="flex flex-col h-full">
      {/* 顶部栏 */}
      <header
        className="flex items-center justify-between px-5 py-3 shrink-0 border-b"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)', transition: 'background 0.4s, border-color 0.4s' }}
      >
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>{courseName || slug}</h1>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>
              共 {progress?.total_points ?? '--'} 个知识点
            </p>
          </div>
          {/* Tab 切换 */}
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--card)' }}>
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => switchTab(key)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
                style={{
                  background: activeTab === key ? 'var(--tab-active-bg)' : 'transparent',
                  color: activeTab === key ? 'var(--text)' : 'var(--text-dim)',
                  boxShadow: activeTab === key ? 'var(--tab-active-shadow)' : 'none',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {/* 进度条 */}
        <div className="flex items-center gap-2.5">
          <span className="text-xs" style={{ color: 'var(--text-dim)' }}>掌握度</span>
          <div className="w-28 h-1.5 rounded-full overflow-hidden relative progress-shimmer"
            style={{ background: 'var(--card)' }}>
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${progress?.overall_mastery ?? 0}%`,
                background: 'linear-gradient(90deg, var(--accent), var(--accent-glow))',
              }}
            />
          </div>
          <span className="text-sm font-bold" style={{
            background: 'var(--pct-gradient)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {progress ? `${Math.round(progress.overall_mastery)}%` : '--'}
          </span>
        </div>
      </header>

      {/* 内容区 */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'qa' && <ChatPage courseId={slug} />}
        {activeTab === 'graph' && <KnowledgeGraph identifier={slug} />}
        {activeTab === 'notes' && <NotesView slug={slug} />}
        {activeTab === 'wrong' && <WrongAnswersView slug={slug} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add Coder/web/src/pages/CoursePage.tsx Coder/web/src/components/course/NotesView.tsx Coder/web/src/components/course/WrongAnswersView.tsx
git commit -m "feat: redesign CoursePage header with tabs and progress bar, extract Notes/Wrong views"
```

---

### Task 6: 聊天组件样式升级

**Files:**
- Modify: `Coder/web/src/components/chat/MessageList.tsx`
- Modify: `Coder/web/src/components/ChatMessage.tsx`
- Modify: `Coder/web/src/pages/ChatPage.tsx`

- [ ] **Step 1: 更新 MessageList 气泡样式**

```tsx
// Coder/web/src/components/chat/MessageList.tsx
import { useEffect, useRef } from 'react'
import type { Message } from '@/types'
import { ChatMessage } from '@/components/ChatMessage'
import { EmptyState } from '@/components/shared/EmptyState'
import { MessageSquare, AlertTriangle } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  streaming: boolean
  insideCourse?: boolean
}

export function MessageList({ messages, streaming, insideCourse }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0 && !streaming) {
    return (
      <EmptyState
        icon={MessageSquare}
        title={insideCourse ? '基于课程教材提问，获得精准回答' : '输入你的问题开始对话'}
        description={insideCourse ? '回答将标注引用自哪本教材、哪个章节' : '当前为通用对话模式，回答不基于课程教材'}
      />
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 space-y-6">
      {/* 非课程提示 */}
      {!insideCourse && messages.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px]" style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>
          <AlertTriangle className="h-3.5 w-3.5" />
          当前对话未关联课程，AI 回答基于通用知识。选择一个课程可获得基于教材的精准回答。
        </div>
      )}

      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex gap-2.5 max-w-[85%] animate-fade-in-up ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          style={{ animationDelay: `${i * 50}ms` }}
        >
          {/* Avatar */}
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-xs shrink-0"
            style={{
              background: msg.role === 'user'
                ? 'var(--card)'
                : 'linear-gradient(135deg, var(--accent), var(--gradient-to))',
            }}
          >
            {msg.role === 'user' ? '👤' : '✨'}
          </div>
          {/* Bubble */}
          <div
            className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed"
            style={{
              background: msg.role === 'user'
                ? 'var(--user-bubble-bg)'
                : 'var(--card)',
              border: msg.role === 'user'
                ? '1px solid var(--user-bubble-border)'
                : '1px solid var(--border)',
              borderTopRightRadius: msg.role === 'user' ? '4px' : undefined,
              borderTopLeftRadius: msg.role === 'assistant' ? '4px' : undefined,
              color: 'var(--text)',
            }}
          >
            {msg.role === 'user' ? (
              <p>{msg.content}</p>
            ) : (
              <ChatMessage parts={msg.parts} />
            )}
          </div>
        </div>
      ))}

      {streaming && (
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--accent-glow)' }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--accent-glow)' }} />
          CourseMate 正在回答...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 2: 更新 ChatMessage 添加引用样式**

```tsx
// Coder/web/src/components/ChatMessage.tsx
import type { ChatPart } from '../types'
import { ToolCallAccordion } from './chat/ToolCallAccordion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText } from 'lucide-react'

export function ChatMessage({ parts }: { parts?: ChatPart[] }) {
  if (!parts || parts.length === 0) {
    return <span className="text-sm italic" style={{ color: 'var(--text-dim)' }}>空回复</span>
  }

  return (
    <div className="space-y-2">
      {parts.map((p, i) => {
        if (p.type === 'content' && p.content) {
          return (
            <div key={i} className="prose prose-sm max-w-none" style={{ color: 'var(--text)' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {p.content}
              </ReactMarkdown>
            </div>
          )
        }
        if (p.type === 'tool_call') {
          return <ToolCallAccordion key={i} name={p.name || ''} args={p.args || ''} />
        }
        if (p.type === 'tool_result' && p.content) {
          // 引用来源标注
          const isCitation = p.name && ['retrieve', 'search_course_knowledge', 'rag_search'].some(n => p.name?.includes(n))
          if (isCitation) {
            try {
              const data = JSON.parse(p.content)
              if (Array.isArray(data) && data.length > 0) {
                return (
                  <div key={i} className="flex flex-col gap-1">
                    {data.slice(0, 3).map((ref: any, j: number) => (
                      <div
                        key={j}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px]"
                        style={{ background: 'var(--accent-bg-light)', color: 'var(--accent-glow)' }}
                      >
                        <FileText className="h-3 w-3" />
                        <span>{ref.metadata?.filename || ref.source || '教材'}</span>
                        {ref.metadata?.section && (
                          <span style={{ color: 'var(--text-dim)' }}>· {ref.metadata.section}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )
              }
            } catch {}
          }
          return null // 隐藏非引用的 tool_result
        }
        if (p.type === 'error') {
          return (
            <div key={i} className="text-sm p-2 rounded-lg" style={{ color: 'var(--red)', background: 'rgba(239,68,68,.08)' }}>
              {p.content}
            </div>
          )
        }
        return null
      })}
    </div>
  )
}
```

- [ ] **Step 3: 更新 ChatPage**

```tsx
// Coder/web/src/pages/ChatPage.tsx
// 新增 `insideCourse` prop 传给 MessageList

// 在 handleSend 的参数中:
// <MessageList messages={messages} streaming={streaming} insideCourse={!!courseId} />
```

- [ ] **Step 4: Commit**

```bash
git add Coder/web/src/components/chat/MessageList.tsx Coder/web/src/components/ChatMessage.tsx Coder/web/src/pages/ChatPage.tsx
git commit -m "feat: update chat bubble styling with animations, citation display, and course context indicator"
```

---

### Task 7: 知识图谱样式升级

**Files:**
- Modify: `Coder/web/src/components/KnowledgeGraph.tsx`

- [ ] **Step 1: 更新知识图谱节点颜色和交互**

在现有 KnowledgeGraph 组件中，将 `colors` 数组替换为按掌握度映射颜色，添加图例，支持响应式 SVG：

关键修改点（在 return 中的 SVG 之前添加掌握度映射）：

```tsx
// 替换现有颜色映射逻辑
// 后端需返回节点的 mastery 字段: { mastery: 'mastered' | 'learning' | 'new' }
const masteryColors: Record<string, string> = {
  mastered: '#22c55e',
  learning: '#6366f1',
  new: '#94a3b8',
}
const masteryGlow: Record<string, string> = {
  mastered: 'rgba(34,197,94,.2)',
  learning: 'rgba(99,102,241,.2)',
  new: 'rgba(148,163,184,.1)',
}

// 节点渲染替换为:
const mastery = (n as any).mastery || 'new'
const color = masteryColors[mastery] || '#94a3b8'
const r = mastery === 'mastered' ? 8 : mastery === 'learning' ? 7 : 5.5

<circle
  cx={n.x} cy={n.y} r={isHover ? r + 2 : r}
  fill={color}
  opacity={isHover ? 1 : 0.85}
  style={{ filter: `drop-shadow(0 0 ${isHover ? 6 : 2}px ${color}44)` }}
  className="transition-all duration-200"
/>

// 图例更新为:
<div className="flex flex-wrap gap-3 justify-center mt-3">
  <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
    <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#22c55e' }} /> 已掌握
  </span>
  <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
    <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#6366f1' }} /> 学习中
  </span>
  <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
    <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#94a3b8' }} /> 未开始
  </span>
  <span className="text-[10px] ml-auto" style={{ color: 'var(--text-dim)' }}>💡 点击节点跳转问答</span>
</div>
```

完整修改见文件，此处列出关键 diff。

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/components/KnowledgeGraph.tsx
git commit -m "feat: update knowledge graph with mastery-based node colors and legend"
```

---

### Task 8: 知识库管理页样式升级

**Files:**
- Modify: `Coder/web/src/pages/KnowledgePage.tsx`

- [ ] **Step 1: 更新 KnowledgePage 为新设计**

```tsx
// Coder/web/src/pages/KnowledgePage.tsx
import { useState, useCallback } from 'react'
import { api } from '../api/client'
import { Upload, FileText, FileSpreadsheet, FileImage, File } from 'lucide-react'

interface DocFile {
  id: string
  filename: string
  size: number
  chunks: number
  course_slug?: string
  course_name?: string
  status: 'indexed' | 'indexing'
}

export function KnowledgePage() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<{ filename: string; chunks: number; status: string }[]>([])
  const [docFiles, setDocFiles] = useState<DocFile[]>([])

  // 加载已有文件列表
  useState(() => {
    api.get<{ documents: DocFile[] }>('/knowledge/documents')
      .then((d) => setDocFiles(d.documents))
      .catch(() => {})
  })

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      const data = await api.uploadFiles<{ results: { filename: string; chunks: number; status: string }[] }>(
        '/knowledge/upload',
        files,
      )
      setUploadResults(data.results)
      setFiles([])
    } catch (e) {
      setUploadResults([{ filename: 'Error', chunks: 0, status: String(e) }])
    } finally {
      setUploading(false)
    }
  }, [files])

  const fileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    if (ext === 'pdf') return <FileText className="h-4 w-4" style={{ color: '#ef4444' }} />
    if (ext === 'pptx') return <FileImage className="h-4 w-4" style={{ color: '#f59e0b' }} />
    if (ext === 'xlsx' || ext === 'csv') return <FileSpreadsheet className="h-4 w-4" style={{ color: '#22c55e' }} />
    return <File className="h-4 w-4" style={{ color: 'var(--accent-glow)' }} />
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
      <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text)' }}>知识库管理</h2>
      <p className="text-xs mb-6" style={{ color: 'var(--text-dim)' }}>上传教材和课件，构建课程知识库</p>

      {/* 上传区域 */}
      <div className="mb-6">
        <label
          className="flex flex-col items-center gap-2.5 py-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors"
          style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
        >
          <Upload className="h-8 w-8" style={{ color: 'var(--text-dim)' }} />
          <span className="text-sm" style={{ color: 'var(--text)' }}>拖拽文件上传，或点击选择</span>
          <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
            支持 PDF / PPTX / DOCX / EPUB / XLSX / CSV / TXT / MD
          </span>
          <input
            type="file"
            multiple
            accept=".txt,.md,.pdf,.docx,.pptx,.xlsx,.csv,.epub"
            className="hidden"
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
        </label>
        {files.length > 0 && (
          <div className="flex items-center justify-between mt-3 px-3 py-2 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
              已选择 {files.length} 个文件: {files.map((f) => f.name).join(', ')}
            </span>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90"
              style={{ background: 'var(--accent)' }}
            >
              {uploading ? '导入中...' : '导入'}
            </button>
          </div>
        )}
        {uploadResults.length > 0 && uploadResults.map((r, i) => (
          <div key={i} className="mt-2 px-3 py-2 rounded-lg text-xs" style={{
            background: r.status === 'imported' ? 'rgba(34,197,94,.08)' : 'rgba(239,68,68,.08)',
            color: r.status === 'imported' ? 'var(--green)' : 'var(--red)',
          }}>
            {r.filename}: {r.status === 'imported' ? `${r.chunks} 个文档块已导入` : r.status}
          </div>
        ))}
      </div>

      {/* 文件列表 */}
      <div className="flex flex-col gap-1.5">
        {docFiles.map((f) => (
          <div key={f.id} className="flex items-center justify-between px-3.5 py-2.5 rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2.5">
              {fileIcon(f.filename)}
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--text)' }}>{f.filename}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                  {formatSize(f.size)} · {f.chunks} 个文档块
                  {f.course_name ? ` · 关联: ${f.course_name}` : ''}
                </p>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-md font-medium" style={{
              background: f.status === 'indexed' ? 'rgba(34,197,94,.1)' : 'rgba(245,158,11,.1)',
              color: f.status === 'indexed' ? 'var(--green)' : 'var(--amber)',
            }}>
              {f.status === 'indexed' ? '已索引' : '解析中'}
            </span>
          </div>
        ))}
        {docFiles.length === 0 && (
          <div className="text-center py-12" style={{ color: 'var(--text-dim)' }}>
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">暂无文档</p>
            <p className="text-xs mt-1">上传你的第一份课件开始构建知识库</p>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/pages/KnowledgePage.tsx
git commit -m "feat: redesign knowledge page with file list and upload zone"
```

---

### Task 9: 设置页面

**Files:**
- Create: `Coder/web/src/pages/SettingsPage.tsx`

- [ ] **Step 1: 创建设置页面**

```tsx
// Coder/web/src/pages/SettingsPage.tsx
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
      {/* 左侧导航 */}
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
              background: active === key ? 'var(--accent-bg-light)' : 'transparent',
              color: active === key ? 'var(--accent-glow)' : 'var(--text-dim)',
              fontWeight: active === key ? 600 : 400,
            }}
          >
            {label}
          </div>
        ))}
      </div>

      {/* 右侧内容 */}
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
            <p className="text-sm" style={{ color: 'var(--text-dim)' }}>技能管理功能即将在此页面集成，敬请期待。</p>
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
              CourseMate — 围绕课程教材的 AI 学习伴侣。基于 LangChain + LangGraph 构建，聚焦高等教育场景，
              以课程知识库 + RAG 精准问答 + 学习路径追踪为核心。
            </p>
            <p className="text-xs mt-4" style={{ color: 'var(--text-dim)' }}>Version 0.1.0</p>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/pages/SettingsPage.tsx
git commit -m "feat: add settings page with category navigation"
```

---

### Task 10: 最终验证和收尾

- [ ] **Step 1: 运行 TypeScript 类型检查**

```bash
cd Coder/web && npx tsc --noEmit
```

修复所有类型错误。

- [ ] **Step 2: 启动前端验证所有页面**

```bash
cd Coder/web && npm run dev
```

依次访问以下路由验证：
- `http://localhost:5173/` — 首页（统计卡片 + 课程列表）
- `http://localhost:5173/chat` — 通用对话（非课程提示）
- `http://localhost:5173/course/<existing-slug>` — 课程问答
- `http://localhost:5173/course/<slug>/notes` — 笔记
- `http://localhost:5173/course/<slug>/graph` — 知识图谱
- `http://localhost:5173/course/<slug>/wrong` — 错题本
- `http://localhost:5173/knowledge` — 知识库管理
- `http://localhost:5173/settings` — 设置页

验证主题切换按钮在亮/暗之间正常工作。

- [ ] **Step 3: 运行前端构建验证**

```bash
cd Coder/web && npm run build
```

确保无构建错误。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final verification and type fixes for frontend redesign"
```

---

## 总结

**10 个任务，预计 3-4 小时完成。**

每个任务结束后 commit 一次，便于回溯。关键改动：
1. 主题系统（CSS 变量 + animations）
2. 三栏布局（IconNav + Sidebar + Main）
3. 首页 + 设置页
4. CoursePage 重构（新头部 + NotesView/WrongAnswersView 组件抽取）
5. 聊天组件样式升级（气泡 + 引用 + 动画）
6. 知识图谱 + 知识库页样式更新
7. 删除 4 个旧页面，清理路由
