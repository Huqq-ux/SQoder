import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

const COLLAPSED_WIDTH = 52
const DEFAULT_WIDTH = 224
const MIN_WIDTH = 52
const MAX_WIDTH = 400

interface SidebarContextType {
  width: number
  collapsed: boolean
  toggle: () => void
  setWidth: (w: number) => void
}

const SidebarContext = createContext<SidebarContextType>({
  width: DEFAULT_WIDTH,
  collapsed: false,
  toggle: () => {},
  setWidth: () => {},
})

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [width, _setWidth] = useState(() => {
    const stored = localStorage.getItem('sidebar-width')
    return stored ? Number(stored) : DEFAULT_WIDTH
  })

  useEffect(() => {
    localStorage.setItem('sidebar-width', String(width))
  }, [width])

  const collapsed = width <= COLLAPSED_WIDTH

  const toggle = () => {
    if (collapsed) {
      _setWidth(DEFAULT_WIDTH)
    } else {
      _setWidth(COLLAPSED_WIDTH)
    }
  }

  const setWidth = (w: number) => {
    _setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(w))))
  }

  return (
    <SidebarContext.Provider value={{ width, collapsed, toggle, setWidth }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  return useContext(SidebarContext)
}
