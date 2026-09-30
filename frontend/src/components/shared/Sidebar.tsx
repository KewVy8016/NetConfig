// เมนูหลักตามแบบ Device Index พร้อมเมนูซ้อนสำหรับจอขนาดเล็ก
import { Grid, History, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'

interface SidebarProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

export function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const closeMobile = () => { if (window.matchMedia('(max-width: 1024px)').matches) setCollapsed(true) }
  return (
    <>
      {!collapsed && <button type="button" className="index-sidebar-backdrop" onClick={() => setCollapsed(true)} aria-label="ปิดเมนู" />}
      <aside className={`index-sidebar ${collapsed ? 'is-collapsed' : ''}`}>
        <NavLink to="/" className="index-brand" aria-label="NetConfig — รายการอุปกรณ์" onClick={closeMobile}>
          {collapsed ? 'NC' : <>Net<span>Config</span></>}
        </NavLink>
        <button type="button" className="index-sidebar-close" onClick={() => setCollapsed(true)} aria-label="ปิดเมนู"><X size={22} /></button>
        <nav aria-label="เมนูหลัก">
          <NavLink to="/" end aria-label="Nodes" title="Nodes" onClick={closeMobile} className={({ isActive }) => `index-nav-link ${isActive ? 'is-active' : ''}`}><Grid size={22} aria-hidden="true" /><span>Nodes</span></NavLink>
          <NavLink to="/history" aria-label="Command History" title="Command History" onClick={closeMobile} className={({ isActive }) => `index-nav-link ${isActive ? 'is-active' : ''}`}><History size={22} aria-hidden="true" /><span>History</span></NavLink>
        </nav>
      </aside>
    </>
  )
}
