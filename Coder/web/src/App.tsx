import { useChatStore } from './stores/chatStore'
import { Sidebar } from './components/Sidebar'
import { ChatPage } from './pages/ChatPage'
import { KnowledgePage } from './pages/KnowledgePage'
import { SOPPage } from './pages/SOPPage'
import { SkillsPage } from './pages/SkillsPage'
import { MultiAgentPage } from './pages/MultiAgentPage'

export default function App() {
  const navPage = useChatStore((s) => s.navPage)

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {navPage === 'chat' && <ChatPage />}
        {navPage === 'knowledge' && <KnowledgePage />}
        {navPage === 'sop' && <SOPPage />}
        {navPage === 'skills' && <SkillsPage />}
        {navPage === 'multi-agent' && <MultiAgentPage />}
      </main>
    </div>
  )
}
