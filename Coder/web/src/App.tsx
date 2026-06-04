import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import { SidebarProvider } from './components/layout/SidebarContext'
import { TooltipProvider } from '@/components/ui/tooltip'
import { TopNav } from './components/layout/TopNav'
import { Sidebar } from './components/layout/Sidebar'
import { ChatPage } from './pages/ChatPage'
import { KnowledgePage } from './pages/KnowledgePage'

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <TooltipProvider delay={0}>
        <BrowserRouter>
          <SidebarProvider>
            <AppLayout />
          </SidebarProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  )
}

function AppLayout() {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/skills" element={<div className="p-6 text-slate-400">Skills</div>} />
            <Route path="/multi-agent" element={<div className="p-6 text-slate-400">MultiAgent</div>} />
            <Route path="/mcp" element={<div className="p-6 text-slate-400">MCP</div>} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
