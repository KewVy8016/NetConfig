import { Menu } from 'lucide-react'
import type { ReactNode } from 'react'

interface TopbarProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
  title: string
  breadcrumbs?: ReactNode
}

export function Topbar({ collapsed, setCollapsed, title, breadcrumbs }: TopbarProps) {
  return (
    <header className="h-14 sticky top-0 z-10 topbar-blur bg-white/70 border-b border-gray-200 px-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          title="Toggle Sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        
        <div className="flex items-center gap-2">
          <h1 className="font-semibold text-gray-900">{title}</h1>
          {breadcrumbs && (
            <>
              <span className="text-gray-300">/</span>
              {breadcrumbs}
            </>
          )}
        </div>
      </div>
    </header>
  )
}
