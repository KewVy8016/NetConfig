import { Grid, History } from 'lucide-react'
import { NavLink } from 'react-router-dom'

interface SidebarProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

export function Sidebar({ collapsed }: SidebarProps) {
  return (
    <aside
      className={`bg-sidebar-bg text-sidebar-text flex flex-col transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-60'
      } fixed inset-y-0 left-0 z-20`}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-white/10">
        {!collapsed && (
          <span className="text-white font-semibold tracking-wide">NetConfig</span>
        )}
        {collapsed && (
          <span className="text-white font-bold mx-auto">NC</span>
        )}
      </div>

      {/* Nav Links */}
      <nav className="flex-1 py-4 flex flex-col gap-1 px-2">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              isActive
                ? 'bg-sidebar-active text-white'
                : 'hover:bg-sidebar-hover hover:text-white'
            }`
          }
          title="Nodes"
        >
          <Grid className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>Nodes</span>}
        </NavLink>

        <NavLink
          to="/history"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              isActive
                ? 'bg-sidebar-active text-white'
                : 'hover:bg-sidebar-hover hover:text-white'
            }`
          }
          title="Command History"
        >
          <History className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>Command History</span>}
        </NavLink>
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="p-4 text-xs text-sidebar-text/50 border-t border-white/10">
          v0.1.0 (Phase 1)
        </div>
      )}
    </aside>
  )
}
