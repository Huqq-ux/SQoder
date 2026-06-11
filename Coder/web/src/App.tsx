import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import { SidebarProvider } from './components/layout/SidebarContext'
import { TooltipProvider } from '@/components/ui/tooltip'
import { TopNav } from './components/layout/TopNav'
import { Sidebar } from './components/layout/Sidebar'
import { ChatPage } from './pages/ChatPage'
import { CoursePage } from './pages/CoursePage'
import { KnowledgePage } from './pages/KnowledgePage'
import { SkillsPage } from './pages/SkillsPage'
import { DocxPreviewPanel } from './components/DocxPreviewPanel'

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
    <div className="flex flex-col h-screen overflow-hidden bg-white dark:bg-slate-950">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden relative">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/course/:courseId" element={<CoursePage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/skills" element={<SkillsPage />} />
          </Routes>
          <DocxPreviewPanel />
        </main>
      </div>
    </div>
  )
}
