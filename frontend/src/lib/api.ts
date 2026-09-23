// ไคลเอนต์ API สำหรับเรียก NetConfig backend
// ส่ง typed request และจัดการ error response มาตรฐาน

import axios, { AxiosError } from 'axios'

// ---------------------------------------------------------------------------
// Types ที่ตรงกับ backend Pydantic schemas
// ---------------------------------------------------------------------------

export type TransportType = 'ssh' | 'telnet' | 'serial'
export type DeviceKind = 'router' | 'switch'
export type NodeStatus = 'connected' | 'unreachable' | 'checking' | 'unknown'
export type StepStatus = 'pending' | 'success' | 'failed' | 'skipped'

export interface SSHTransport {
  transport: 'ssh'
  host: string
  port: number
  username: string
  password: string
  secret?: string
}

export interface TelnetTransport {
  transport: 'telnet'
  host: string
  port: number
  username?: string
  password: string
  secret?: string
}

export interface SerialTransport {
  transport: 'serial'
  serial_port: string
  baudrate: number
  username?: string
  password?: string
  secret?: string
}

export type TransportConfig = SSHTransport | TelnetTransport | SerialTransport

export interface NodeCreate {
  hostname: string
  device_kind: DeviceKind
  transport_config: TransportConfig
}

export interface ScanResult { host: string; open_ports: number[] }
export interface ScanSubnetResponse { subnet: string; results: ScanResult[] }

export interface NodeResponse {
  id: string
  hostname: string
  host?: string
  transport: TransportType
  port?: number
  serial_port?: string
  device_kind: DeviceKind
  status: NodeStatus
  created_at: string
  updated_at: string
}

export interface NodeListResponse {
  total: number
  nodes: NodeResponse[]
}

export interface ConnectionStep {
  step: string
  status: StepStatus
  message: string
  detail?: string
}

export interface TestConnectionResponse {
  node_id: string
  overall_status: StepStatus
  steps: ConnectionStep[]
  hostname_detected?: string
}

export interface ApiError {
  code: string
  message_th: string
  correlation_id: string
  details?: Record<string, unknown>
}

export interface InterfaceConfig {
  interface_name: string
  ip_address: string
  subnet_mask: string
  description?: string
  admin_up: boolean
}

export interface InterfaceAdminConfig {
  interface_name: string
  admin_up: boolean
}

export interface InterfaceCurrentResponse {
  node_id: string
  interface_name: string
  ip_address?: string
  subnet_mask?: string
  description?: string
  admin_up: boolean
  status: string
  protocol: string
  collected_at: string
}

export interface LoopbackConfig {
  loopback_id: number
  ip_address: string
  subnet_mask: string
  description?: string
  admin_up: boolean
}

export interface LoopbackRemoveConfig {
  loopback_id: number
}

export interface DeviceCapabilitiesResponse {
  node_id: string
  switchport_supported: boolean
  vlan_supported: boolean
  collected_at: string
}

export interface InterfaceCapabilitiesResponse {
  node_id: string
  interface_name: string
  switchport_state: 'enabled' | 'disabled' | 'unsupported' | 'unknown'
  collected_at: string
}

export interface VlanEntry {
  vlan_id: number
  name: string
  status: string
  ports: string[]
}

export interface VlanListResponse {
  node_id: string
  vlans: VlanEntry[]
  collected_at: string
}

export interface AccessPortConfig {
  interface_name: string
  vlan_id: number
  description?: string
  admin_up: boolean
}

export interface VlanConfig {
  vlan_id: number
  name?: string
}

export interface VlanRemoveConfig {
  vlan_id: number
}

export interface SviConfig {
  vlan_id: number
  ip_address: string
  subnet_mask: string
  description?: string
  admin_up: boolean
}

export interface SviRemoveConfig {
  vlan_id: number
}

export interface RoutedPortConfig {
  interface_name: string
  ip_address: string
  subnet_mask: string
  description?: string
  admin_up: boolean
}

export interface RoutedPortRestoreConfig {
  interface_name: string
}

export interface StaticRouteConfig {
  destination: string
  subnet_mask: string
  next_hop?: string
  exit_interface?: string
}

export interface StaticRouteUpdate {
  current: StaticRouteConfig
  desired: StaticRouteConfig
}

export interface StaticRouteEntry extends StaticRouteConfig {
  route_type: 'default' | 'static'
}

export interface StaticRouteListResponse {
  node_id: string
  routes: StaticRouteEntry[]
  collected_at: string
}

export interface RipNetworkConfig {
  version: 1 | 2
  network: string
}

export interface RipNetworkUpdate {
  current: RipNetworkConfig
  desired: RipNetworkConfig
}

export interface RipProcessConfig {
  version: 1 | 2
  networks: string[]
  no_auto_summary: boolean
}

export interface RipStateResponse {
  node_id: string
  enabled: boolean
  version?: 1 | 2
  networks: string[]
  no_auto_summary: boolean
  collected_at: string
}

export interface OspfNetworkConfig {
  process_id: number
  router_id: string
  network: string
  subnet_mask: string
  area: number
}

export interface OspfNetworkUpdate { current: OspfNetworkConfig; desired: OspfNetworkConfig }
export interface OspfProcessConfig { process_id: number; router_id?: string; networks: OspfNetworkConfig[] }
export interface OspfStateResponse { node_id: string; enabled: boolean; process_id?: number; router_id?: string; networks: OspfNetworkConfig[]; collected_at: string }

export interface EigrpNetworkConfig { as_number: number; router_id: string; network: string; subnet_mask: string }
export interface EigrpNetworkUpdate { current: EigrpNetworkConfig; desired: EigrpNetworkConfig }
export interface EigrpProcessConfig { as_number: number; router_id?: string; networks: EigrpNetworkConfig[]; no_auto_summary: boolean }
export interface EigrpStateResponse { node_id: string; enabled: boolean; as_number?: number; router_id?: string; networks: EigrpNetworkConfig[]; no_auto_summary: boolean; collected_at: string }
export interface BgpNeighborConfig { local_as: number; router_id: string; neighbor_ip: string; remote_as: number; description?: string }
export interface BgpNetworkConfig { local_as: number; network: string; subnet_mask: string }
export interface BgpNeighborUpdate { current: BgpNeighborConfig; desired: BgpNeighborConfig }
export interface BgpNetworkUpdate { current: BgpNetworkConfig; desired: BgpNetworkConfig }
export interface BgpProcessConfig { local_as: number; router_id?: string; neighbors: BgpNeighborConfig[]; networks: BgpNetworkConfig[] }
export interface BgpStateResponse { node_id: string; enabled: boolean; local_as?: number; router_id?: string; neighbors: BgpNeighborConfig[]; networks: BgpNetworkConfig[]; collected_at: string }

export interface PreviewResponse {
  operation_id: string
  node_id: string
  operation_type: string
  payload_hash: string
  commands: string[]
  expires_at: string
  warnings: string[]
}

export interface CommandResult {
  command: string
  status: 'success' | 'failed'
  output: string
  error_code?: string
}

export interface ApplyResponse {
  operation_id: string
  node_id: string
  correlation_id: string
  overall_status: 'success' | 'failed' | 'partial_failed'
  results: CommandResult[]
}

export interface ShowResponse {
  node_id: string
  command: string
  output: string
  parsed?: Record<string, string>[]
  collected_at: string
}

export interface HistoryEntry {
  id: string
  node_id: string
  operation_id?: string
  command_type: string
  commands: string[]
  results: CommandResult[]
  overall_status: 'success' | 'failed' | 'partial_failed'
  created_at: string
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// แปลง Axios error เป็น ApiError เพื่อให้ UI แสดงข้อความไทยได้
function extractApiError(error: AxiosError): ApiError {
  const data = error.response?.data as Record<string, unknown> | undefined
  if (data?.code) {
    return data as unknown as ApiError
  }
  // FastAPI validation error format
  if (data?.detail) {
    if (typeof data.detail === 'object' && (data.detail as Record<string, unknown>).code) {
      return data.detail as ApiError
    }
    return {
      code: 'VALIDATION_ERROR',
      message_th: 'ข้อมูลที่กรอกไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง',
      correlation_id: '',
      details: { raw: data.detail },
    }
  }
  if (error.response?.status === 404) {
    return {
      code: 'API_NOT_FOUND',
      message_th: 'Backend ที่กำลังรันยังไม่มี API นี้ กรุณารีสตาร์ท Backend แล้วลองใหม่',
      correlation_id: '',
    }
  }
  return {
    code: 'NETWORK_ERROR',
    message_th: 'ไม่สามารถเชื่อมต่อ backend ได้ กรุณาตรวจสอบว่า server กำลังทำงาน',
    correlation_id: '',
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/** รายการ nodes พร้อม optional search */
export async function listNodes(query?: string): Promise<NodeListResponse> {
  const params = query ? { q: query } : {}
  const { data } = await api.get<NodeListResponse>('/nodes', { params })
  return data
}

/** ดูข้อมูล node เดียว */
export async function getNode(id: string): Promise<NodeResponse> {
  const { data } = await api.get<NodeResponse>(`/nodes/${id}`)
  return data
}

/** สร้าง node ใหม่ */
export async function createNode(payload: NodeCreate): Promise<NodeResponse> {
  try {
    const { data } = await api.post<NodeResponse>('/nodes', payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** ลบ node */
export async function deleteNode(id: string): Promise<void> {
  try {
    await api.delete(`/nodes/${id}`)
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** ทดสอบ connection step-by-step */
export async function testNodeConnection(id: string): Promise<TestConnectionResponse> {
  try {
    const { data } = await api.post<TestConnectionResponse>(`/nodes/${id}/test`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** ทดสอบ connection จาก typed payload โดยยังไม่บันทึก node */
export async function testNodeConnectionDraft(payload: NodeCreate): Promise<TestConnectionResponse> {
  try {
    const { data } = await api.post<TestConnectionResponse>('/nodes/test', payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** ค้นหาเฉพาะ TCP 22/23 ใน subnet ขนาดเล็กสำหรับ Add Node */
export async function scanSubnet(subnet: string): Promise<ScanSubnetResponse> {
  try { const { data } = await api.post<ScanSubnetResponse>('/nodes/scan', { subnet }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview interface โดยยังไม่ส่งคำสั่งไปอุปกรณ์ */
export async function previewInterface(id: string, payload: InterfaceConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/interface/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview เปิด/ปิด interface โดยไม่เปลี่ยน IPv4 เดิม */
export async function previewInterfaceAdmin(id: string, payload: InterfaceAdminConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/interface/admin/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply เฉพาะ preview ที่ operation/hash ยังตรงกัน */
export async function applyInterface(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/interface/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply preview ของ admin state หลังผู้ใช้ยืนยันใน drawer */
export async function applyInterfaceAdmin(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/interface/admin/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview Loopback ใหม่โดย browser ไม่ประกอบ CLI เอง */
export async function previewLoopback(id: string, payload: LoopbackConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/loopback/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview ลบ Loopback ที่ระบุ เพื่อให้ผู้ใช้ยืนยันก่อน Apply */
export async function previewLoopbackRemove(id: string, payload: LoopbackRemoveConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/loopback/remove/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply Loopback preview ที่ backend ตรวจ hash และ TTL แล้ว */
export async function applyLoopback(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/loopback/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่าน capability ด้วย show command ที่ backend ควบคุม ไม่เดาชื่อ node */
export async function getDeviceCapabilities(id: string): Promise<DeviceCapabilitiesResponse> {
  try {
    const { data } = await api.get<DeviceCapabilitiesResponse>(`/nodes/${id}/capabilities`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่านสถานะ switchport ของ interface โดย backend สร้าง show command เอง */
export async function getInterfaceCapabilities(id: string, interfaceName: string): Promise<InterfaceCapabilitiesResponse> {
  try {
    const { data } = await api.get<InterfaceCapabilitiesResponse>(`/nodes/${id}/interfaces/${encodeURIComponent(interfaceName)}/capabilities`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่าน VLAN actual state ที่ backend parse จาก show vlan brief */
export async function listVlans(id: string): Promise<VlanListResponse> {
  try {
    const { data } = await api.get<VlanListResponse>(`/nodes/${id}/vlans`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Preview L2 access port; backend ยืนยัน switchport และ VLAN ก่อน render */
export async function previewAccessPort(id: string, payload: AccessPortConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/access-port/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply access-port preview ที่ backend ตรวจ hash/TTL แล้ว */
export async function applyAccessPort(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/access-port/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Preview สร้าง VLAN resource ใหม่ */
export async function previewVlan(id: string, payload: VlanConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/vlan/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Preview ลบ VLAN ที่ผู้ใช้เลือก */
export async function previewVlanRemove(id: string, payload: VlanRemoveConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/vlan/remove/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Preview สร้าง SVI บน VLAN ที่มีอยู่ */
export async function previewSvi(id: string, payload: SviConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/svi/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Preview ลบ SVI โดยไม่ลบ VLAN resource ตามไปเอง */
export async function previewSviRemove(id: string, payload: SviRemoveConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/svi/remove/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply VLAN/SVI preview ที่ backend ตรวจ hash/TTL แล้ว */
export async function applyVlanSvi(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/vlan-svi/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Preview การแปลง L2 switchport เป็น L3 routed port */
export async function previewRoutedPort(id: string, payload: RoutedPortConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/routed-port/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Preview คืน L3 routed port เป็น switchport พื้นฐาน โดยไม่ restore ค่า L2 เดิม */
export async function previewRoutedPortRestore(id: string, payload: RoutedPortRestoreConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/routed-port/restore/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply routed-port preview ที่ backend ตรวจ hash/TTL แล้ว */
export async function applyRoutedPort(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/routed-port/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** อ่าน Static/Default route ปัจจุบันจาก running-config */
export async function listStaticRoutes(id: string): Promise<StaticRouteListResponse> {
  try {
    const { data } = await api.get<StaticRouteListResponse>(`/nodes/${id}/routes/static`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview สำหรับเพิ่มหรือลบ Static route */
export async function previewStaticRoute(id: string, payload: StaticRouteConfig, remove = false): Promise<PreviewResponse> {
  try {
    const action = remove ? 'remove/' : ''
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/static-route/${action}preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview สำหรับแก้ route โดย remove ค่าเดิมก่อน add ค่าใหม่ */
export async function previewStaticRouteUpdate(id: string, payload: StaticRouteUpdate): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/static-route/update/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply Static route preview ที่ operation/hash ยังตรงกัน */
export async function applyStaticRoute(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/static-route/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่าน RIP actual state จาก running-config */
export async function getRipState(id: string): Promise<RipStateResponse> {
  try {
    const { data } = await api.get<RipStateResponse>(`/nodes/${id}/routing/rip`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview เพิ่มหรือลบ RIP network */
export async function previewRipNetwork(id: string, payload: RipNetworkConfig, remove = false): Promise<PreviewResponse> {
  try {
    const action = remove ? 'remove/' : ''
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/rip/network/${action}preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview แก้ RIP network/version */
export async function previewRipNetworkUpdate(id: string, payload: RipNetworkUpdate): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/rip/network/update/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** สร้าง preview ลบ RIP process ทั้งหมด */
export async function previewRipProcessRemove(id: string, payload: RipProcessConfig): Promise<PreviewResponse> {
  try {
    const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/rip/process/remove/preview`, payload)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** Apply RIP preview ที่ operation/hash ยังตรงกัน */
export async function applyRip(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try {
    const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/rip/apply`, {
      operation_id: operationId,
      payload_hash: payloadHash,
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่าน OSPF actual state จาก running-config */
export async function getOspfState(id: string): Promise<OspfStateResponse> {
  try { const { data } = await api.get<OspfStateResponse>(`/nodes/${id}/routing/ospf`); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview เพิ่ม/ลบ OSPF network */
export async function previewOspfNetwork(id: string, payload: OspfNetworkConfig, remove = false): Promise<PreviewResponse> {
  try { const action = remove ? 'remove/' : ''; const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/ospf/network/${action}preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview แก้ OSPF network */
export async function previewOspfNetworkUpdate(id: string, payload: OspfNetworkUpdate): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/ospf/network/update/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview ลบ OSPF process */
export async function previewOspfProcessRemove(id: string, payload: OspfProcessConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/ospf/process/remove/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply OSPF preview */
export async function applyOspf(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/ospf/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** อ่าน EIGRP actual state จาก running-config */
export async function getEigrpState(id: string): Promise<EigrpStateResponse> {
  try { const { data } = await api.get<EigrpStateResponse>(`/nodes/${id}/routing/eigrp`); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview เพิ่ม/ลบ EIGRP network */
export async function previewEigrpNetwork(id: string, payload: EigrpNetworkConfig, remove = false): Promise<PreviewResponse> {
  try { const action = remove ? 'remove/' : ''; const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/eigrp/network/${action}preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview แก้ EIGRP network */
export async function previewEigrpNetworkUpdate(id: string, payload: EigrpNetworkUpdate): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/eigrp/network/update/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview ลบ EIGRP process */
export async function previewEigrpProcessRemove(id: string, payload: EigrpProcessConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/eigrp/process/remove/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply EIGRP preview */
export async function applyEigrp(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/eigrp/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** อ่าน BGP actual state จาก running-config */
export async function getBgpState(id: string): Promise<BgpStateResponse> {
  try { const { data } = await api.get<BgpStateResponse>(`/nodes/${id}/routing/bgp`); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview เพิ่ม/ลบ BGP neighbor */
export async function previewBgpNeighbor(id: string, payload: BgpNeighborConfig, remove = false): Promise<PreviewResponse> {
  try { const action = remove ? 'remove/' : ''; const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/bgp/neighbor/${action}preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview แก้ BGP neighbor */
export async function previewBgpNeighborUpdate(id: string, payload: BgpNeighborUpdate): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/bgp/neighbor/update/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview เพิ่ม/ลบ BGP advertised network */
export async function previewBgpNetwork(id: string, payload: BgpNetworkConfig, remove = false): Promise<PreviewResponse> {
  try { const action = remove ? 'remove/' : ''; const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/bgp/network/${action}preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview แก้ BGP advertised network */
export async function previewBgpNetworkUpdate(id: string, payload: BgpNetworkUpdate): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/bgp/network/update/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview ลบ BGP process ทั้งหมด */
export async function previewBgpProcessRemove(id: string, payload: BgpProcessConfig): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/bgp/process/remove/preview`, payload); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply BGP preview */
export async function applyBgp(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/bgp/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** สร้าง preview บันทึก startup-config หลังผู้ใช้ยืนยัน */
export async function previewSaveConfig(id: string): Promise<PreviewResponse> {
  try { const { data } = await api.post<PreviewResponse>(`/nodes/${id}/config/save/preview`, { confirm: true }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** Apply คำสั่งบันทึก startup-config */
export async function applySaveConfig(id: string, operationId: string, payloadHash: string): Promise<ApplyResponse> {
  try { const { data } = await api.post<ApplyResponse>(`/nodes/${id}/config/save/apply`, { operation_id: operationId, payload_hash: payloadHash }); return data } catch (error) { throw extractApiError(error as AxiosError) }
}

/** เรียก Show command จาก allowlist */
export async function showCommand(id: string, command: string): Promise<ShowResponse> {
  try {
    const { data } = await api.get<ShowResponse>(`/nodes/${id}/show`, { params: { command } })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** อ่านค่าปัจจุบันของ interface สำหรับ prefill ฟอร์ม */
export async function getInterfaceCurrent(id: string, interfaceName: string): Promise<InterfaceCurrentResponse> {
  try {
    const encodedName = encodeURIComponent(interfaceName)
    const { data } = await api.get<InterfaceCurrentResponse>(`/nodes/${id}/interfaces/${encodedName}`)
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}

/** ดึง command history แบบ filter ได้ */
export async function listHistory(nodeId?: string, overallStatus?: string): Promise<HistoryEntry[]> {
  try {
    const { data } = await api.get<HistoryEntry[]>('/history', {
      params: { node_id: nodeId || undefined, overall_status: overallStatus || undefined },
    })
    return data
  } catch (error) {
    throw extractApiError(error as AxiosError)
  }
}
