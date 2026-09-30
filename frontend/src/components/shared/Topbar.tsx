// แถบหัวหน้า: แยก breadcrumb ของรายการอุปกรณ์จากหัวข้อหน้าตั้งค่าเดิม
import { ChevronRight, Menu } from 'lucide-react'
import type { ReactNode } from 'react'

interface TopbarProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
  title: string
  breadcrumbs?: ReactNode
  variant?: 'default' | 'breadcrumb'
}

export function Topbar({ collapsed, setCollapsed, title, breadcrumbs, variant = 'default' }: TopbarProps) {
  const toggle = <button type="button" onClick={() => setCollapsed(!collapsed)} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" title="เปิดหรือปิดเมนู" aria-label={collapsed ? 'เปิดเมนู' : 'ย่อหรือปิดเมนู'} aria-expanded={!collapsed}><Menu className="w-5 h-5" aria-hidden="true" /></button>
  if (variant === 'breadcrumb') {
    return <header className="index-topbar">{toggle}<nav aria-label="ตำแหน่งปัจจุบัน"><span>NetConfig</span><ChevronRight size={15} aria-hidden="true" /><span aria-current="page">{title}</span></nav></header>
  }
  return (
    <header className="h-14 sticky top-0 z-10 bg-white border-b border-gray-200 px-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {toggle}
        <div className="flex items-center gap-2">
          <h1 className="font-semibold text-gray-900">{title}</h1>
          {breadcrumbs && <><span className="text-gray-300">/</span>{breadcrumbs}</>}
        </div>
      </div>
    </header>
  )
}
