// หน้ารายการอุปกรณ์: แสดงข้อมูลจริงและผลตรวจการเชื่อมต่อล่าสุด
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, LayoutGrid, List, Plus, RefreshCw, Router, Search, Server, ShieldAlert, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Topbar } from '../components/shared/Topbar'
import { StatusBadge } from '../components/shared/StatusBadge'
import { deleteNode, listNodes, type NodeResponse, type NodeStatus, testNodeConnection } from '../lib/api'
import '../device-index.css'

interface NodesPageProps {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

function DeviceIdentity({ node }: { node: NodeResponse }) {
  const Icon = node.device_kind === 'switch' ? Server : Router
  return (
    <div className="index-identity">
      <Icon className="index-device-symbol" aria-hidden="true" />
      <div className="index-device-label">
        <Link to={`/nodes/${node.id}`} className="index-node-name" title={node.hostname}>{node.hostname}</Link>
        <span className="index-device-kind">{node.device_kind === 'switch' ? 'Switch' : 'Router'}</span>
      </div>
    </div>
  )
}

function DeviceActions({ node, onDelete, pending }: { node: NodeResponse; onDelete: (node: NodeResponse) => void; pending: boolean }) {
  return (
    <div className="index-actions">
      <Link to={`/nodes/${node.id}`} className="index-primary configure-action" aria-label={`Configure ${node.hostname}`}>
        <ArrowRight size={17} aria-hidden="true" />Configure
      </Link>
      <button type="button" className="index-delete" onClick={() => onDelete(node)} disabled={pending} aria-label={`ลบ Node ${node.hostname}`} title={`ลบ Node ${node.hostname}`}>
        <Trash2 size={18} aria-hidden="true" />
      </button>
    </div>
  )
}

export function NodesPage({ collapsed, setCollapsed }: NodesPageProps) {
  const [search, setSearch] = useState('')
  const [view, setView] = useState<'card' | 'table'>('table')
  const [statusFilter, setStatusFilter] = useState<NodeStatus | ''>('')
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteNode(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] })
      queryClient.invalidateQueries({ queryKey: ['history'] })
    },
  })
  const confirmDelete = (node: NodeResponse) => {
    if (window.confirm(`ยืนยันลบ Node ${node.hostname} ออกจากแอปหรือไม่? Config บนอุปกรณ์จะไม่เปลี่ยน และ History เดิมยังอยู่`)) {
      deleteMutation.mutate(node.id)
    }
  }
  const { data, isLoading, isError, refetch } = useQuery({
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
  const liveStatus = (node: NodeResponse): NodeStatus => {
    const health = healthById.get(node.id)
    // เมื่อ polling ชน config lock ให้คงสถานะล่าสุด ไม่แสดง Unknown ชั่วคราว
    if (!health || health.isError) return node.status
    if (health.isFetching && !health.data) return 'checking'
    if (health.data?.overall_status === 'success') return 'connected'
    if (health.data?.overall_status === 'failed') return 'unreachable'
    return node.status
  }
  const nodes = (data?.nodes ?? []).filter((node) => !statusFilter || liveStatus(node) === statusFilter)
  const clearFilters = () => { setSearch(''); setStatusFilter('') }

  return (
    <div className="device-index-page">
      <Topbar collapsed={collapsed} setCollapsed={setCollapsed} title="Nodes" variant="breadcrumb" />
      <main className="device-index-content">
        <div className="index-heading">
          <div>
            <h1>Nodes</h1>
            <p>จัดการอุปกรณ์และเปิดหน้าตั้งค่า Interface หรือ Routing</p>
          </div>
          <Link to="/nodes/add" className="index-primary index-add"><Plus size={21} aria-hidden="true" />Add Node</Link>
        </div>
        {deleteMutation.isError && <p role="alert" className="index-error"><ShieldAlert size={18} aria-hidden="true" />ลบ Node ไม่สำเร็จ กรุณาลองใหม่</p>}
        <div className="index-toolbar">
          <div className="index-search">
            <Search size={20} aria-hidden="true" />
            <input type="search" placeholder="ค้นหาชื่ออุปกรณ์หรือ IP" aria-label="ค้นหาชื่ออุปกรณ์หรือ IP" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') setSearch('') }} />
          </div>
          <select className="index-status-filter" aria-label="กรองสถานะอุปกรณ์" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as NodeStatus | '')}>
            <option value="">ทุกสถานะ</option>
            <option value="connected">Connected</option>
            <option value="unreachable">Unreachable</option>
            <option value="checking">Checking</option>
            <option value="unknown">Unknown</option>
          </select>
          <div className="index-view-switch" role="group" aria-label="มุมมองรายการอุปกรณ์">
            <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}><List size={19} aria-hidden="true" />Table</button>
            <button type="button" aria-pressed={view === 'card'} onClick={() => setView('card')}><LayoutGrid size={18} aria-hidden="true" />Cards</button>
          </div>
        </div>
        <p className="index-status-note">สถานะเป็นผลตรวจล่าสุด · ตรวจซ้ำทุก 30 วินาทีขณะเปิดหน้านี้</p>
        {isLoading ? (
          <div className="index-state" role="status"><RefreshCw className="index-spin" aria-hidden="true" /><p>กำลังโหลดรายการอุปกรณ์…</p></div>
        ) : isError ? (
          <div className="index-state" role="alert">
            <ShieldAlert aria-hidden="true" /><h2>โหลดรายการอุปกรณ์ไม่สำเร็จ</h2>
            <p>ตรวจสอบว่า backend ทำงานอยู่ แล้วลองอีกครั้ง</p>
            <button type="button" className="index-secondary" onClick={() => refetch()}><RefreshCw size={17} aria-hidden="true" />ลองอีกครั้ง</button>
          </div>
        ) : nodes.length === 0 ? (
          <div className="index-state">
            <Server aria-hidden="true" /><h2>{search || statusFilter ? 'ไม่พบอุปกรณ์ที่ตรงกับตัวกรอง' : 'ยังไม่มีอุปกรณ์'}</h2>
            <p>{search || statusFilter ? 'เปลี่ยนคำค้นหรือสถานะเพื่อดูรายการอื่น' : 'เพิ่มอุปกรณ์และทดสอบการเชื่อมต่อก่อนเริ่มตั้งค่า'}</p>
            {search || statusFilter ? <button type="button" className="index-secondary" onClick={clearFilters}>ล้างตัวกรอง</button> : <Link to="/nodes/add" className="index-primary"><Plus size={18} aria-hidden="true" />Add Node</Link>}
          </div>
        ) : view === 'table' ? (
          <div className="index-table-scroll" role="region" aria-label="รายการอุปกรณ์" tabIndex={0}>
            <table className="index-table">
              <caption className="sr-only">รายการอุปกรณ์และผลตรวจการเชื่อมต่อล่าสุด</caption>
              <colgroup><col style={{ width: '20%' }} /><col style={{ width: '23%' }} /><col style={{ width: '16%' }} /><col style={{ width: '19%' }} /><col style={{ width: '22%' }} /></colgroup>
              <thead><tr><th scope="col">Node</th><th scope="col">IP / Console port</th><th scope="col">Connection</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead>
              <tbody>{nodes.map((node) => (
                <tr key={node.id}>
                  <td><DeviceIdentity node={node} /></td>
                  <td className="index-endpoint">{node.host || node.serial_port || '—'}</td>
                  <td className="index-transport">{node.transport}</td>
                  <td><StatusBadge status={liveStatus(node)} /></td>
                  <td><DeviceActions node={node} onDelete={confirmDelete} pending={deleteMutation.isPending} /></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : (
          <div className="index-cards">{nodes.map((node) => (
            <article key={node.id} className="index-device-card">
              <DeviceIdentity node={node} />
              <div className="index-card-endpoint"><span className="index-endpoint">{node.host || node.serial_port || '—'}</span><span className="index-transport">{node.transport}</span></div>
              <StatusBadge status={liveStatus(node)} />
              <DeviceActions node={node} onDelete={confirmDelete} pending={deleteMutation.isPending} />
            </article>
          ))}</div>
        )}
      </main>
    </div>
  )
}
