import { BrowserRouter, Routes, Route } from 'react-router-dom'
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
          <Route path="/chat/:sessionId" element={<ChatPage />} />
          <Route path="/course/:slug" element={<CoursePage />} />
          <Route path="/course/:slug/:tab" element={<CoursePage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
        <DocxPreviewPanel />
      </main>
    </div>
  )
}
