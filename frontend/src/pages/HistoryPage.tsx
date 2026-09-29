// หน้า Command History แสดง audit ตาม Design โดยกรองและแบ่งหน้าได้
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, Clock, Copy, Loader2, RefreshCw, TriangleAlert, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Topbar } from '../components/shared/Topbar'
import { listHistory, listHistoryNodes, listNodes, type HistoryEntry } from '../lib/api'

const PAGE_SIZE = 10
// datetime-local เลือกละเอียดระดับนาที; ขอบเขตบนแบบ exclusive จึงต้องเลื่อนไปอีกหนึ่งนาที
const MINUTE_MS = 60_000
const statusLabels = { success: 'สำเร็จ', failed: 'ไม่สำเร็จ', partial_failed: 'สำเร็จบางส่วน' }
const commandLabels: Record<string, string> = {
  'Interface Configuration': 'ตั้งค่า Interface',
  'Interface Admin State': 'เปิด/ปิด Interface',
  'Loopback Configuration': 'ตั้งค่า Loopback',
  'Static Route Configuration': 'ตั้งค่า Static Route',
  'RIP Configuration': 'ตั้งค่า RIP',
  'OSPF Configuration': 'ตั้งค่า OSPF',
  'EIGRP Configuration': 'ตั้งค่า EIGRP',
  'BGP Configuration': 'ตั้งค่า BGP',
  'Save Configuration': 'บันทึก Config',
  'Show Command': 'ดูข้อมูลอุปกรณ์',
}

/** แสดง audit ของคำสั่งที่ส่งอุปกรณ์แบบ newest-first */
export function HistoryPage({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (value: boolean) => void }) {
  const [nodeFilter, setNodeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [timeFrom, setTimeFrom] = useState('')
  const [timeTo, setTimeTo] = useState('')
  const [page, setPage] = useState(0)
  const [expanded, setExpanded] = useState<string | null>(null)
  const fromMillis = timeFrom ? new Date(timeFrom).getTime() : null
  const toMillis = timeTo ? new Date(timeTo).getTime() : null
  const timeError = (fromMillis !== null && Number.isNaN(fromMillis)) || (toMillis !== null && Number.isNaN(toMillis))
    ? 'กรุณาระบุวันและเวลาที่ถูกต้อง'
    : fromMillis !== null && toMillis !== null && fromMillis > toMillis
      ? 'เวลาสิ้นสุดต้องไม่อยู่ก่อนเวลาเริ่มต้น'
      : ''
  const nodesQuery = useQuery({ queryKey: ['nodes'], queryFn: () => listNodes() })
  const historyNodesQuery = useQuery({ queryKey: ['history-nodes'], queryFn: listHistoryNodes })
  const historyQuery = useQuery({
    queryKey: ['history', nodeFilter, statusFilter, timeFrom, timeTo, page, PAGE_SIZE],
    queryFn: () => listHistory(nodeFilter || undefined, statusFilter || undefined, PAGE_SIZE, page * PAGE_SIZE,
      fromMillis === null ? undefined : new Date(fromMillis).toISOString(),
      toMillis === null ? undefined : new Date(toMillis + MINUTE_MS).toISOString()),
    enabled: !timeError,
  })
  const items = historyQuery.data?.items ?? []
  const total = historyQuery.data?.total ?? 0
  const hasFilter = Boolean(nodeFilter || statusFilter || timeFrom || timeTo)
  const currentNodes = nodesQuery.data?.nodes ?? []
  const nodeNames = new Map(currentNodes.map((node) => [node.id, node.hostname]))
  const archivedNodes = (historyNodesQuery.data ?? []).filter((node) => !nodeNames.has(node.id))
  const changeFilter = (node: string, status: string) => { setNodeFilter(node); setStatusFilter(status); setPage(0); setExpanded(null) }
  const changeTime = (from: string, to: string) => { setTimeFrom(from); setTimeTo(to); setPage(0); setExpanded(null) }
  const clearFilters = () => { changeFilter('', ''); changeTime('', '') }

  return <div className="flex-1 flex flex-col min-h-screen">
    <Topbar collapsed={collapsed} setCollapsed={setCollapsed} title="Command History" breadcrumbs={<Link to="/" className="text-gray-500 hover:text-accent-DEFAULT">Nodes</Link>} />
    <main className="p-6 max-w-4xl mx-auto w-full">
      <div className="mb-4 flex flex-col gap-1 lg:flex-row lg:items-center lg:justify-between">
        <p className="text-sm text-slate-600">ตรวจสอบคำสั่งที่ส่งไปยังอุปกรณ์ ผลลัพธ์แต่ละคำสั่ง และเวลาที่ดำเนินการ รายการนี้เป็นบันทึกย้อนหลัง ไม่ใช่ค่าปัจจุบันของอุปกรณ์</p>
        {historyQuery.isSuccess && <span className="text-sm font-medium text-slate-700" aria-live="polite">{hasFilter ? 'พบ' : 'ทั้งหมด'} {total} รายการ</span>}
      </div>
      <div className="card mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600" htmlFor="history-node">Node</label>
          <select id="history-node" className="select-field" value={nodeFilter} onChange={(event) => changeFilter(event.target.value, statusFilter)}>
            <option value="">ทุก Node</option>
            {currentNodes.map((node) => <option key={node.id} value={node.id}>{node.hostname}</option>)}
            {archivedNodes.map((node) => <option key={node.id} value={node.id}>{node.hostname ?? node.id} (ลบแล้ว)</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600" htmlFor="history-status">สถานะ</label>
          <select id="history-status" className="select-field" value={statusFilter} onChange={(event) => changeFilter(nodeFilter, event.target.value)}>
            <option value="">ทุกสถานะ</option><option value="success">สำเร็จ</option><option value="failed">ไม่สำเร็จ</option><option value="partial_failed">สำเร็จบางส่วน</option>
          </select>
        </div>
        <div><label className="mb-1 block text-xs font-semibold text-slate-600" htmlFor="history-from">ตั้งแต่</label><input id="history-from" type="datetime-local" className="input-field w-full min-w-0" value={timeFrom} onChange={(event) => changeTime(event.target.value, timeTo)} /></div>
        <div><label className="mb-1 block text-xs font-semibold text-slate-600" htmlFor="history-to">ถึง</label><input id="history-to" type="datetime-local" className="input-field w-full min-w-0" value={timeTo} onChange={(event) => changeTime(timeFrom, event.target.value)} /></div>
        </div>
        <p className="mt-2 text-xs text-slate-500">ช่วงเวลาใช้เวลาท้องถิ่นของเครื่องที่เปิดเว็บ และรวมรายการที่เกิดภายในนาทีสิ้นสุดที่เลือก</p>
        {timeError && <p role="alert" className="mt-2 text-sm text-red-700">{timeError}</p>}
        <div className="mt-3 flex items-center justify-between gap-3">
        {hasFilter ? <button type="button" className="btn-ghost btn-sm" onClick={clearFilters}>ล้างตัวกรอง</button> : <span />}
        <button type="button" className="btn-ghost btn-sm inline-flex items-center gap-1.5 whitespace-nowrap" onClick={() => { historyQuery.refetch(); nodesQuery.refetch(); historyNodesQuery.refetch() }} disabled={historyQuery.isFetching || Boolean(timeError)}>
          <RefreshCw className={`w-4 h-4 ${historyQuery.isFetching ? 'animate-spin' : ''}`} />รีเฟรช
        </button>
        </div>
      </div>
      {(nodesQuery.isError || historyNodesQuery.isError) && <p role="alert" className="text-sm text-red-700 mb-3">โหลดตัวเลือก Node ไม่สำเร็จ <button type="button" className="underline" onClick={() => { nodesQuery.refetch(); historyNodesQuery.refetch() }}>ลองอีกครั้ง</button></p>}
      {historyQuery.isLoading && <div className="card flex justify-center py-12" role="status"><Loader2 className="w-6 h-6 animate-spin text-blue-600" /><span className="sr-only">กำลังโหลดประวัติ</span></div>}
      {historyQuery.isError && <div className="card border-red-200 bg-red-50 text-red-700" role="alert">โหลดประวัติไม่สำเร็จ <button type="button" className="underline" onClick={() => historyQuery.refetch()}>ลองอีกครั้ง</button></div>}
      {!timeError && historyQuery.isSuccess && <>
        <HistoryTable entries={items} nodeNames={nodeNames} filtered={hasFilter} expanded={expanded} setExpanded={setExpanded} />
        {total > PAGE_SIZE && <nav aria-label="หน้าประวัติ" className="mt-4 flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:justify-between">
          <span className="text-slate-600">หน้า {page + 1} จาก {Math.ceil(total / PAGE_SIZE)} · {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} จาก {total} รายการ</span>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-secondary btn-sm inline-flex items-center gap-1.5 whitespace-nowrap disabled:cursor-not-allowed" disabled={page === 0} onClick={() => { setPage(page - 1); setExpanded(null) }}><ChevronLeft className="w-4 h-4" />ก่อนหน้า</button>
            <button type="button" className="btn-secondary btn-sm inline-flex items-center gap-1.5 whitespace-nowrap disabled:cursor-not-allowed" disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => { setPage(page + 1); setExpanded(null) }}>ถัดไป<ChevronRight className="w-4 h-4" /></button>
          </div>
        </nav>}
      </>}
    </main>
  </div>
}

/** ตารางผลพร้อมปุ่มขยายที่ใช้คีย์บอร์ดได้ */
function HistoryTable({ entries, nodeNames, filtered, expanded, setExpanded }: { entries: HistoryEntry[]; nodeNames: Map<string, string>; filtered: boolean; expanded: string | null; setExpanded: (id: string | null) => void }) {
  if (entries.length === 0) return <div className="card text-center py-16"><Clock className="w-9 h-9 text-gray-300 mx-auto mb-3" /><p className="font-medium text-gray-700">{filtered ? 'ไม่พบรายการตามตัวกรอง' : 'ยังไม่มีประวัติคำสั่ง'}</p><p className="mt-1 text-sm text-gray-500">{filtered ? 'ลองปรับ Node สถานะ หรือช่วงเวลา' : 'ประวัติจะปรากฏหลังสั่ง Show หรือ Apply การตั้งค่า'}</p></div>
  return <><div className="space-y-3 lg:hidden">{entries.map((entry) => {
    const isOpen = expanded === entry.id
    return <HistoryCard key={entry.id} entry={entry} nodeName={nodeNames.get(entry.node_id) ?? entry.node_hostname ?? entry.node_id} isOpen={isOpen} onToggle={() => setExpanded(isOpen ? null : entry.id)} />
  })}</div><div className="table-wrap hidden lg:block"><table className="ds-table table-fixed"><colgroup><col className="w-10" /><col className="w-36" /><col className="w-36" /><col /><col className="w-28" /><col className="w-36" /></colgroup><thead><tr><th /><th>เวลา</th><th>Node</th><th>ประเภทคำสั่ง</th><th>สถานะ</th><th className="!text-center">รายละเอียด</th></tr></thead><tbody>{entries.map((entry) => {
    const isOpen = expanded === entry.id
    return <HistoryRow key={entry.id} entry={entry} nodeName={nodeNames.get(entry.node_id) ?? entry.node_hostname ?? entry.node_id} isOpen={isOpen} onToggle={() => setExpanded(isOpen ? null : entry.id)} />
  })}</tbody></table></div></>
}

/** แถว audit ที่เปิดผลแต่ละคำสั่งและคัดลอกคำสั่งได้ */
function HistoryRow({ entry, nodeName, isOpen, onToggle }: { entry: HistoryEntry; nodeName: string; isOpen: boolean; onToggle: () => void }) {
  return <>
    <tr><td>{isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</td>
      <td className="whitespace-nowrap"><span className="block font-medium">{new Date(entry.created_at).toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: '2-digit' })}</span><span className="block text-xs text-slate-500">{new Date(entry.created_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span></td>
      <td className="font-semibold truncate" title={nodeName}>{nodeName}</td><td><span className="font-medium">{commandLabels[entry.command_type] ?? entry.command_type}</span>{commandLabels[entry.command_type] && <span className="block text-xs text-slate-500">{entry.command_type}</span>}</td>
      <td><HistoryStatus entry={entry} /></td>
      <td className="text-center"><button type="button" className="btn-ghost btn-sm inline-flex justify-center whitespace-nowrap" aria-expanded={isOpen} aria-controls={`history-detail-table-${entry.id}`} onClick={onToggle}>{isOpen ? 'ซ่อน' : 'ดูรายละเอียด'}</button></td></tr>
    {isOpen && <tr id={`history-detail-table-${entry.id}`}><td colSpan={6} className="bg-gray-50"><HistoryDetail entry={entry} /></td></tr>}
  </>
}

/** รายการแท็บเล็ตที่อ่านครบโดยไม่ต้องเลื่อนตารางแนวนอน */
function HistoryCard({ entry, nodeName, isOpen, onToggle }: { entry: HistoryEntry; nodeName: string; isOpen: boolean; onToggle: () => void }) {
  return <article className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
    <button type="button" className="w-full p-4 text-left" aria-expanded={isOpen} aria-controls={`history-detail-card-${entry.id}`} onClick={onToggle}>
      <span className="flex items-start justify-between gap-3"><span className="min-w-0"><span className="block text-xs text-slate-500">{new Date(entry.created_at).toLocaleString('th-TH')}</span><span className="mt-1 block font-semibold">{nodeName} · {commandLabels[entry.command_type] ?? entry.command_type}</span></span>{isOpen ? <ChevronDown className="w-4 h-4 shrink-0" /> : <ChevronRight className="w-4 h-4 shrink-0" />}</span>
      <span className="mt-3 block"><HistoryStatus entry={entry} /></span>
    </button>
    {isOpen && <div id={`history-detail-card-${entry.id}`} className="border-t border-gray-200 bg-gray-50"><HistoryDetail entry={entry} /></div>}
  </article>
}

/** สถานะต้องใช้ไอคอนและข้อความคู่กับสี */
function HistoryStatus({ entry }: { entry: HistoryEntry }) {
  const statusClass = entry.overall_status === 'success' ? 'badge-green' : entry.overall_status === 'partial_failed' ? 'badge-amber' : 'badge-red'
  const StatusIcon = entry.overall_status === 'success' ? CheckCircle2 : entry.overall_status === 'partial_failed' ? TriangleAlert : XCircle
  return <span className={`badge ${statusClass}`}><StatusIcon className="w-3 h-3" />{statusLabels[entry.overall_status]}</span>
}

/** แสดงคำสั่งและผลก่อน ซ่อน audit IDs รองไว้ใน disclosure */
function HistoryDetail({ entry }: { entry: HistoryEntry }) {
  const [copyState, setCopyState] = useState('คัดลอก')
  const copy = async () => {
    try { await navigator.clipboard.writeText(entry.commands.join('\n')); setCopyState('คัดลอกแล้ว') }
    catch { setCopyState('คัดลอกไม่สำเร็จ') }
  }
  return <div className="p-4"><div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
    <div><div className="mb-2 flex items-center justify-between text-xs font-semibold text-gray-500">คำสั่งที่ส่ง <button type="button" className="btn-ghost btn-sm" onClick={copy}><Copy className="w-3 h-3" />{copyState}</button></div><pre className="terminal-area rounded-lg p-3 text-xs whitespace-pre-wrap overflow-auto max-h-56">{entry.commands.join('\n')}</pre></div>
    <div><div className="mb-2 text-xs font-semibold text-gray-500">ผลลัพธ์จากอุปกรณ์</div><div className="rounded-lg border border-gray-200 bg-white p-3 text-xs overflow-auto max-h-56 space-y-3">{entry.results.map((result, index) => <div key={index}><span className={result.status === 'success' ? 'text-green-700' : 'text-red-700'}>{result.status === 'success' ? 'สำเร็จ' : 'ไม่สำเร็จ'}</span> · <code>{result.command}</code>{result.error_code && <span className="text-red-700"> · {result.error_code}</span>}<pre className="whitespace-pre-wrap">{result.output || 'ไม่มีผลลัพธ์เพิ่มเติม'}</pre></div>)}</div></div>
  </div><details className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer w-fit">ข้อมูลอ้างอิง</summary><p className="mt-2 break-all">Correlation ID: {entry.correlation_id}{entry.operation_id && ` · Operation ID: ${entry.operation_id}`}</p></details></div>
}
