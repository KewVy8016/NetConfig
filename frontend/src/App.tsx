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
    return saved === 'true'
  })

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(collapsed))
  }, [collapsed])

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-bg">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        
        {/* Main Content Area */}
        <div 
          className={`flex-1 flex flex-col transition-all duration-200 ${
            collapsed ? 'ml-16' : 'ml-60'
          }`}
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
