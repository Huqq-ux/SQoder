import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import { SidebarProvider } from './components/layout/SidebarContext'
import { TopNav } from './components/layout/TopNav'
import { ChatPage } from './pages/ChatPage'

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
    <div className="flex flex-col h-screen overflow-hidden">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0">
          <div className="p-3 text-slate-400 text-sm">Sidebar placeholder</div>
        </aside>
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/knowledge" element={<div className="p-6 text-slate-400">Knowledge</div>} />
            <Route path="/skills" element={<div className="p-6 text-slate-400">Skills</div>} />
            <Route path="/multi-agent" element={<div className="p-6 text-slate-400">MultiAgent</div>} />
            <Route path="/mcp" element={<div className="p-6 text-slate-400">MCP</div>} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
