import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Clock, Copy, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Topbar } from '../components/shared/Topbar'
import { listHistory, type HistoryEntry } from '../lib/api'

/**
 * HistoryPage
 * แสดง operation แบบ newest-first ตาม Design พร้อมขยาย command/result ที่ redact แล้ว
 */
export function HistoryPage({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (value: boolean) => void }) {
  const [nodeFilter, setNodeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const historyQuery = useQuery({
    queryKey: ['history', nodeFilter, statusFilter],
    queryFn: () => listHistory(nodeFilter || undefined, statusFilter || undefined),
  })

  return <div className="flex-1 flex flex-col min-h-screen">
    <Topbar collapsed={collapsed} setCollapsed={setCollapsed} title="Command History" breadcrumbs={<Link to="/" className="text-gray-500 hover:text-accent-DEFAULT">Nodes</Link>} />
    <main className="p-6 max-w-7xl mx-auto w-full">
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <select className="select-field w-auto min-w-44" value={nodeFilter} onChange={(event) => setNodeFilter(event.target.value)}>
          <option value="">All Nodes</option>
          {Array.from(new Set((historyQuery.data ?? []).map((entry) => entry.node_id))).map((nodeId) => <option key={nodeId} value={nodeId}>{nodeId}</option>)}
        </select>
        <select className="select-field w-auto min-w-36" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All Status</option><option value="success">Success</option><option value="failed">Failed</option><option value="partial_failed">Partial Failed</option>
        </select>
        <span className="text-sm text-gray-500 ml-auto">Audit history ลบไม่ได้จากหน้านี้</span>
      </div>
      {historyQuery.isLoading && <div className="card flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-blue-600" /></div>}
      {historyQuery.isError && <div className="card border-red-200 bg-red-50 text-red-700">โหลดประวัติไม่สำเร็จ</div>}
      {!historyQuery.isLoading && !historyQuery.isError && <HistoryTable entries={historyQuery.data ?? []} expanded={expanded} setExpanded={setExpanded} />}
    </main>
  </div>
}

function HistoryTable({ entries, expanded, setExpanded }: { entries: HistoryEntry[]; expanded: string | null; setExpanded: (id: string | null) => void }) {
  if (entries.length === 0) return <div className="card text-center py-16"><Clock className="w-9 h-9 text-gray-300 mx-auto mb-3" /><p className="text-gray-500">ยังไม่มี command history</p></div>
  return <div className="table-wrap"><table className="ds-table"><thead><tr><th className="w-8" /><th>Time</th><th>Node</th><th>Command Type</th><th>Status</th></tr></thead><tbody>{entries.map((entry) => {
    const isOpen = expanded === entry.id
    return <HistoryRow key={entry.id} entry={entry} isOpen={isOpen} onToggle={() => setExpanded(isOpen ? null : entry.id)} />
  })}</tbody></table></div>
}

function HistoryRow({ entry, isOpen, onToggle }: { entry: HistoryEntry; isOpen: boolean; onToggle: () => void }) {
  const statusClass = entry.overall_status === 'success' ? 'badge-green' : entry.overall_status === 'partial_failed' ? 'badge-amber' : 'badge-red'
  const copy = () => navigator.clipboard.writeText(entry.commands.join('\n'))
  return <>
    <tr onClick={onToggle} className="cursor-pointer"><td>{isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</td><td className="font-mono text-xs">{new Date(entry.created_at).toLocaleString()}</td><td className="font-mono text-xs">{entry.node_id}</td><td>{entry.command_type}</td><td><span className={`badge ${statusClass}`}><span className="badge-dot" />{entry.overall_status}</span></td></tr>
    {isOpen && <tr><td colSpan={5} className="bg-gray-50"><div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-2"><div><div className="flex items-center justify-between text-xs font-semibold text-gray-500 mb-2">COMMAND <button type="button" className="btn-ghost btn-sm" onClick={(event) => { event.stopPropagation(); copy() }}><Copy className="w-3 h-3" />Copy</button></div><pre className="terminal-area rounded-lg p-3 text-xs whitespace-pre-wrap overflow-auto max-h-56">{entry.commands.join('\n')}</pre></div><div><div className="text-xs font-semibold text-gray-500 mb-2">RESULT</div><pre className="rounded-lg border border-gray-200 bg-white p-3 text-xs whitespace-pre-wrap overflow-auto max-h-56">{entry.results.map((result) => `${result.status === 'success' ? '✓' : '✕'} ${result.command}\n${result.output}`).join('\n\n')}</pre></div></div></td></tr>}
  </>
}
