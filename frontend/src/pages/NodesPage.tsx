import { useQueries, useQuery } from '@tanstack/react-query'
import { Plus, Search, Server, ShieldAlert, Terminal } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Topbar } from '../components/shared/Topbar'
import { StatusBadge } from '../components/shared/StatusBadge'
import { listNodes, type NodeStatus, testNodeConnection } from '../lib/api'

interface NodesPageProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

export function NodesPage({ collapsed, setCollapsed }: NodesPageProps) {
  const [search, setSearch] = useState('')
  const [view, setView] = useState<'card' | 'table'>('card')
  const navigate = useNavigate()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['nodes', search],
    queryFn: () => listNodes(search),
  })

  const healthQueries = useQueries({
    queries: (data?.nodes ?? []).map((node) => ({
      queryKey: ['node-health', node.id],
      queryFn: () => testNodeConnection(node.id),
      retry: false,
      refetchInterval: 30_000,
      refetchIntervalInBackground: false,
    })),
  })
  const healthById = new Map((data?.nodes ?? []).map((node, index) => [node.id, healthQueries[index]]))
  const liveStatus = (fallback: NodeStatus, nodeId: string): NodeStatus => {
    const health = healthById.get(nodeId)
    if (!health) return fallback
    // polling อาจชนกับ Reconnect/config lock; ใช้สถานะล่าสุดแทน Unknown ชั่วคราว
    if (health.isError) return fallback
    if (health.isFetching && !health.data) return 'checking'
    if (health.data?.overall_status === 'success') return 'connected'
    if (health.data?.overall_status === 'failed') return 'unreachable'
    return fallback
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar collapsed={collapsed} setCollapsed={setCollapsed} title="Nodes Dashboard" />

      <main className="p-6">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center mb-6">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by hostname or IP..."
              className="input-field pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="bg-gray-100 p-1 rounded-lg flex items-center">
              <button
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${view === 'card' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setView('card')}
              >
                Cards
              </button>
              <button
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${view === 'table' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setView('table')}
              >
                Table
              </button>
            </div>
            
            <Link to="/nodes/add" className="btn-primary flex items-center gap-2 flex-1 justify-center sm:flex-none">
              <Plus className="w-4 h-4" />
              Add Node
            </Link>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="spinner text-accent-DEFAULT" />
          </div>
        ) : isError ? (
          <div className="card border-red-200 bg-red-50 text-center py-12">
            <ShieldAlert className="w-8 h-8 text-red-500 mx-auto mb-3" />
            <h3 className="text-red-700 font-medium">Failed to load nodes</h3>
            <p className="text-red-600 text-sm mt-1">Backend connection error</p>
          </div>
        ) : data?.nodes.length === 0 ? (
          <div className="card text-center py-16">
            <Server className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-gray-900 font-medium text-lg mb-1">No nodes found</h3>
            <p className="text-gray-500 text-sm mb-6">Get started by adding your first device.</p>
            <Link to="/nodes/add" className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Add Node
            </Link>
          </div>
        ) : view === 'card' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data?.nodes.map((node) => (
              <div
                key={node.id}
                className="card hover:shadow-md transition-shadow cursor-pointer flex flex-col"
                onClick={() => navigate(`/nodes/${node.id}`)}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Terminal className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 truncate" title={node.hostname}>
                        {node.hostname}
                      </h3>
                      <p className="text-xs text-gray-500 uppercase tracking-wider">{node.device_kind}</p>
                    </div>
                  </div>
                  <StatusBadge status={liveStatus(node.status, node.id)} />
                </div>
                
                <div className="mt-auto space-y-2 text-sm">
                  <div className="flex justify-between text-gray-500">
                    <span>Address</span>
                    <span className="text-gray-900 font-medium truncate max-w-[140px]" title={node.host || node.serial_port || ''}>
                      {node.host || node.serial_port || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>Protocol</span>
                    <span className="text-gray-900 uppercase text-xs font-semibold bg-gray-100 px-2 py-0.5 rounded">
                      {node.transport}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="table-wrap">
            <table className="ds-table">
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>IP / Port</th>
                  <th>Type</th>
                  <th>Protocol</th>
                  <th>Status</th>
                  <th className="text-right">Added</th>
                </tr>
              </thead>
              <tbody>
                {data?.nodes.map((node) => (
                  <tr key={node.id} onClick={() => navigate(`/nodes/${node.id}`)} className="cursor-pointer">
                    <td className="font-medium text-gray-900">{node.hostname}</td>
                    <td className="font-mono text-xs">{node.host || node.serial_port || '-'}</td>
                    <td className="capitalize">{node.device_kind}</td>
                    <td className="uppercase text-xs font-semibold">{node.transport}</td>
                    <td><StatusBadge status={liveStatus(node.status, node.id)} /></td>
                    <td className="text-right text-gray-500">
                      {new Date(node.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
