import { useState, useEffect } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/shared/Sidebar'
import { NodesPage } from './pages/NodesPage'
import { AddNodePage } from './pages/AddNodePage'
import { NodeDetailPage } from './pages/NodeDetailPage'
import { HistoryPage } from './pages/HistoryPage'

function App() {
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar_collapsed')
    return window.matchMedia('(max-width: 1024px)').matches || saved === 'true'
  })

  useEffect(() => {
    if (!window.matchMedia('(max-width: 1024px)').matches) localStorage.setItem('sidebar_collapsed', String(collapsed))
  }, [collapsed])

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1024px)')
    const adapt = () => setCollapsed(media.matches || localStorage.getItem('sidebar_collapsed') === 'true')
    const closeOnEscape = (event: KeyboardEvent) => { if (media.matches && event.key === 'Escape') setCollapsed(true) }
    media.addEventListener('change', adapt)
    window.addEventListener('keydown', closeOnEscape)
    return () => { media.removeEventListener('change', adapt); window.removeEventListener('keydown', closeOnEscape) }
  }, [])

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-bg">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        
        {/* Main Content Area */}
        <div 
          className={`index-main ${collapsed ? 'is-collapsed' : ''}`}
        >
          <Routes>
            <Route path="/" element={<NodesPage collapsed={collapsed} setCollapsed={setCollapsed} />} />
            <Route path="/nodes/add" element={<AddNodePage collapsed={collapsed} setCollapsed={setCollapsed} />} />
            <Route path="/nodes/:id" element={<NodeDetailPage collapsed={collapsed} setCollapsed={setCollapsed} />} />
            <Route path="/history" element={<HistoryPage collapsed={collapsed} setCollapsed={setCollapsed} />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
