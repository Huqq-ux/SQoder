# Frontend Refactor Design

**Date**: 2026-06-04
**Goal**: 全面翻新 Coder/web 前端，现代科技感风格，深色模式优先，shadcn/ui 组件库

## Scope

- **Keep**: API 层、Zustand store 结构、后端 API
- **Replace**: 样式系统、路由系统、组件库、页面布局
- **Remove**: SOP 页面、SOP 相关导航项

## Tech Stack Changes

| Layer | Before | After |
|-------|--------|-------|
| Styling | Single App.css (630 lines) | Tailwind CSS + CSS variables |
| Components | Hand-written | shadcn/ui (Radix UI primitives) |
| Routing | State-based (navPage in store) | React Router v6 |
| Icons | Emoji hardcoded | lucide-react |

## Layout Architecture

```
┌────────────────────────────────────────────────┐
│  TopNav (fixed, glass-blur)                     │
│  [Toggle] Logo  PageTitle    [Search ⌘K] [⚙]  │
├──────────┬─────────────────────────────────────┤
│ Sidebar  │  Page Content                       │
│ (collaps-│  <Routes>                           │
│ ible)    │                                      │
│          │                                      │
└──────────┴─────────────────────────────────────┘
```

- **TopNav**: h-14, backdrop-blur, border-b, z-50
- **Sidebar**: expanded w-56, collapsed w-10 (icon-only with tooltips)
- **Collapse state**: persisted to localStorage
- **Main area**: flex-1, overflow-y-auto

## Routes

```
/              → Redirect /chat
/chat          → ChatPage (canvas layout)
/knowledge     → KnowledgePage
/skills        → SkillsPage
/multi-agent   → MultiAgentPage
/mcp           → MCPPage
```

Remove `/sop` route entirely.

## Component Tree

```
App (ThemeProvider + Router)
├── TopNav
│   ├── SidebarToggleButton
│   ├── PageTitle (from route)
│   ├── CommandPalette (⌘K)
│   └── ThemeToggle + SettingsDropdown
├── Sidebar (collapsible via context)
│   ├── NavItem × 5 (icon + label, active state via route match)
│   ├── SessionList (rendered only on /chat)
│   │   ├── SessionItem (title, delete)
│   │   └── NewSessionButton
│   └── SessionListSkeleton (loading state)
└── <Routes>
    ├── ChatPage
    │   ├── ChatPanel (flex-1)
    │   │   ├── MessageList (auto-scroll)
    │   │   │   ├── EmptyState
    │   │   │   ├── UserBubble
    │   │   │   └── AssistantBubble
    │   │   │       ├── MarkdownContent (react-markdown)
    │   │   │       └── ToolCallAccordion (collapsible)
    │   │   └── ChatInput (textarea + send/stop button)
    │   └── CanvasPanel (collapsible right panel)
    │       ├── CodeViewer (syntax highlight)
    │       ├── FilePreviewCard
    │       └── ToolCallDetailCard
    ├── KnowledgePage
    │   ├── UploadZone (drag & drop)
    │   ├── SearchInput + ResultsList
    │   └── UploadResultCard
    ├── SkillsPage
    │   ├── SkillCardGrid
    │   ├── SkillDetailSheet (slide-over replaces alert())
    │   └── SkillUploadForm
    ├── MultiAgentPage
    │   ├── TaskInput
    │   └── ExecutionResultCard (streaming ready)
    └── MCPPage
        ├── MarketplaceGrid (search + card grid)
        └── InstalledList (table/list + status dots)
```

## Visual Design

### Theme (dark-first)

- **Colors**: slate-900 background, slate-800 cards, blue-500 primary, violet-400 accent
- **Glass**: TopNav uses `bg-slate-900/80 backdrop-blur-md`
- **Borders**: `border-slate-800` (dark), `border-slate-200` (light)
- **Typography**: font-sans (Inter via system stack), text-sm base
- **Radius**: rounded-lg (8px) buttons/inputs, rounded-xl (12px) cards
- **Shadows**: shadow-sm cards, shadow-lg dropdowns
- **Animations**: transition-colors 150ms on interactive elements

### Sidebar

- Expanded: bg-slate-950, text-slate-300, active item bg-blue-500/10 text-blue-400
- Collapsed: same bg, tooltip on hover for icon items
- Session list: scrollable, max-h-[40vh], border-t

### Chat Bubbles

- User: bg-blue-500/20 text-blue-100, aligned right
- Assistant: transparent, full width
- Tool calls: bg-slate-800/50 rounded, accent-left border

### Canvas Panel

- Default: closed (w-0)
- Open: w-96, bg-slate-900, border-l, resize handle
- Trigger: auto-open when tool_call with code/file arrives
- Content: tabs for multiple files/tools

## State Management

Zustand store changes:

- **Remove**: `navPage` (replaced by routing)
- **Keep**: sessions, currentSessionId, messages, streaming
- **Add**: `canvasOpen: boolean`, `canvasContent: { type, data } | null`

## Files to Create/Modify

### New files

| File | Purpose |
|------|---------|
| `src/index.css` | Tailwind directives + CSS variables |
| `src/lib/utils.ts` | cn() helper for class merging |
| `src/components/ui/*.tsx` | shadcn/ui primitives |
| `src/components/layout/TopNav.tsx` | Top navigation bar |
| `src/components/layout/Sidebar.tsx` | Refactored collapsible sidebar |
| `src/components/layout/SidebarContext.tsx` | Collapse state context |
| `src/components/chat/ChatInput.tsx` | Extracted from ChatPage |
| `src/components/chat/MessageList.tsx` | Extracted from ChatPage |
| `src/components/chat/CanvasPanel.tsx` | Right panel for code/file |
| `src/components/shared/EmptyState.tsx` | Reusable empty state |

### Modified files

| File | Changes |
|------|---------|
| `App.tsx` | Router, layout, remove page conditionals |
| `App.css` | **DELETE** (replaced by Tailwind) |
| `main.tsx` | Import Tailwind |
| `Sidebar.tsx` | Collapsible, remove emoji, lucide icons |
| `ChatMessage.tsx` | Use shadcn accordion for tool calls |
| `ChatPage.tsx` | Canvas layout, extract sub-components |
| `KnowledgePage.tsx` | Card layout, drag-drop zone |
| `SkillsPage.tsx` | Grid cards, sheet instead of alert() |
| `MultiAgentPage.tsx` | Minimal polish |
| `MCPPage.tsx` | Fix broken CSS, use Tailwind |
| `chatStore.ts` | Remove navPage, add canvas state |
| `types.ts` | Remove NavPage type |

### Deleted files

- `App.css` — replaced by Tailwind

## Risk Mitigation

- **Incremental**: Install Tailwind first, then migrate page by page, verify each works
- **API unchanged**: Zero backend changes needed
- **Testing**: After each page migration, run `npm run dev` and manually smoke-test

## Out of Scope

- Mobile responsive (future phase)
- Backend changes
- New features beyond UI refactor
- i18n / accessibility audit
- Unit tests for UI components
