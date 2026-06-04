import { useSidebar } from './SidebarContext'
import { useTheme } from 'next-themes'
import { PanelLeft, Sun, Moon } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function TopNav() {
  const { collapsed, toggle } = useSidebar()
  const { theme, setTheme } = useTheme()

  return (
    <header className="h-14 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center px-4 shrink-0 z-50">
      <Button variant="ghost" size="icon" onClick={toggle} className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 mr-2" title={collapsed ? '展开侧边栏' : '折叠侧边栏'}>
        <PanelLeft className="h-4 w-4" />
      </Button>

      <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">Qbot</span>

      <div className="flex-1 max-w-md mx-auto">
        <div className="flex items-center bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-400 dark:text-slate-500">
          <span>搜索...</span>
          <kbd className="ml-auto text-[10px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 dark:text-slate-600">⌘K</kbd>
        </div>
      </div>

      <div className="flex items-center gap-2 ml-4">
        <Button variant="ghost" size="icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" title="切换主题">
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
