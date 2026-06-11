import { NavLink, useLocation } from 'react-router-dom';
import { BookOpen, MessageSquare, FolderOpen, Wrench } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

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
    const next = current === 'light' ? null : 'light';
    if (next) {
      el.setAttribute('data-theme', 'light');
    } else {
      el.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', next || 'dark');
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
              background: isActive ? 'var(--brand)' : 'transparent',
              boxShadow: isActive ? 'var(--icon-active-shadow)' : 'none',
            }}
          >
            <Icon className="h-[18px] w-[18px]" />
          </NavLink>
        );

        if (!isActive) {
          return (
            <Tooltip key={to}>
              <TooltipTrigger>{link}</TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          );
        }
        return link;
      })}

      {/* Theme toggle switch */}
      <Tooltip>
        <TooltipTrigger>
          <button
            onClick={toggleTheme}
            className="w-11 h-6 rounded-xl border-[1.5px] relative mt-auto mb-2 transition-colors duration-300"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
            title="切换主题"
          >
            <div className="theme-knob" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">切换主题</TooltipContent>
      </Tooltip>
    </nav>
  );
}
