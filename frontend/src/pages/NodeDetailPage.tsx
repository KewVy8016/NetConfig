import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, ChevronLeft, Copy, Eye, Loader2, RefreshCw, Save, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router-dom'
import { z } from 'zod'
import { Topbar } from '../components/shared/Topbar'
import { StatusBadge } from '../components/shared/StatusBadge'
import {
  applyInterface,
  applyInterfaceAdmin,
  applyAccessPort,
  applyRoutedPort,
  applyVlanSvi,
  applyLoopback,
  applyEigrp,
  applyBgp,
  applySaveConfig,
  applyOspf,
  applyRip,
  applyStaticRoute,
  getInterfaceCurrent,
  getInterfaceCapabilities,
  getDeviceCapabilities,
  getEigrpState,
  getBgpState,
  getNode,
  getOspfState,
  getRipState,
  listStaticRoutes,
  listVlans,
  previewInterface,
  previewInterfaceAdmin,
  previewAccessPort,
  previewRoutedPort,
  previewRoutedPortRestore,
  previewSvi,
  previewSviRemove,
  previewVlan,
  previewVlanRemove,
  previewLoopback,
  previewLoopbackRemove,
  previewEigrpNetwork,
  previewEigrpNetworkUpdate,
  previewEigrpProcessRemove,
  previewBgpNeighbor,
  previewBgpNeighborUpdate,
  previewBgpNetwork,
  previewBgpNetworkUpdate,
  previewBgpProcessRemove,
  previewSaveConfig,
  previewOspfNetwork,
  previewOspfNetworkUpdate,
  previewOspfProcessRemove,
  previewRipNetwork,
  previewRipNetworkUpdate,
  previewRipProcessRemove,
  previewStaticRoute,
  previewStaticRouteUpdate,
  showCommand,
  testNodeConnection,
  type ApplyResponse,
  type AccessPortConfig,
  type EigrpNetworkConfig,
  type EigrpStateResponse,
  type BgpNeighborConfig,
  type BgpNetworkConfig,
  type BgpStateResponse,
  type DeviceCapabilitiesResponse,
  type InterfaceConfig,
  type InterfaceAdminConfig,
  type InterfaceCapabilitiesResponse,
  type LoopbackConfig,
  type PreviewResponse,
  type OspfNetworkConfig,
  type OspfStateResponse,
  type RipNetworkConfig,
  type RipStateResponse,
  type ShowResponse,
  type StaticRouteConfig,
  type StaticRouteEntry,
  type VlanEntry,
  type VlanConfig,
  type SviConfig,
  type RoutedPortConfig,
} from '../lib/api'

const interfaceSchema = z.object({
  interface_name: z.string().min(1, 'ระบุชื่อ interface').max(64).regex(/^[A-Za-z][A-Za-z0-9/_.-]*$/, 'ชื่อ interface ไม่ถูกต้อง'),
  ip_address: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 address ที่ถูกต้อง'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal subnet mask'),
  description: z.string().max(240, 'คำอธิบายยาวเกินไป').optional(),
  admin_up: z.boolean(),
})

type InterfaceForm = z.infer<typeof interfaceSchema>

const loopbackSchema = z.object({
  loopback_id: z.number().int('Loopback number ต้องเป็นจำนวนเต็ม').min(0, 'Loopback number ต้องไม่ติดลบ').max(2147483647),
  ip_address: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 address ที่ถูกต้อง'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal subnet mask'),
  description: z.string().max(240, 'คำอธิบายยาวเกินไป').optional(),
  admin_up: z.boolean(),
})
type LoopbackForm = z.infer<typeof loopbackSchema>
type LoopbackPreviewIntent = { mode: 'create'; payload: LoopbackConfig } | { mode: 'remove'; loopback_id: number }

const accessPortSchema = z.object({
  interface_name: z.string().min(1, 'เลือก physical interface'),
  vlan_id: z.number().int().min(1).max(4094),
  description: z.string().max(240, 'คำอธิบายยาวเกินไป').optional(),
  admin_up: z.boolean(),
})
type AccessPortForm = z.infer<typeof accessPortSchema>

const vlanSchema = z.object({
  vlan_id: z.number().int().min(2, 'VLAN 1 เป็น default และสร้างใหม่ไม่ได้').max(4094),
  name: z.string().max(32).regex(/^[A-Za-z0-9_.-]*$/, 'ชื่อ VLAN ใช้ได้เฉพาะตัวอักษร ตัวเลข จุด ขีด และขีดล่าง').optional(),
})
type VlanForm = z.infer<typeof vlanSchema>
const sviSchema = z.object({
  vlan_id: z.number().int().min(1).max(4094),
  ip_address: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 address ที่ถูกต้อง'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal subnet mask'),
  description: z.string().max(240, 'คำอธิบายยาวเกินไป').optional(),
  admin_up: z.boolean(),
})
type SviForm = z.infer<typeof sviSchema>
type VlanSviPreviewIntent = { mode: 'vlan_create'; payload: VlanConfig } | { mode: 'vlan_remove' | 'svi_remove'; vlan_id: number } | { mode: 'svi_create'; payload: SviConfig }

const routedPortSchema = z.object({
  interface_name: z.string().min(1, 'เลือก physical interface'),
  ip_address: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 address ที่ถูกต้อง'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal subnet mask'),
  description: z.string().max(240, 'คำอธิบายยาวเกินไป').optional(),
  admin_up: z.boolean(),
})
type RoutedPortForm = z.infer<typeof routedPortSchema>
type RoutedPortPreviewIntent = { mode: 'create'; payload: RoutedPortConfig } | { mode: 'restore'; interface_name: string }

const staticRouteSchema = z.object({
  destination: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 network ที่ถูกต้อง'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal subnet mask'),
  target_type: z.enum(['next_hop', 'exit_interface']),
  target: z.string().min(1, 'ระบุ Next Hop หรือ Exit Interface').max(64),
}).superRefine((data, context) => {
  const valid = data.target_type === 'next_hop'
    ? /^(?:\d{1,3}\.){3}\d{1,3}$/.test(data.target)
    : /^[A-Za-z][A-Za-z0-9/_.-]*$/.test(data.target)
  if (!valid) context.addIssue({ code: 'custom', path: ['target'], message: data.target_type === 'next_hop' ? 'ระบุ IPv4 next-hop ที่ถูกต้อง' : 'ชื่อ Exit Interface ไม่ถูกต้อง' })
})

type StaticRouteForm = z.infer<typeof staticRouteSchema>
type StaticPreviewIntent =
  | { mode: 'add' | 'remove'; payload: StaticRouteConfig }
  | { mode: 'update'; current: StaticRouteConfig; desired: StaticRouteConfig }

const ripNetworkSchema = z.object({
  version: z.union([z.literal(1), z.literal(2)]),
  network: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 major network เช่น 10.0.0.0'),
})

type RipNetworkForm = z.infer<typeof ripNetworkSchema>
type RipPreviewIntent =
  | { mode: 'add' | 'remove'; payload: RipNetworkConfig }
  | { mode: 'update'; current: RipNetworkConfig; desired: RipNetworkConfig }
  | { mode: 'remove_process'; state: RipStateResponse }

const ospfNetworkSchema = z.object({
  process_id: z.number().int().min(1, 'Process ID ต้องมากกว่า 0').max(65535),
  router_id: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ Router ID IPv4'),
  network: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 network'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal netmask'),
  area: z.number().int().min(0, 'Area ต้องไม่น้อยกว่า 0').max(4294967295),
})
type OspfNetworkForm = z.infer<typeof ospfNetworkSchema>
type OspfPreviewIntent =
  | { mode: 'add' | 'remove'; payload: OspfNetworkConfig }
  | { mode: 'update'; current: OspfNetworkConfig; desired: OspfNetworkConfig }
  | { mode: 'remove_process'; state: OspfStateResponse }

const eigrpNetworkSchema = z.object({
  as_number: z.number().int().min(1, 'AS ต้องมากกว่า 0').max(65535),
  router_id: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ Router ID IPv4'),
  network: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 network'),
  subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal netmask'),
})
type EigrpNetworkForm = z.infer<typeof eigrpNetworkSchema>
type EigrpPreviewIntent =
  | { mode: 'add' | 'remove'; payload: EigrpNetworkConfig }
  | { mode: 'update'; current: EigrpNetworkConfig; desired: EigrpNetworkConfig }
  | { mode: 'remove_process'; state: EigrpStateResponse }

const bgpNeighborSchema = z.object({ local_as: z.number().int().min(1).max(4294967295), router_id: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ Router ID IPv4'), neighbor_ip: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ Neighbor IPv4'), remote_as: z.number().int().min(1).max(4294967295), description: z.string().max(240).optional() })
const bgpNetworkSchema = z.object({ local_as: z.number().int().min(1).max(4294967295), network: z.string().regex(/^(?:\d{1,3}\.){3}\d{1,3}$/, 'ระบุ IPv4 network'), subnet_mask: z.string().regex(/^\d{1,3}(\.\d{1,3}){3}$/, 'ใช้ dotted decimal netmask') })
type BgpNeighborForm = z.infer<typeof bgpNeighborSchema>
type BgpNetworkForm = z.infer<typeof bgpNetworkSchema>
type BgpPreviewIntent = { mode: 'neighbor_add' | 'neighbor_remove'; payload: BgpNeighborConfig } | { mode: 'neighbor_update'; current: BgpNeighborConfig; desired: BgpNeighborConfig } | { mode: 'network_add' | 'network_remove'; payload: BgpNetworkConfig } | { mode: 'network_update'; current: BgpNetworkConfig; desired: BgpNetworkConfig } | { mode: 'remove_process'; state: BgpStateResponse }

const SHOW_COMMANDS = [
  'show ip interface brief',
  'show ip route',
  'show ip protocols',
  'show ip ospf neighbor',
  'show ip eigrp neighbors',
  'show ip bgp summary',
  'show running-config',
]

function getApiMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'message_th' in error) {
    return String(error.message_th)
  }
  return 'เกิดข้อผิดพลาด กรุณาลองใหม่'
}

/**
 * NodeDetailPage
 * หน้ารายละเอียด node ตาม Design: interface, routing, show และ CLI placeholder
 * การแก้ config ต้องผ่าน preview drawer ก่อน Apply ทุกครั้ง
 */
export function NodeDetailPage({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (value: boolean) => void }) {
  const { id } = useParams<{ id: string }>()
  const nodeId = id ?? ''
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'interfaces' | 'routing' | 'show' | 'cli'>('interfaces')
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [applyResult, setApplyResult] = useState<ApplyResponse | null>(null)
  const [showResult, setShowResult] = useState<ShowResponse | null>(null)
  const [selectedShow, setSelectedShow] = useState(SHOW_COMMANDS[0])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const drawerCloseTimer = useRef<number | null>(null)

  const closePreviewDrawer = () => {
    if (drawerCloseTimer.current !== null) {
      window.clearTimeout(drawerCloseTimer.current)
      drawerCloseTimer.current = null
    }
    setDrawerOpen(false)
    setPreview(null)
    setApplyResult(null)
  }

  useEffect(() => () => {
    if (drawerCloseTimer.current !== null) window.clearTimeout(drawerCloseTimer.current)
  }, [])

  // Preview drawer ต้องปิดด้วย Escape ตาม interaction ใน Design โดยไม่ Apply อะไรเพิ่ม
  useEffect(() => {
    if (!drawerOpen) return undefined
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [drawerOpen])

  const nodeQuery = useQuery({
    queryKey: ['node', nodeId],
    queryFn: () => getNode(nodeId),
    enabled: Boolean(nodeId),
  })

  // สถานะใน DB เป็นผลตรวจครั้งล่าสุด จึงต้อง heartbeat จากหน้า Detail
  // เพื่อไม่ให้ Connected ค้างเมื่ออุปกรณ์หลุดหลังจากบันทึก Node
  const healthQuery = useQuery({
    queryKey: ['node-health', nodeId],
    queryFn: () => testNodeConnection(nodeId),
    enabled: Boolean(nodeId),
    retry: false,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  const interfaceQuery = useQuery({
    queryKey: ['show', nodeId, 'show ip interface brief'],
    queryFn: () => showCommand(nodeId, 'show ip interface brief'),
    enabled: Boolean(nodeId) && activeTab === 'interfaces',
    retry: false,
  })

  const isSwitchDevice = nodeQuery.data?.device_kind === 'switch'

  // Switch ใช้การตั้งค่า L2/L3 port จากหน้า Interfaces และไม่แสดง routing protocol forms
  useEffect(() => {
    if (isSwitchDevice && activeTab === 'routing') {
      setActiveTab('interfaces')
    }
  }, [activeTab, isSwitchDevice])

  const capabilityQuery = useQuery({
    queryKey: ['capabilities', nodeId],
    queryFn: () => getDeviceCapabilities(nodeId),
    enabled: Boolean(nodeId) && isSwitchDevice && activeTab === 'interfaces',
    retry: false,
  })

  const vlanQuery = useQuery({
    queryKey: ['vlans', nodeId],
    queryFn: () => listVlans(nodeId),
    enabled: Boolean(nodeId) && isSwitchDevice && activeTab === 'interfaces' && capabilityQuery.data?.vlan_supported === true,
    retry: false,
  })

  const previewMutation = useMutation({
    mutationFn: (payload: InterfaceConfig) => previewInterface(nodeId, payload),
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const interfaceAdminPreviewMutation = useMutation({
    mutationFn: (payload: InterfaceAdminConfig) => previewInterfaceAdmin(nodeId, payload),
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const loopbackPreviewMutation = useMutation({
    mutationFn: (intent: LoopbackPreviewIntent) => intent.mode === 'create'
      ? previewLoopback(nodeId, intent.payload)
      : previewLoopbackRemove(nodeId, { loopback_id: intent.loopback_id }),
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const accessPortPreviewMutation = useMutation({
    mutationFn: (payload: AccessPortConfig) => previewAccessPort(nodeId, payload),
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const vlanSviPreviewMutation = useMutation({
    mutationFn: (intent: VlanSviPreviewIntent) => {
      if (intent.mode === 'vlan_create') return previewVlan(nodeId, intent.payload)
      if (intent.mode === 'vlan_remove') return previewVlanRemove(nodeId, { vlan_id: intent.vlan_id })
      if (intent.mode === 'svi_create') return previewSvi(nodeId, intent.payload)
      return previewSviRemove(nodeId, { vlan_id: intent.vlan_id })
    },
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const routedPortPreviewMutation = useMutation({
    mutationFn: (intent: RoutedPortPreviewIntent) => intent.mode === 'create'
      ? previewRoutedPort(nodeId, intent.payload)
      : previewRoutedPortRestore(nodeId, { interface_name: intent.interface_name }),
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const staticPreviewMutation = useMutation({
    mutationFn: (intent: StaticPreviewIntent) => {
      if (intent.mode === 'update') {
        return previewStaticRouteUpdate(nodeId, { current: intent.current, desired: intent.desired })
      }
      return previewStaticRoute(nodeId, intent.payload, intent.mode === 'remove')
    },
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const ripPreviewMutation = useMutation({
    mutationFn: (intent: RipPreviewIntent) => {
      if (intent.mode === 'update') {
        return previewRipNetworkUpdate(nodeId, { current: intent.current, desired: intent.desired })
      }
      if (intent.mode === 'remove_process') {
        if (!intent.state.version) throw new Error('ไม่พบ RIP version ปัจจุบัน')
        return previewRipProcessRemove(nodeId, {
          version: intent.state.version,
          networks: intent.state.networks,
          no_auto_summary: intent.state.no_auto_summary,
        })
      }
      return previewRipNetwork(nodeId, intent.payload, intent.mode === 'remove')
    },
    onSuccess: (data) => {
      setPreview(data)
      setApplyResult(null)
      setDrawerOpen(true)
    },
  })

  const ospfPreviewMutation = useMutation({
    mutationFn: (intent: OspfPreviewIntent) => {
      if (intent.mode === 'update') return previewOspfNetworkUpdate(nodeId, { current: intent.current, desired: intent.desired })
      if (intent.mode === 'remove_process') {
        if (!intent.state.process_id) throw new Error('ไม่พบ OSPF process ปัจจุบัน')
        return previewOspfProcessRemove(nodeId, { process_id: intent.state.process_id, router_id: intent.state.router_id, networks: intent.state.networks })
      }
      return previewOspfNetwork(nodeId, intent.payload, intent.mode === 'remove')
    },
    onSuccess: (data) => { setPreview(data); setApplyResult(null); setDrawerOpen(true) },
  })

  const eigrpPreviewMutation = useMutation({
    mutationFn: (intent: EigrpPreviewIntent) => {
      if (intent.mode === 'update') return previewEigrpNetworkUpdate(nodeId, { current: intent.current, desired: intent.desired })
      if (intent.mode === 'remove_process') {
        if (!intent.state.as_number) throw new Error('ไม่พบ EIGRP AS ปัจจุบัน')
        return previewEigrpProcessRemove(nodeId, { as_number: intent.state.as_number, router_id: intent.state.router_id, networks: intent.state.networks, no_auto_summary: intent.state.no_auto_summary })
      }
      return previewEigrpNetwork(nodeId, intent.payload, intent.mode === 'remove')
    },
    onSuccess: (data) => { setPreview(data); setApplyResult(null); setDrawerOpen(true) },
  })

  const bgpPreviewMutation = useMutation({
    mutationFn: (intent: BgpPreviewIntent) => {
      if (intent.mode === 'remove_process') {
        if (!intent.state.local_as) throw new Error('ไม่พบ BGP local AS ปัจจุบัน')
        return previewBgpProcessRemove(nodeId, { local_as: intent.state.local_as, router_id: intent.state.router_id, neighbors: intent.state.neighbors, networks: intent.state.networks })
      }
      if (intent.mode === 'neighbor_update') return previewBgpNeighborUpdate(nodeId, { current: intent.current, desired: intent.desired })
      if (intent.mode === 'neighbor_add' || intent.mode === 'neighbor_remove') return previewBgpNeighbor(nodeId, intent.payload as BgpNeighborConfig, intent.mode === 'neighbor_remove')
      if (intent.mode === 'network_update') return previewBgpNetworkUpdate(nodeId, { current: intent.current, desired: intent.desired })
      return previewBgpNetwork(nodeId, intent.payload as BgpNetworkConfig, intent.mode === 'network_remove')
    },
    onSuccess: (data) => { setPreview(data); setApplyResult(null); setDrawerOpen(true) },
  })

  const savePreviewMutation = useMutation({
    mutationFn: () => previewSaveConfig(nodeId),
    onSuccess: (data) => { setPreview(data); setApplyResult(null); setDrawerOpen(true) },
  })

  const applyMutation = useMutation({
    mutationFn: () => {
      if (!preview) throw new Error('ไม่พบ preview')
      if (preview.operation_type === 'save_config') return applySaveConfig(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type === 'interface_admin') return applyInterfaceAdmin(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('bgp_')) return applyBgp(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('eigrp_')) return applyEigrp(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('ospf_')) return applyOspf(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('rip_')) {
        return applyRip(nodeId, preview.operation_id, preview.payload_hash)
      }
      if (preview.operation_type.startsWith('static_route')) {
        return applyStaticRoute(nodeId, preview.operation_id, preview.payload_hash)
      }
      if (preview.operation_type.startsWith('loopback')) return applyLoopback(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type === 'access_port') return applyAccessPort(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('routed_port')) return applyRoutedPort(nodeId, preview.operation_id, preview.payload_hash)
      if (preview.operation_type.startsWith('vlan') || preview.operation_type.startsWith('svi')) return applyVlanSvi(nodeId, preview.operation_id, preview.payload_hash)
      return applyInterface(nodeId, preview.operation_id, preview.payload_hash)
    },
    onSuccess: (data) => {
      setApplyResult(data)
      queryClient.invalidateQueries({ queryKey: ['history'] })
      queryClient.invalidateQueries({ queryKey: ['show', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['show', nodeId, 'show ip interface brief'] })
      queryClient.invalidateQueries({ queryKey: ['static-routes', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['rip-state', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['ospf-state', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['eigrp-state', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['bgp-state', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['vlans', nodeId] })
      if (data.overall_status === 'success') {
        drawerCloseTimer.current = window.setTimeout(() => {
          drawerCloseTimer.current = null
          setDrawerOpen(false)
          setPreview(null)
          setApplyResult(null)
        }, 1200)
      }
    },
  })

  const showMutation = useMutation({
    mutationFn: (command: string) => showCommand(nodeId, command),
    onSuccess: (data) => setShowResult(data),
  })

  const connectionMutation = useMutation({
    mutationFn: () => testNodeConnection(nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['node', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['nodes'] })
      queryClient.invalidateQueries({ queryKey: ['show', nodeId] })
      queryClient.invalidateQueries({ queryKey: ['node-health', nodeId] })
    },
  })

  const form = useForm<InterfaceForm>({
    resolver: zodResolver(interfaceSchema),
    defaultValues: { interface_name: '', ip_address: '', subnet_mask: '255.255.255.0', description: '', admin_up: true },
  })

  const interfaceDetailMutation = useMutation({
    mutationFn: (interfaceName: string) => getInterfaceCurrent(nodeId, interfaceName),
    onSuccess: (data) => {
      if (form.getValues('interface_name') !== data.interface_name) return
      form.setValue('ip_address', data.ip_address ?? '', { shouldValidate: false })
      form.setValue('subnet_mask', data.subnet_mask ?? '', { shouldValidate: false })
      form.setValue('description', data.description ?? '', { shouldValidate: false })
      form.setValue('admin_up', data.admin_up, { shouldValidate: false })
      form.clearErrors()
    },
  })

  const interfaceCapabilityMutation = useMutation({
    mutationFn: (interfaceName: string) => getInterfaceCapabilities(nodeId, interfaceName),
  })

  const handlePreview = (data: InterfaceForm) => previewMutation.mutate(data)
  const handleInterfaceAdminPreview = (payload: InterfaceAdminConfig) => interfaceAdminPreviewMutation.mutate(payload)
  const handleInterfaceSelect = (interfaceName: string) => {
    form.setValue('interface_name', interfaceName, { shouldValidate: true })
    interfaceDetailMutation.reset()
    interfaceCapabilityMutation.reset()
    if (interfaceName) interfaceDetailMutation.mutate(interfaceName)
    if (interfaceName && isSwitchDevice) interfaceCapabilityMutation.mutate(interfaceName)
  }
  const handleShow = (command: string) => {
    setSelectedShow(command)
    showMutation.mutate(command)
  }
  const handleApply = () => {
    if (preview?.commands.some((command) => command.trim() === 'shutdown') && !window.confirm('ยืนยันปิดใช้งาน interface นี้หรือไม่?')) {
      return
    }
    if (preview?.operation_type === 'static_route_remove' && !window.confirm('ยืนยันลบ Static/Default route นี้หรือไม่?')) {
      return
    }
    if (preview?.operation_type === 'static_route_update' && !window.confirm('ยืนยันแก้ไข route โดยลบค่าเดิมแล้วเพิ่มค่าใหม่หรือไม่?')) {
      return
    }
    if (preview?.operation_type === 'loopback_remove' && !window.confirm('ยืนยันลบ Loopback นี้หรือไม่? การลบมีผลกับ running-config ทันที')) return
    if (preview?.operation_type === 'access_port' && !window.confirm('ยืนยันเปลี่ยนพอร์ตเป็น L2 access port ตามคำสั่ง preview หรือไม่?')) return
    if (preview?.operation_type === 'routed_port' && !window.confirm('ยืนยันเปลี่ยน L2 switchport เป็น L3 routed port หรือไม่? VLAN/trunk เดิมอาจไม่ใช้งานต่อ')) return
    if (preview?.operation_type === 'routed_port_restore' && !window.confirm('ยืนยันลบ IPv4 และคืนเป็น L2 switchport พื้นฐานหรือไม่? ระบบจะไม่คืน VLAN/trunk/description/admin state เดิม')) return
    if (preview?.operation_type === 'svi_remove' && !window.confirm('ยืนยันลบ SVI นี้หรือไม่? VLAN resource จะยังคงอยู่')) return
    if (preview?.operation_type === 'vlan_remove' && !window.confirm('ยืนยันลบ VLAN นี้หรือไม่? ต้องไม่มี SVI อ้างอยู่')) return
    if (preview?.operation_type === 'rip_process_remove' && !window.confirm('ยืนยันลบ RIP protocol และ advertised networks ทั้งหมดหรือไม่?')) {
      return
    }
    if (preview?.operation_type === 'ospf_process_remove' && !window.confirm('ยืนยันลบ OSPF process และ network ทั้งหมดหรือไม่?')) return
    if (preview?.operation_type === 'eigrp_process_remove' && !window.confirm('ยืนยันลบ EIGRP process และ network ทั้งหมดหรือไม่?')) return
    if (preview?.operation_type === 'bgp_process_remove' && !window.confirm('ยืนยันลบ BGP process, neighbor และ network ทั้งหมดหรือไม่?')) return
    if (preview?.operation_type === 'save_config' && !window.confirm('ยืนยันบันทึก running-config ปัจจุบันลง startup-config หรือไม่?')) return
    applyMutation.mutate()
  }
  const copyOutput = async () => {
    if (!showResult) return
    await navigator.clipboard.writeText(showResult.output)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  if (nodeQuery.isLoading) {
    return <PageShell><LoadingState /></PageShell>
  }
  if (nodeQuery.isError || !nodeQuery.data) {
    return <PageShell><ErrorState message={getApiMessage(nodeQuery.error)} /></PageShell>
  }

  const node = nodeQuery.data
  // NODE_BUSY/Backend error จาก heartbeat ไม่ได้แปลว่าอุปกรณ์หลุด
  // จึงยึด DB status ล่าสุดที่ Reconnect เพิ่งเขียนไว้แทน Unknown
  const liveStatus = healthQuery.isError
    ? node.status
    : healthQuery.isFetching && !healthQuery.data
      ? 'checking'
      : healthQuery.data?.overall_status === 'success'
        ? 'connected'
        : healthQuery.data?.overall_status === 'failed'
          ? 'unreachable'
          : node.status
  return (
    <PageShell>
      <Topbar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        title={node.hostname}
        breadcrumbs={<Link to="/" className="text-gray-500 hover:text-accent-DEFAULT">Nodes</Link>}
      />

      <main className="p-6 max-w-7xl mx-auto w-full space-y-5">
        {/* --- Header node และ action ที่ปลอดภัย --- */}
        <section className="card flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="btn-icon hover:bg-gray-100" aria-label="กลับไปหน้า Nodes"><ChevronLeft className="w-5 h-5" /></Link>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{node.hostname}</h2>
              <p className="text-sm text-gray-500 font-mono">{node.host ?? node.serial_port} · {node.transport.toUpperCase()}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={connectionMutation.isPending ? 'checking' : liveStatus} />
            <button
              type="button"
              className="btn-secondary btn-sm flex items-center gap-2"
              onClick={() => connectionMutation.mutate()}
              disabled={connectionMutation.isPending}
            >
              {connectionMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {connectionMutation.isPending ? 'Testing...' : 'Reconnect'}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={() => savePreviewMutation.mutate()} disabled={savePreviewMutation.isPending} title="สร้าง preview ก่อนบันทึก startup-config">{savePreviewMutation.isPending ? 'กำลังสร้าง Preview...' : 'Save Config'}</button>
          </div>
        </section>

        {connectionMutation.data && (
          <div className={`rounded-lg border p-3 text-sm flex items-center gap-2 ${connectionMutation.data.overall_status === 'success' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`} role="status">
            {connectionMutation.data.overall_status === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {connectionMutation.data.overall_status === 'success' ? `เชื่อมต่อสำเร็จ${connectionMutation.data.hostname_detected ? ` — ${connectionMutation.data.hostname_detected}` : ''}` : 'เชื่อมต่อไม่สำเร็จ สถานะถูกอัปเดตเป็น Unreachable'}
          </div>
        )}
        {connectionMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 flex items-center gap-2" role="alert">
            <AlertCircle className="w-4 h-4" />{getApiMessage(connectionMutation.error)}
          </div>
        )}

        {/* --- Tabs ตาม Node Detail ใน Design --- */}
        <nav className="flex gap-1 border-b border-gray-200" aria-label="Node detail tabs">
          {(isSwitchDevice
            ? (['interfaces', 'show', 'cli'] as const)
            : (['interfaces', 'routing', 'show', 'cli'] as const)
          ).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 ${activeTab === tab ? 'border-accent-DEFAULT text-accent-DEFAULT' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
            >
              {tab === 'interfaces' ? 'Interfaces' : tab === 'routing' ? 'Routing' : tab === 'show' ? 'Show' : 'CLI'}
            </button>
          ))}
        </nav>

        {activeTab === 'interfaces' && (
          <InterfacesPanel
            form={form}
            onPreview={handlePreview}
            isPreviewing={previewMutation.isPending}
            previewError={previewMutation.error}
            result={interfaceQuery.data ?? null}
            isLoading={interfaceQuery.isLoading || interfaceQuery.isFetching}
            loadError={interfaceQuery.error}
            onRefresh={() => interfaceQuery.refetch()}
            onInterfaceSelect={handleInterfaceSelect}
            onAdminStatePreview={handleInterfaceAdminPreview}
            isAdminStatePreviewing={interfaceAdminPreviewMutation.isPending}
            adminStatePreviewError={interfaceAdminPreviewMutation.error}
            isDetailLoading={interfaceDetailMutation.isPending}
            detailError={interfaceDetailMutation.error}
            interfaceCapabilities={interfaceCapabilityMutation.data ?? null}
            isInterfaceCapabilityLoading={interfaceCapabilityMutation.isPending}
            interfaceCapabilityError={interfaceCapabilityMutation.error}
            capabilities={capabilityQuery.data ?? null}
            isCapabilityLoading={capabilityQuery.isLoading || capabilityQuery.isFetching}
            capabilityError={capabilityQuery.error}
            isSwitchDevice={isSwitchDevice}
            vlans={vlanQuery.data?.vlans ?? []}
            isVlanLoading={vlanQuery.isLoading || vlanQuery.isFetching}
            vlanError={vlanQuery.error}
            onVlanRefresh={() => vlanQuery.refetch()}
            onAccessPortPreview={(payload) => accessPortPreviewMutation.mutate(payload)}
            isAccessPortPreviewing={accessPortPreviewMutation.isPending}
            accessPortPreviewError={accessPortPreviewMutation.error}
            onVlanSviPreview={(intent) => vlanSviPreviewMutation.mutate(intent)}
            isVlanSviPreviewing={vlanSviPreviewMutation.isPending}
            vlanSviPreviewError={vlanSviPreviewMutation.error}
            onRoutedPortPreview={(intent) => routedPortPreviewMutation.mutate(intent)}
            isRoutedPortPreviewing={routedPortPreviewMutation.isPending}
            routedPortPreviewError={routedPortPreviewMutation.error}
            onLoopbackPreview={(intent) => loopbackPreviewMutation.mutate(intent)}
            isLoopbackPreviewing={loopbackPreviewMutation.isPending}
            loopbackPreviewError={loopbackPreviewMutation.error}
          />
        )}
        {activeTab === 'routing' && (
          <RoutingPanel
            nodeId={nodeId}
            onStaticPreview={(intent) => staticPreviewMutation.mutate(intent)}
            onRipPreview={(intent) => ripPreviewMutation.mutate(intent)}
            onOspfPreview={(intent) => ospfPreviewMutation.mutate(intent)}
            onEigrpPreview={(intent) => eigrpPreviewMutation.mutate(intent)}
            onBgpPreview={(intent) => bgpPreviewMutation.mutate(intent)}
            isPreviewing={staticPreviewMutation.isPending || ripPreviewMutation.isPending || ospfPreviewMutation.isPending || eigrpPreviewMutation.isPending || bgpPreviewMutation.isPending}
            previewError={staticPreviewMutation.error ?? ripPreviewMutation.error ?? ospfPreviewMutation.error ?? eigrpPreviewMutation.error ?? bgpPreviewMutation.error}
          />
        )}
        {activeTab === 'show' && (
          <ShowPanel selectedCommand={selectedShow} result={showResult} isLoading={showMutation.isPending} error={showMutation.error} onRun={handleShow} onCopy={copyOutput} copied={copied} />
        )}
        {activeTab === 'cli' && <ComingSoon title="CLI Terminal" detail="Raw terminal เป็นฟีเจอร์เสริม Phase 4 และจะไม่ข้าม workflow validation" />}
      </main>

      {drawerOpen && preview && (
        <PreviewDrawer
          preview={preview}
          applyResult={applyResult}
          isApplying={applyMutation.isPending}
          error={applyMutation.error}
          onClose={closePreviewDrawer}
          onApply={handleApply}
        />
      )}
    </PageShell>
  )
}

function PageShell({ children }: { children: React.ReactNode }) {
  return <div className="flex-1 flex flex-col min-h-screen"><div className="flex-1">{children}</div></div>
}

function LoadingState() {
  return <div className="p-12 flex justify-center"><Loader2 className="w-7 h-7 animate-spin text-accent-DEFAULT" /></div>
}

function ErrorState({ message }: { message: string }) {
  return <div className="p-8"><div className="card border-red-200 bg-red-50 text-red-800 flex items-center gap-3"><AlertCircle className="w-5 h-5" />{message}</div></div>
}

function InterfacesPanel({ form, onPreview, isPreviewing, previewError, result, isLoading, loadError, onRefresh, onInterfaceSelect, onAdminStatePreview, isAdminStatePreviewing, adminStatePreviewError, isDetailLoading, detailError, interfaceCapabilities, isInterfaceCapabilityLoading, interfaceCapabilityError, capabilities, isCapabilityLoading, capabilityError, isSwitchDevice, vlans, isVlanLoading, vlanError, onVlanRefresh, onAccessPortPreview, isAccessPortPreviewing, accessPortPreviewError, onVlanSviPreview, isVlanSviPreviewing, vlanSviPreviewError, onRoutedPortPreview, isRoutedPortPreviewing, routedPortPreviewError, onLoopbackPreview, isLoopbackPreviewing, loopbackPreviewError }: { form: ReturnType<typeof useForm<InterfaceForm>>; onPreview: (data: InterfaceForm) => void; isPreviewing: boolean; previewError: Error | null; result: ShowResponse | null; isLoading: boolean; loadError: Error | null; onRefresh: () => void; onInterfaceSelect: (interfaceName: string) => void; onAdminStatePreview: (payload: InterfaceAdminConfig) => void; isAdminStatePreviewing: boolean; adminStatePreviewError: Error | null; isDetailLoading: boolean; detailError: Error | null; interfaceCapabilities: InterfaceCapabilitiesResponse | null; isInterfaceCapabilityLoading: boolean; interfaceCapabilityError: Error | null; capabilities: DeviceCapabilitiesResponse | null; isCapabilityLoading: boolean; capabilityError: Error | null; isSwitchDevice: boolean; vlans: VlanEntry[]; isVlanLoading: boolean; vlanError: Error | null; onVlanRefresh: () => void; onAccessPortPreview: (payload: AccessPortConfig) => void; isAccessPortPreviewing: boolean; accessPortPreviewError: Error | null; onVlanSviPreview: (intent: VlanSviPreviewIntent) => void; isVlanSviPreviewing: boolean; vlanSviPreviewError: Error | null; onRoutedPortPreview: (intent: RoutedPortPreviewIntent) => void; isRoutedPortPreviewing: boolean; routedPortPreviewError: Error | null; onLoopbackPreview: (intent: LoopbackPreviewIntent) => void; isLoopbackPreviewing: boolean; loopbackPreviewError: Error | null }) {
  const interfaces = result?.parsed ?? []
  const interfaceNames = interfaces.map((row) => row.interface).filter(Boolean)
  const selectedInterface = form.watch('interface_name')
  const [configPopup, setConfigPopup] = useState<'loopback' | 'access' | 'routed' | 'vlan' | null>(null)

  // ป้องกันการ preview ชื่อ interface เก่าที่หายไปหลัง Refresh อุปกรณ์
  useEffect(() => {
    if (selectedInterface && !interfaceNames.includes(selectedInterface)) {
      onInterfaceSelect('')
    }
  }, [interfaceNames.join('|'), onInterfaceSelect, selectedInterface])

  // Popup ต้องปิดด้วย Escape โดยไม่สร้าง preview หรือส่งคำสั่งใด ๆ
  useEffect(() => {
    if (!configPopup) return undefined
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setConfigPopup(null)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [configPopup])

  const openPreviewFromPopup = <T,>(handler: (intent: T) => void) => (intent: T) => {
    setConfigPopup(null)
    handler(intent)
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-5">
      <section className="card">
        {isSwitchDevice && <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs">
          <div className="font-semibold text-gray-700 mb-1">Device capability</div>
          {isCapabilityLoading ? <span className="inline-flex items-center gap-1 text-gray-500"><Loader2 className="w-3 h-3 animate-spin" />กำลังตรวจ Switchport/VLAN...</span> : capabilityError ? <span className="text-amber-700">ตรวจ capability ไม่สำเร็จ: {getApiMessage(capabilityError)}</span> : capabilities && <span className="flex flex-wrap gap-x-4 gap-y-1"><span className={capabilities.switchport_supported ? 'text-green-700' : 'text-gray-500'}>Switchport: {capabilities.switchport_supported ? 'รองรับ' : 'ไม่รองรับ'}</span><span className={capabilities.vlan_supported ? 'text-green-700' : 'text-gray-500'}>VLAN: {capabilities.vlan_supported ? 'รองรับ' : 'ไม่รองรับ'}</span></span>}
        </div>}
        <div className="flex items-center justify-between mb-4"><div><h3 className="text-lg font-semibold">Interfaces</h3><p className="text-sm text-gray-500">อ่านสถานะจริงด้วย Show หลัง Apply</p></div><div className="flex items-center gap-2"><span className="badge badge-blue"><span className="badge-dot" />IPv4</span><button type="button" className="btn-secondary btn-sm" onClick={onRefresh} disabled={isLoading}>{isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Refresh'}</button></div></div>
        {loadError && <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด Interface ไม่สำเร็จ: {getApiMessage(loadError)}</div>}
        {adminStatePreviewError && <div role="alert" className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">เตรียมคำสั่งเปิด/ปิด Interface ไม่สำเร็จ: {getApiMessage(adminStatePreviewError)}</div>}
        <div className="table-wrap"><table className="ds-table"><thead><tr><th>Interface</th><th>IP Address</th><th>Status</th><th>Protocol</th><th className="text-right">Admin State</th></tr></thead><tbody>{interfaces.length ? interfaces.map((row, index) => {
          const adminUp = !/administratively\s+down/i.test(row.status ?? '')
          const nextAdminUp = !adminUp
          return <tr key={index}><td className="font-mono text-xs">{row.interface}</td><td className="font-mono text-xs">{row.ip}</td><td>{row.status}</td><td>{row.protocol}</td><td className="text-right"><button type="button" role="switch" aria-checked={adminUp} aria-label={`${adminUp ? 'ปิด' : 'เปิด'} ${row.interface}`} disabled={isAdminStatePreviewing || isLoading} onClick={() => onAdminStatePreview({ interface_name: row.interface, admin_up: nextAdminUp })} className="inline-flex items-center gap-2" title="สร้าง Preview เพื่อเปลี่ยนสถานะ Admin"><span className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${adminUp ? 'bg-green-600' : 'bg-gray-300'}`}><span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${adminUp ? 'translate-x-6' : 'translate-x-1'}`} /></span><span className="text-xs text-gray-600">{adminUp ? 'เปิด' : 'ปิด'}</span></button></td></tr>
        }) : <tr><td colSpan={5} className="text-center text-gray-500 py-10">{isLoading ? 'กำลังโหลด Interface จากอุปกรณ์...' : 'ไม่พบ Interface กรุณากด Refresh'}</td></tr>}</tbody></table></div>
      </section>
      <div className="space-y-5">
      <section className="card">
        <h3 className="text-lg font-semibold mb-1">Configure Interface</h3>
        <p className="text-sm text-gray-500 mb-5">ระบบจะ validate และแสดงคำสั่งก่อนส่งเสมอ</p>
        <form onSubmit={form.handleSubmit(onPreview)} className="space-y-4">
          <Field label="Interface" error={form.formState.errors.interface_name?.message}>
            <select value={selectedInterface} onChange={(event) => onInterfaceSelect(event.target.value)} className="select-field font-mono" disabled={isLoading || interfaceNames.length === 0}>
              <option value="">{isLoading ? 'กำลังโหลด Interface...' : interfaceNames.length ? 'เลือก Interface' : 'ไม่พบ Interface — กด Refresh'}</option>
              {interfaces.map((row) => (
                <option key={row.interface} value={row.interface}>{row.interface} — {row.ip} ({row.status}/{row.protocol})</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">รายการอ่านจากอุปกรณ์ด้วย show ip interface brief</p>
            {isSwitchDevice && isInterfaceCapabilityLoading && <p className="text-xs text-gray-500 mt-1">กำลังตรวจ switchport ของพอร์ต...</p>}
            {isSwitchDevice && interfaceCapabilityError && <p className="text-xs text-amber-700 mt-1">ตรวจ switchport ไม่สำเร็จ: {getApiMessage(interfaceCapabilityError)}</p>}
            {isSwitchDevice && interfaceCapabilities && <p className="text-xs text-gray-600 mt-1">Switchport ปัจจุบัน: <strong>{interfaceCapabilities.switchport_state === 'enabled' ? 'Enabled (L2)' : interfaceCapabilities.switchport_state === 'disabled' ? 'Disabled (L3)' : interfaceCapabilities.switchport_state === 'unsupported' ? 'ไม่รองรับ' : 'ไม่ทราบ'}</strong></p>}
          </Field>
          {isDetailLoading && <div className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />กำลังโหลดค่าปัจจุบันของ Interface...</div>}
          {detailError && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลดค่าปัจจุบันไม่สำเร็จ: {getApiMessage(detailError)}</div>}
          <div className="grid grid-cols-2 gap-3"><Field label="IP Address" error={form.formState.errors.ip_address?.message}><input {...form.register('ip_address')} className="input-field font-mono" placeholder="192.168.1.1" /></Field><Field label="Subnet Mask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" placeholder="255.255.255.0" /></Field></div>
          <Field label="Description" error={form.formState.errors.description?.message}><input {...form.register('description')} className="input-field" placeholder="Uplink to R2" /></Field>
          <label className="flex items-center gap-3 text-sm"><input type="checkbox" {...form.register('admin_up')} className="w-4 h-4 accent-blue-600" /> no shutdown (administratively up)</label>
          {previewError && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
          <button type="submit" className="btn-primary w-full flex justify-center gap-2" disabled={isPreviewing || isDetailLoading || interfaceNames.length === 0}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Preview Commands</button>
        </form>
      </section>
      <section className="card">
        <h3 className="text-lg font-semibold mb-1">Additional Configuration</h3>
        <p className="text-sm text-gray-500 mb-4">เปิดฟอร์มเฉพาะงานโดยไม่ทำให้หน้าหลักยาวเกินไป</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ConfigPopupButton title="Loopback" detail="สร้างหรือลบ virtual interface" onClick={() => setConfigPopup('loopback')} />
          {isSwitchDevice && <ConfigPopupButton title="L2 Access Port" detail="กำหนด access VLAN ให้ switchport" onClick={() => setConfigPopup('access')} />}
          {isSwitchDevice && <ConfigPopupButton title="L3 Routed Port" detail="สลับพอร์ตเป็น no switchport" onClick={() => setConfigPopup('routed')} />}
          {isSwitchDevice && <ConfigPopupButton title="VLAN / SVI" detail="จัดการ VLAN และ interface VLAN" onClick={() => setConfigPopup('vlan')} />}
        </div>
      </section>
      </div>
      {configPopup === 'loopback' && <ConfigPopup title="Loopback Configuration" onClose={() => setConfigPopup(null)}>
        <LoopbackPanel interfaces={interfaces} onPreview={openPreviewFromPopup(onLoopbackPreview)} isPreviewing={isLoopbackPreviewing} previewError={loopbackPreviewError} />
      </ConfigPopup>}
      {configPopup === 'access' && <ConfigPopup title="L2 Access Port Configuration" onClose={() => setConfigPopup(null)}>
        <AccessPortPanel interfaces={interfaces} vlans={vlans} switchportSupported={capabilities?.switchport_supported === true} isVlanLoading={isVlanLoading} vlanError={vlanError} onRefreshVlans={onVlanRefresh} onPreview={openPreviewFromPopup(onAccessPortPreview)} isPreviewing={isAccessPortPreviewing} previewError={accessPortPreviewError} />
      </ConfigPopup>}
      {configPopup === 'routed' && <ConfigPopup title="L3 Routed Port Configuration" onClose={() => setConfigPopup(null)}>
        <RoutedPortPanel interfaces={interfaces} switchportSupported={capabilities?.switchport_supported === true} onPreview={openPreviewFromPopup(onRoutedPortPreview)} isPreviewing={isRoutedPortPreviewing} previewError={routedPortPreviewError} />
      </ConfigPopup>}
      {configPopup === 'vlan' && <ConfigPopup title="VLAN / SVI Configuration" onClose={() => setConfigPopup(null)}>
        <VlanSviPanel interfaces={interfaces} vlans={vlans} vlanSupported={capabilities?.vlan_supported === true} isVlanLoading={isVlanLoading} onRefreshVlans={onVlanRefresh} onPreview={openPreviewFromPopup(onVlanSviPreview)} isPreviewing={isVlanSviPreviewing} previewError={vlanSviPreviewError} />
      </ConfigPopup>}
    </div>
  )
}

/** ปุ่มเปิดฟอร์ม config เพิ่มเติมโดยไม่ส่งคำสั่งไปยังอุปกรณ์ */
function ConfigPopupButton({ title, detail, onClick }: { title: string; detail: string; onClick: () => void }) {
  return <button type="button" className="rounded-lg border border-gray-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500" onClick={onClick}><span className="block text-sm font-semibold text-gray-900">{title}</span><span className="mt-1 block text-xs text-gray-500">{detail}</span></button>
}

/** Dialog กลางสำหรับฟอร์ม config เพิ่มเติม ปิดได้ด้วยปุ่ม ฉากหลัง และ Escape */
function ConfigPopup({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-950/40 p-4" role="presentation" onMouseDown={onClose}>
      <section className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="config-popup-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-5 py-4">
          <h2 id="config-popup-title" className="text-lg font-semibold">{title}</h2>
          <button type="button" className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500" onClick={onClose} aria-label="ปิดหน้าต่าง" autoFocus><X className="h-5 w-5" /></button>
        </div>
        <div className="p-5">{children}</div>
      </section>
    </div>
  )
}

/** ฟอร์ม Loopback แยกจาก inventory เพราะสร้าง interface ใหม่ได้ */
function LoopbackPanel({ interfaces, onPreview, isPreviewing, previewError }: { interfaces: Record<string, string>[]; onPreview: (intent: LoopbackPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const form = useForm<LoopbackForm>({
    resolver: zodResolver(loopbackSchema),
    defaultValues: { loopback_id: 0, ip_address: '', subnet_mask: '255.255.255.255', description: '', admin_up: true },
  })
  const loopbacks = interfaces.filter((row) => /^loopback\d+$/i.test(row.interface ?? ''))
  const [selectedLoopback, setSelectedLoopback] = useState('')

  const submit = (data: LoopbackForm) => onPreview({
    mode: 'create',
    payload: {
      loopback_id: data.loopback_id,
      ip_address: data.ip_address,
      subnet_mask: data.subnet_mask,
      ...(data.description ? { description: data.description } : {}),
      admin_up: data.admin_up,
    },
  })
  const remove = () => {
    const match = /^loopback(\d+)$/i.exec(selectedLoopback)
    if (match) onPreview({ mode: 'remove', loopback_id: Number(match[1]) })
  }

  return <section className="card">
    <h3 className="text-lg font-semibold mb-1">Loopback</h3>
    <p className="text-sm text-gray-500 mb-5">สร้าง virtual routed interface แยกจากรายการ Interface ที่มีอยู่</p>
    <form onSubmit={form.handleSubmit(submit)} className="space-y-4">
      <Field label="Loopback Number" error={form.formState.errors.loopback_id?.message}><input type="number" min={0} step={1} {...form.register('loopback_id', { valueAsNumber: true })} className="input-field font-mono" /></Field>
      <div className="grid grid-cols-2 gap-3"><Field label="IP Address" error={form.formState.errors.ip_address?.message}><input {...form.register('ip_address')} className="input-field font-mono" placeholder="1.1.1.1" /></Field><Field label="Subnet Mask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" placeholder="255.255.255.255" /></Field></div>
      <Field label="Description" error={form.formState.errors.description?.message}><input {...form.register('description')} className="input-field" placeholder="Router ID" /></Field>
      <label className="flex items-center gap-3 text-sm"><input type="checkbox" {...form.register('admin_up')} className="w-4 h-4 accent-blue-600" /> no shutdown (administratively up)</label>
      {previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
      <button type="submit" className="btn-primary w-full flex justify-center gap-2" disabled={isPreviewing}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Preview Loopback</button>
    </form>
    <div className="mt-5 pt-4 border-t border-gray-200 space-y-3">
      <div><h4 className="text-sm font-semibold">Existing Loopbacks</h4><p className="text-xs text-gray-500">เลือกจาก inventory เพื่อสร้าง preview ลบเท่านั้น</p></div>
      <select value={selectedLoopback} onChange={(event) => setSelectedLoopback(event.target.value)} className="select-field font-mono" disabled={isPreviewing || loopbacks.length === 0}>
        <option value="">{loopbacks.length ? 'เลือก Loopback ที่จะลบ' : 'ยังไม่พบ Loopback'}</option>
        {loopbacks.map((row) => <option key={row.interface} value={row.interface}>{row.interface} — {row.ip ?? 'unassigned'}</option>)}
      </select>
      <button type="button" className="btn-secondary w-full text-red-700 border-red-300 hover:bg-red-50" disabled={!selectedLoopback || isPreviewing} onClick={remove}>Preview Remove Loopback</button>
    </div>
  </section>
}

/** L2 access port ใช้เฉพาะ inventory และ VLAN actual state ที่ backend อ่านให้ */
function AccessPortPanel({ interfaces, vlans, switchportSupported, isVlanLoading, vlanError, onRefreshVlans, onPreview, isPreviewing, previewError }: { interfaces: Record<string, string>[]; vlans: VlanEntry[]; switchportSupported: boolean; isVlanLoading: boolean; vlanError: Error | null; onRefreshVlans: () => void; onPreview: (payload: AccessPortConfig) => void; isPreviewing: boolean; previewError: Error | null }) {
  const form = useForm<AccessPortForm>({
    resolver: zodResolver(accessPortSchema),
    defaultValues: { interface_name: '', vlan_id: 1, description: '', admin_up: true },
  })
  const physicalInterfaces = interfaces.filter((row) => !/^(loopback|vlan)/i.test(row.interface ?? ''))
  const unavailable = !switchportSupported || isVlanLoading || vlans.length === 0

  return <section className="card">
    <div className="flex items-center justify-between gap-2 mb-1"><h3 className="text-lg font-semibold">L2 Access Port</h3><button type="button" className="btn-secondary btn-sm" onClick={onRefreshVlans} disabled={isVlanLoading || !switchportSupported}>Refresh VLAN</button></div>
    <p className="text-sm text-gray-500 mb-5">เลือกพอร์ตและ VLAN ที่มีอยู่จริง แล้วตรวจ switchport ซ้ำก่อน Preview</p>
    {!switchportSupported && <div role="status" className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">อุปกรณ์นี้ไม่รองรับ switchport จึงตั้ง L2 access port ไม่ได้</div>}
    {vlanError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">โหลด VLAN ไม่สำเร็จ: {getApiMessage(vlanError)}</div>}
    <form onSubmit={form.handleSubmit(onPreview)} className="space-y-4">
      <Field label="Physical Interface" error={form.formState.errors.interface_name?.message}><select {...form.register('interface_name')} className="select-field font-mono" disabled={unavailable || physicalInterfaces.length === 0}><option value="">{physicalInterfaces.length ? 'เลือก physical interface' : 'ไม่พบ physical interface'}</option>{physicalInterfaces.map((row) => <option key={row.interface} value={row.interface}>{row.interface} — {row.status}/{row.protocol}</option>)}</select></Field>
      <Field label="Access VLAN" error={form.formState.errors.vlan_id?.message}><select {...form.register('vlan_id', { valueAsNumber: true })} className="select-field font-mono" disabled={unavailable}><option value="">{isVlanLoading ? 'กำลังโหลด VLAN...' : 'เลือก VLAN'}</option>{vlans.map((vlan) => <option key={vlan.vlan_id} value={vlan.vlan_id}>VLAN {vlan.vlan_id} — {vlan.name} ({vlan.status})</option>)}</select></Field>
      <Field label="Description" error={form.formState.errors.description?.message}><input {...form.register('description')} className="input-field" placeholder="User access port" /></Field>
      <label className="flex items-center gap-3 text-sm"><input type="checkbox" {...form.register('admin_up')} className="w-4 h-4 accent-blue-600" /> no shutdown (administratively up)</label>
      {previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
      <button type="submit" className="btn-primary w-full flex justify-center gap-2" disabled={unavailable || isPreviewing}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Preview Access Port</button>
    </form>
  </section>
}

/** แปลง L2 port เป็น L3 และคืน L2 พื้นฐานตาม ADR-026 */
function RoutedPortPanel({ interfaces, switchportSupported, onPreview, isPreviewing, previewError }: { interfaces: Record<string, string>[]; switchportSupported: boolean; onPreview: (intent: RoutedPortPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const form = useForm<RoutedPortForm>({ resolver: zodResolver(routedPortSchema), defaultValues: { interface_name: '', ip_address: '', subnet_mask: '255.255.255.0', description: '', admin_up: true } })
  const [restoreInterface, setRestoreInterface] = useState('')
  const physicalInterfaces = interfaces.filter((row) => !/^(loopback|vlan)/i.test(row.interface ?? ''))
  const submit = (data: RoutedPortForm) => onPreview({ mode: 'create', payload: { interface_name: data.interface_name, ip_address: data.ip_address, subnet_mask: data.subnet_mask, ...(data.description ? { description: data.description } : {}), admin_up: data.admin_up } })

  return <section className="card">
    <h3 className="text-lg font-semibold mb-1">L3 Routed Port</h3>
    <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-5">การ Apply จะส่ง <code>no switchport</code> และค่า L2 เดิมอาจไม่ใช้งานต่อ. Restore จะลบ IPv4 แล้วคืน <code>switchport</code> เท่านั้น — ไม่คืน VLAN/trunk/description/admin state เดิม</p>
    {!switchportSupported && <div role="status" className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3">อุปกรณ์นี้ไม่รองรับ L3 routed-port workflow</div>}
    {switchportSupported && <><form onSubmit={form.handleSubmit(submit)} className="space-y-4"><Field label="L2 Physical Interface" error={form.formState.errors.interface_name?.message}><select {...form.register('interface_name')} className="select-field font-mono" disabled={isPreviewing || physicalInterfaces.length === 0}><option value="">เลือกพอร์ต L2 ที่จะแปลง</option>{physicalInterfaces.map((row) => <option key={row.interface} value={row.interface}>{row.interface} — {row.status}/{row.protocol}</option>)}</select></Field><div className="grid grid-cols-2 gap-3"><Field label="IP Address" error={form.formState.errors.ip_address?.message}><input {...form.register('ip_address')} className="input-field font-mono" placeholder="10.0.0.1" /></Field><Field label="Subnet Mask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" /></Field></div><Field label="Description" error={form.formState.errors.description?.message}><input {...form.register('description')} className="input-field" placeholder="Routed uplink" /></Field><label className="flex items-center gap-3 text-sm"><input type="checkbox" {...form.register('admin_up')} className="w-4 h-4 accent-blue-600" /> no shutdown</label><button type="submit" className="btn-primary w-full flex justify-center gap-2" disabled={isPreviewing}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Preview Convert to L3</button></form><div className="mt-5 pt-4 border-t border-gray-200 space-y-2"><h4 className="font-semibold text-sm">Restore Basic L2 Switchport</h4><select value={restoreInterface} onChange={(event) => setRestoreInterface(event.target.value)} className="select-field font-mono" disabled={isPreviewing || physicalInterfaces.length === 0}><option value="">เลือกพอร์ต L3 ที่จะคืน</option>{physicalInterfaces.map((row) => <option key={row.interface} value={row.interface}>{row.interface}</option>)}</select><button type="button" className="btn-secondary btn-sm" disabled={!restoreInterface || isPreviewing} onClick={() => onPreview({ mode: 'restore', interface_name: restoreInterface })}>Preview Restore L2</button></div>{previewError && <div role="alert" className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}</>}
  </section>
}

/** จัดการ VLAN และ SVI แบบคนละ resource เพื่อให้ขอบเขตการลบชัดเจน */
function VlanSviPanel({ interfaces, vlans, vlanSupported, isVlanLoading, onRefreshVlans, onPreview, isPreviewing, previewError }: { interfaces: Record<string, string>[]; vlans: VlanEntry[]; vlanSupported: boolean; isVlanLoading: boolean; onRefreshVlans: () => void; onPreview: (intent: VlanSviPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const vlanForm = useForm<VlanForm>({ resolver: zodResolver(vlanSchema), defaultValues: { vlan_id: 20, name: '' } })
  const sviForm = useForm<SviForm>({ resolver: zodResolver(sviSchema), defaultValues: { vlan_id: 1, ip_address: '', subnet_mask: '255.255.255.0', description: '', admin_up: true } })
  const [removeVlanId, setRemoveVlanId] = useState('')
  const [removeSviId, setRemoveSviId] = useState('')
  const existingSvis = interfaces.filter((row) => /^vlan\d+$/i.test(row.interface ?? ''))
  const unavailable = !vlanSupported || isVlanLoading

  const createVlan = (data: VlanForm) => onPreview({ mode: 'vlan_create', payload: { vlan_id: data.vlan_id, ...(data.name ? { name: data.name } : {}) } })
  const createSvi = (data: SviForm) => onPreview({ mode: 'svi_create', payload: { vlan_id: data.vlan_id, ip_address: data.ip_address, subnet_mask: data.subnet_mask, ...(data.description ? { description: data.description } : {}), admin_up: data.admin_up } })
  const removeVlan = () => { if (removeVlanId) onPreview({ mode: 'vlan_remove', vlan_id: Number(removeVlanId) }) }
  const removeSvi = () => { const match = /^vlan(\d+)$/i.exec(removeSviId); if (match) onPreview({ mode: 'svi_remove', vlan_id: Number(match[1]) }) }

  return <section className="card">
    <div className="flex items-center justify-between gap-2 mb-1"><h3 className="text-lg font-semibold">VLAN / SVI</h3><button type="button" className="btn-secondary btn-sm" onClick={onRefreshVlans} disabled={isVlanLoading || !vlanSupported}>Refresh VLAN</button></div>
    <p className="text-sm text-gray-500 mb-5">VLAN และ SVI เป็นคนละ resource — ต้องลบ SVI ก่อนลบ VLAN</p>
    {!vlanSupported && <div role="status" className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3">อุปกรณ์นี้ไม่รองรับ VLAN/SVI management</div>}
    {vlanSupported && <div className="space-y-5">
      <form onSubmit={vlanForm.handleSubmit(createVlan)} className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3"><h4 className="font-semibold text-sm">Create VLAN</h4><div className="grid grid-cols-2 gap-3"><Field label="VLAN ID" error={vlanForm.formState.errors.vlan_id?.message}><input type="number" min={2} max={4094} {...vlanForm.register('vlan_id', { valueAsNumber: true })} className="input-field font-mono" /></Field><Field label="Name" error={vlanForm.formState.errors.name?.message}><input {...vlanForm.register('name')} className="input-field" placeholder="USERS" /></Field></div><button type="submit" className="btn-primary btn-sm" disabled={unavailable || isPreviewing}>Preview Create VLAN</button></form>
      <form onSubmit={sviForm.handleSubmit(createSvi)} className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3"><h4 className="font-semibold text-sm">Create SVI</h4><Field label="Existing VLAN" error={sviForm.formState.errors.vlan_id?.message}><select {...sviForm.register('vlan_id', { valueAsNumber: true })} className="select-field font-mono" disabled={unavailable || vlans.length === 0}>{vlans.map((vlan) => <option key={vlan.vlan_id} value={vlan.vlan_id}>VLAN {vlan.vlan_id} — {vlan.name}</option>)}</select></Field><div className="grid grid-cols-2 gap-3"><Field label="IP Address" error={sviForm.formState.errors.ip_address?.message}><input {...sviForm.register('ip_address')} className="input-field font-mono" placeholder="192.168.20.1" /></Field><Field label="Subnet Mask" error={sviForm.formState.errors.subnet_mask?.message}><input {...sviForm.register('subnet_mask')} className="input-field font-mono" /></Field></div><Field label="Description" error={sviForm.formState.errors.description?.message}><input {...sviForm.register('description')} className="input-field" placeholder="Management SVI" /></Field><label className="flex items-center gap-3 text-sm"><input type="checkbox" {...sviForm.register('admin_up')} className="w-4 h-4 accent-blue-600" /> no shutdown</label><button type="submit" className="btn-primary btn-sm" disabled={unavailable || vlans.length === 0 || isPreviewing}>Preview Create SVI</button></form>
      <div className="grid grid-cols-1 gap-3"><div className="rounded-lg border border-red-200 p-3 space-y-2"><h4 className="font-semibold text-sm text-red-700">Remove SVI</h4><select value={removeSviId} onChange={(event) => setRemoveSviId(event.target.value)} className="select-field font-mono" disabled={isPreviewing || existingSvis.length === 0}><option value="">{existingSvis.length ? 'เลือก SVI' : 'ไม่พบ SVI'}</option>{existingSvis.map((svi) => <option key={svi.interface} value={svi.interface}>{svi.interface} — {svi.ip ?? 'unassigned'}</option>)}</select><button type="button" className="btn-secondary btn-sm text-red-700 border-red-300" disabled={!removeSviId || isPreviewing} onClick={removeSvi}>Preview Remove SVI</button></div><div className="rounded-lg border border-red-200 p-3 space-y-2"><h4 className="font-semibold text-sm text-red-700">Remove VLAN</h4><select value={removeVlanId} onChange={(event) => setRemoveVlanId(event.target.value)} className="select-field font-mono" disabled={isPreviewing || vlans.filter((vlan) => vlan.vlan_id > 1).length === 0}><option value="">เลือก VLAN (2–4094)</option>{vlans.filter((vlan) => vlan.vlan_id > 1).map((vlan) => <option key={vlan.vlan_id} value={vlan.vlan_id}>VLAN {vlan.vlan_id} — {vlan.name}</option>)}</select><button type="button" className="btn-secondary btn-sm text-red-700 border-red-300" disabled={!removeVlanId || isPreviewing} onClick={removeVlan}>Preview Remove VLAN</button></div></div>
      {previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
    </div>}
  </section>
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return <div><label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>{children}{error && <p className="error-msg">{error}</p>}</div>
}

function routeToConfig(route: StaticRouteEntry): StaticRouteConfig {
  return {
    destination: route.destination,
    subnet_mask: route.subnet_mask,
    ...(route.next_hop ? { next_hop: route.next_hop } : { exit_interface: route.exit_interface }),
  }
}

/** แผง Routing ตาม Design; เปิดเฉพาะ protocol ที่ผ่าน phase gate แล้ว */
function RoutingPanel({ nodeId, onStaticPreview, onRipPreview, onOspfPreview, onEigrpPreview, onBgpPreview, isPreviewing, previewError }: { nodeId: string; onStaticPreview: (intent: StaticPreviewIntent) => void; onRipPreview: (intent: RipPreviewIntent) => void; onOspfPreview: (intent: OspfPreviewIntent) => void; onEigrpPreview: (intent: EigrpPreviewIntent) => void; onBgpPreview: (intent: BgpPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const [protocol, setProtocol] = useState<'bgp' | 'eigrp' | 'ospf' | 'rip' | 'static'>('static')
  const [editing, setEditing] = useState<StaticRouteEntry | null>(null)
  const routesQuery = useQuery({
    queryKey: ['static-routes', nodeId],
    queryFn: () => listStaticRoutes(nodeId),
    retry: false,
  })
  const ripQuery = useQuery({
    queryKey: ['rip-state', nodeId],
    queryFn: () => getRipState(nodeId),
    retry: false,
  })
  const ospfQuery = useQuery({ queryKey: ['ospf-state', nodeId], queryFn: () => getOspfState(nodeId), retry: false })
  const eigrpQuery = useQuery({ queryKey: ['eigrp-state', nodeId], queryFn: () => getEigrpState(nodeId), retry: false })
  const bgpQuery = useQuery({ queryKey: ['bgp-state', nodeId], queryFn: () => getBgpState(nodeId), retry: false })
  const form = useForm<StaticRouteForm>({
    resolver: zodResolver(staticRouteSchema),
    defaultValues: { destination: '', subnet_mask: '255.255.255.0', target_type: 'next_hop', target: '' },
  })
  const targetType = form.watch('target_type')
  const routes = routesQuery.data?.routes ?? []

  const toPayload = (data: StaticRouteForm): StaticRouteConfig => ({
    destination: data.destination,
    subnet_mask: data.subnet_mask,
    ...(data.target_type === 'next_hop' ? { next_hop: data.target } : { exit_interface: data.target }),
  })
  const cancelEdit = () => {
    setEditing(null)
    form.reset({ destination: '', subnet_mask: '255.255.255.0', target_type: 'next_hop', target: '' })
  }
  const startEdit = (route: StaticRouteEntry) => {
    setEditing(route)
    form.reset({
      destination: route.destination,
      subnet_mask: route.subnet_mask,
      target_type: route.next_hop ? 'next_hop' : 'exit_interface',
      target: route.next_hop ?? route.exit_interface ?? '',
    })
  }
  const submitRoute = (data: StaticRouteForm) => {
    const desired = toPayload(data)
    if (editing) onStaticPreview({ mode: 'update', current: routeToConfig(editing), desired })
    else onStaticPreview({ mode: 'add', payload: desired })
  }
  const useDefaultRoute = () => {
    form.setValue('destination', '0.0.0.0', { shouldValidate: true })
    form.setValue('subnet_mask', '0.0.0.0', { shouldValidate: true })
  }

  return (
    <section className="card p-0 overflow-hidden">
      <div className="flex flex-wrap items-center gap-4 px-5 py-4 bg-gray-50 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Routing Table</h3>
        <span className={`inline-flex items-center gap-2 text-sm ${ospfQuery.data?.enabled ? 'text-green-700' : 'text-gray-500'}`}><span className={`w-2 h-2 rounded-full ${ospfQuery.data?.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />OSPF <strong className="font-mono">{ospfQuery.data?.enabled ? `${ospfQuery.data.networks.length} networks` : 'Off'}</strong></span>
        <span className={`inline-flex items-center gap-2 text-sm ${eigrpQuery.data?.enabled ? 'text-green-700' : 'text-gray-500'}`}><span className={`w-2 h-2 rounded-full ${eigrpQuery.data?.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />EIGRP <strong className="font-mono">{eigrpQuery.data?.enabled ? `${eigrpQuery.data.networks.length} networks` : 'Off'}</strong></span>
        <span className={`inline-flex items-center gap-2 text-sm ${bgpQuery.data?.enabled ? 'text-green-700' : 'text-gray-500'}`}><span className={`w-2 h-2 rounded-full ${bgpQuery.data?.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />BGP <strong className="font-mono">{bgpQuery.data?.enabled ? `${bgpQuery.data.neighbors.length} peers` : 'Off'}</strong></span>
        <span className={`inline-flex items-center gap-2 text-sm ${ripQuery.data?.enabled ? 'text-green-700' : 'text-gray-500'}`}><span className={`w-2 h-2 rounded-full ${ripQuery.data?.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />RIP <strong className="font-mono">{ripQuery.data?.enabled ? `${ripQuery.data.networks.length} networks` : 'Off'}</strong></span>
        <span className="inline-flex items-center gap-2 text-sm text-amber-700"><span className="w-2 h-2 rounded-full bg-amber-500" />Static <strong className="font-mono">{routes.length} routes</strong></span>
      </div>
      <div className="flex overflow-x-auto border-b border-gray-200 px-3" role="tablist" aria-label="Routing protocols">
        <button type="button" role="tab" aria-selected={protocol === 'ospf'} onClick={() => setProtocol('ospf')} className={`px-4 py-3 text-sm ${protocol === 'ospf' ? 'font-medium text-accent-DEFAULT border-b-2 border-accent-DEFAULT' : 'text-gray-600'}`}>OSPF <span className={`ml-1 badge ${ospfQuery.data?.enabled ? 'badge-green' : 'badge-gray'}`}>{ospfQuery.data?.networks.length ?? 0}</span></button>
        <button type="button" role="tab" aria-selected={protocol === 'eigrp'} onClick={() => setProtocol('eigrp')} className={`px-4 py-3 text-sm ${protocol === 'eigrp' ? 'font-medium text-accent-DEFAULT border-b-2 border-accent-DEFAULT' : 'text-gray-600'}`}>EIGRP <span className={`ml-1 badge ${eigrpQuery.data?.enabled ? 'badge-green' : 'badge-gray'}`}>{eigrpQuery.data?.networks.length ?? 0}</span></button>
        <button type="button" role="tab" aria-selected={protocol === 'bgp'} onClick={() => setProtocol('bgp')} className={`px-4 py-3 text-sm ${protocol === 'bgp' ? 'font-medium text-accent-DEFAULT border-b-2 border-accent-DEFAULT' : 'text-gray-600'}`}>BGP <span className={`ml-1 badge ${bgpQuery.data?.enabled ? 'badge-green' : 'badge-gray'}`}>{bgpQuery.data?.neighbors.length ?? 0}</span></button>
        <button type="button" role="tab" aria-selected={protocol === 'rip'} onClick={() => setProtocol('rip')} className={`px-4 py-3 text-sm ${protocol === 'rip' ? 'font-medium text-accent-DEFAULT border-b-2 border-accent-DEFAULT' : 'text-gray-600'}`}>RIP <span className={`ml-1 badge ${ripQuery.data?.enabled ? 'badge-green' : 'badge-gray'}`}>{ripQuery.data?.networks.length ?? 0}</span></button>
        {['EIGRP', 'BGP'].map((name) => <button key={name} type="button" role="tab" disabled className="px-4 py-3 text-sm text-gray-400 cursor-not-allowed" title="ยังไม่ผ่าน phase gate">{name} <span className="ml-1 text-xs">0</span></button>)}
        <button type="button" role="tab" aria-selected={protocol === 'static'} onClick={() => setProtocol('static')} className={`px-4 py-3 text-sm ${protocol === 'static' ? 'font-medium text-accent-DEFAULT border-b-2 border-accent-DEFAULT' : 'text-gray-600'}`}>Static <span className="ml-1 badge badge-amber">{routes.length}</span></button>
      </div>

      {protocol === 'ospf' ? (
        <OspfRoutingContent state={ospfQuery.data ?? null} isLoading={ospfQuery.isLoading || ospfQuery.isFetching} error={ospfQuery.error} onRefresh={() => ospfQuery.refetch()} onPreview={onOspfPreview} isPreviewing={isPreviewing} previewError={previewError} />
      ) : protocol === 'eigrp' ? (
        <EigrpRoutingContent state={eigrpQuery.data ?? null} isLoading={eigrpQuery.isLoading || eigrpQuery.isFetching} error={eigrpQuery.error} onRefresh={() => eigrpQuery.refetch()} onPreview={onEigrpPreview} isPreviewing={isPreviewing} previewError={previewError} />
      ) : protocol === 'bgp' ? (
        <BgpRoutingContent state={bgpQuery.data ?? null} isLoading={bgpQuery.isLoading || bgpQuery.isFetching} error={bgpQuery.error} onRefresh={() => bgpQuery.refetch()} onPreview={onBgpPreview} isPreviewing={isPreviewing} previewError={previewError} />
      ) : protocol === 'rip' ? (
        <RipRoutingContent state={ripQuery.data ?? null} isLoading={ripQuery.isLoading || ripQuery.isFetching} error={ripQuery.error} onRefresh={() => ripQuery.refetch()} onPreview={onRipPreview} isPreviewing={isPreviewing} previewError={previewError} />
      ) : <div className="p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h4 className="text-lg font-semibold">Static / Default Routes</h4><p className="text-sm text-gray-500">อ่านจาก running-config และ Apply ผ่าน typed preview เท่านั้น</p></div>
          <button type="button" className="btn-secondary btn-sm flex items-center gap-2" onClick={() => routesQuery.refetch()} disabled={routesQuery.isFetching}>{routesQuery.isFetching ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}Refresh</button>
        </div>

        {routesQuery.error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด Static route ไม่สำเร็จ: {getApiMessage(routesQuery.error)}</div>}
        <div className="table-wrap overflow-auto">
          <table className="ds-table min-w-[720px]"><thead><tr><th>Destination</th><th>Mask</th><th>Next Hop / Exit</th><th>Type</th><th className="text-right">Actions</th></tr></thead><tbody>
            {routes.length ? routes.map((route, index) => (
              <tr key={`${route.destination}-${route.subnet_mask}-${route.next_hop ?? route.exit_interface}-${index}`} className={editing === route ? 'bg-blue-50' : ''}>
                <td className="font-mono text-xs">{route.destination}</td><td className="font-mono text-xs">{route.subnet_mask}</td><td className="font-mono text-xs">{route.next_hop ?? route.exit_interface}</td>
                <td><span className={`badge ${route.route_type === 'default' ? 'badge-amber' : 'badge-blue'}`}><span className="badge-dot" />{route.route_type === 'default' ? 'Default' : 'Static'}</span></td>
                <td><div className="flex justify-end gap-1"><button type="button" className="btn-ghost btn-sm" onClick={() => startEdit(route)}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onStaticPreview({ mode: 'remove', payload: routeToConfig(route) })}>Delete</button></div></td>
              </tr>
            )) : <tr><td colSpan={5} className="text-center text-gray-500 py-10">{routesQuery.isLoading ? 'กำลังโหลด Static route...' : 'ยังไม่มี Static/Default route'}</td></tr>}
          </tbody></table>
        </div>

        {editing && <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex items-center justify-between"><span>กำลังแก้ route <strong className="font-mono">{editing.destination}</strong></span><button type="button" className="btn-ghost btn-sm" onClick={cancelEdit}>Cancel</button></div>}

        <form onSubmit={form.handleSubmit(submitRoute)} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4">
          <div className="flex items-center justify-between gap-3"><h5 className="font-semibold text-sm">{editing ? 'Edit Route' : 'Add Route'}</h5><button type="button" className="btn-secondary btn-sm" onClick={useDefaultRoute}>Default Route</button></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <Field label="Destination" error={form.formState.errors.destination?.message}><input {...form.register('destination')} className="input-field font-mono" placeholder="172.16.0.0" /></Field>
            <Field label="Subnet Mask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" placeholder="255.255.0.0" /></Field>
            <Field label="Target Type"><select {...form.register('target_type')} className="select-field"><option value="next_hop">Next Hop</option><option value="exit_interface">Exit Interface</option></select></Field>
          </div>
          <Field label={targetType === 'next_hop' ? 'Next Hop' : 'Exit Interface'} error={form.formState.errors.target?.message}><input {...form.register('target')} className="input-field font-mono" placeholder={targetType === 'next_hop' ? '10.0.23.2' : 'GigabitEthernet0/1'} /></Field>
          {previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
          <div className="flex gap-2"><button type="submit" className="btn-primary btn-sm flex items-center gap-2" disabled={isPreviewing}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}{editing ? 'Preview Update' : 'Preview Route'}</button>{editing && <button type="button" className="btn-secondary btn-sm" onClick={cancelEdit}>Cancel</button>}</div>
        </form>
      </div>}
    </section>
  )
}

function RipRoutingContent({ state, isLoading, error, onRefresh, onPreview, isPreviewing, previewError }: { state: RipStateResponse | null; isLoading: boolean; error: Error | null; onRefresh: () => void; onPreview: (intent: RipPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const [editing, setEditing] = useState<string | null>(null)
  const form = useForm<RipNetworkForm>({
    resolver: zodResolver(ripNetworkSchema),
    defaultValues: { version: 2, network: '' },
  })

  useEffect(() => {
    if (!editing && state?.version) form.setValue('version', state.version)
  }, [editing, form, state?.version])

  const resetForm = () => {
    setEditing(null)
    form.reset({ version: state?.version ?? 2, network: '' })
  }
  const startEdit = (network: string) => {
    setEditing(network)
    form.reset({ version: state?.version ?? 2, network })
  }
  const submit = (data: RipNetworkForm) => {
    const desired: RipNetworkConfig = { version: data.version, network: data.network }
    if (editing) {
      onPreview({ mode: 'update', current: { version: state?.version ?? data.version, network: editing }, desired })
    } else {
      onPreview({ mode: 'add', payload: desired })
    }
  }

  return (
    <div className="p-5 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3"><h4 className="text-lg font-semibold">RIP — Routing Information Protocol</h4><span className={`badge ${state?.enabled ? 'badge-green' : 'badge-gray'}`}><span className="badge-dot" />{state?.enabled ? 'Active' : 'Off'}</span></div>
          <p className="text-sm text-gray-500">{state?.enabled ? `Version ${state.version} · ${state.networks.length} network · ${state.no_auto_summary ? 'no auto-summary' : 'auto-summary'}` : 'ยังไม่ได้กำหนด RIP process'}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-secondary btn-sm flex items-center gap-2" onClick={onRefresh} disabled={isLoading}>{isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}Refresh</button>
          {state?.enabled && <button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove_process', state })}>Remove Protocol</button>}
        </div>
      </div>

      {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด RIP ไม่สำเร็จ: {getApiMessage(error)}</div>}
      <div className="table-wrap overflow-auto">
        <table className="ds-table min-w-[620px]"><thead><tr><th>Network</th><th>Version</th><th>Status</th><th className="text-right">Actions</th></tr></thead><tbody>
          {state?.networks.length ? state.networks.map((network) => (
            <tr key={network} className={editing === network ? 'bg-blue-50' : ''}>
              <td className="font-mono text-xs">{network}</td><td className="font-mono text-xs">RIPv{state.version}</td><td><span className="badge badge-green"><span className="badge-dot" />Applied</span></td>
              <td><div className="flex justify-end gap-1"><button type="button" className="btn-ghost btn-sm" onClick={() => startEdit(network)}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove', payload: { version: state.version ?? 2, network } })}>Delete</button></div></td>
            </tr>
          )) : <tr><td colSpan={4} className="text-center text-gray-500 py-10">{isLoading ? 'กำลังโหลด RIP...' : 'ยังไม่มี RIP network'}</td></tr>}
        </tbody></table>
      </div>

      {editing && <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex items-center justify-between"><span>กำลังแก้ network <strong className="font-mono">{editing}</strong></span><button type="button" className="btn-ghost btn-sm" onClick={resetForm}>Cancel</button></div>}

      <form onSubmit={form.handleSubmit(submit)} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4">
        <h5 className="font-semibold text-sm">{editing ? 'Edit Network' : state?.enabled ? 'Add Network' : 'Enable RIP & Add Network'}</h5>
        <div className="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-3">
          <Field label="RIP Version" error={form.formState.errors.version?.message}><select {...form.register('version', { valueAsNumber: true })} className="select-field"><option value={2}>Version 2</option><option value={1}>Version 1</option></select></Field>
          <Field label="Network to Advertise" error={form.formState.errors.network?.message}><input {...form.register('network')} className="input-field font-mono" placeholder="10.0.0.0" /><p className="text-xs text-gray-500 mt-1">ใช้ major network boundary ตาม IOS RIP เช่น 10.0.0.0</p></Field>
        </div>
        <div className="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-800">ระบบจะตั้ง <code>no auto-summary</code> ทุกครั้งเพื่อให้พฤติกรรมชัดเจน</div>
        {previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}
        <div className="flex gap-2"><button type="submit" className="btn-primary btn-sm flex items-center gap-2" disabled={isPreviewing}>{isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}{editing ? 'Preview Update' : 'Preview Changes'}</button>{editing && <button type="button" className="btn-secondary btn-sm" onClick={resetForm}>Cancel</button>}</div>
      </form>
    </div>
  )
}

function OspfRoutingContent({ state, isLoading, error, onRefresh, onPreview, isPreviewing, previewError }: { state: OspfStateResponse | null; isLoading: boolean; error: Error | null; onRefresh: () => void; onPreview: (intent: OspfPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const [editing, setEditing] = useState<OspfNetworkConfig | null>(null)
  const form = useForm<OspfNetworkForm>({ resolver: zodResolver(ospfNetworkSchema), defaultValues: { process_id: 1, router_id: '', network: '10.0.23.0', subnet_mask: '255.255.255.252', area: 0 } })
  useEffect(() => { if (!editing && state?.enabled) form.reset({ process_id: state.process_id ?? 1, router_id: state.router_id ?? '', network: '', subnet_mask: '255.255.255.0', area: 0 }) }, [editing, form, state])
  const reset = () => { setEditing(null); form.reset({ process_id: state?.process_id ?? 1, router_id: state?.router_id ?? '', network: '', subnet_mask: '255.255.255.0', area: 0 }) }
  const edit = (entry: OspfNetworkConfig) => { setEditing(entry); form.reset(entry) }
  const submit = (data: OspfNetworkForm) => {
    const desired: OspfNetworkConfig = data
    if (editing) onPreview({ mode: 'update', current: editing, desired })
    else onPreview({ mode: 'add', payload: desired })
  }
  return <div className="p-5 space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-3"><h4 className="text-lg font-semibold">OSPF — Open Shortest Path First</h4><span className={`badge ${state?.enabled ? 'badge-green' : 'badge-gray'}`}><span className="badge-dot" />{state?.enabled ? 'Active' : 'Off'}</span></div><p className="text-sm text-gray-500">{state?.enabled ? `Process ${state.process_id} · Router-ID ${state.router_id} · ${state.networks.length} networks` : 'ยังไม่ได้กำหนด OSPF process'}</p></div><div className="flex gap-2"><button type="button" className="btn-secondary btn-sm" onClick={onRefresh} disabled={isLoading}>Refresh</button>{state?.enabled && <button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove_process', state })}>Remove Protocol</button>}</div></div>
    {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด OSPF ไม่สำเร็จ: {getApiMessage(error)}</div>}
    <div className="table-wrap overflow-auto"><table className="ds-table min-w-[720px]"><thead><tr><th>Network</th><th>Netmask</th><th>Area</th><th>Status</th><th className="text-right">Actions</th></tr></thead><tbody>{state?.networks.length ? state.networks.map((entry) => <tr key={`${entry.network}-${entry.subnet_mask}-${entry.area}`}><td className="font-mono text-xs">{entry.network}</td><td className="font-mono text-xs">{entry.subnet_mask}</td><td className="font-mono text-xs">{entry.area}</td><td><span className="badge badge-green"><span className="badge-dot" />Applied</span></td><td><div className="flex justify-end gap-1"><button type="button" className="btn-ghost btn-sm" onClick={() => edit(entry)}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove', payload: entry })}>Delete</button></div></td></tr>) : <tr><td colSpan={5} className="text-center text-gray-500 py-10">{isLoading ? 'กำลังโหลด OSPF...' : 'ยังไม่มี OSPF network'}</td></tr>}</tbody></table></div>
    {editing && <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex justify-between"><span>กำลังแก้ network <strong className="font-mono">{editing.network}</strong></span><button type="button" className="btn-ghost btn-sm" onClick={reset}>Cancel</button></div>}
    <form onSubmit={form.handleSubmit(submit)} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"><h5 className="font-semibold text-sm">{editing ? 'Edit Network' : state?.enabled ? 'Add Network' : 'Enable OSPF & Add Network'}</h5><div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3"><Field label="Process ID" error={form.formState.errors.process_id?.message}><input type="number" {...form.register('process_id', { valueAsNumber: true })} className="input-field" /></Field><Field label="Router ID" error={form.formState.errors.router_id?.message}><input {...form.register('router_id')} className="input-field font-mono" placeholder="2.2.2.2" /></Field><Field label="Network" error={form.formState.errors.network?.message}><input {...form.register('network')} className="input-field font-mono" placeholder="10.0.23.0" /></Field><Field label="Netmask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" /></Field><Field label="Area" error={form.formState.errors.area?.message}><input type="number" {...form.register('area', { valueAsNumber: true })} className="input-field" /></Field></div><p className="text-xs text-gray-500">Wildcard mask จะคำนวณจาก Netmask ใน backend</p>{previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}<div className="flex gap-2"><button type="submit" className="btn-primary btn-sm" disabled={isPreviewing}>{editing ? 'Preview Update' : 'Preview Changes'}</button>{editing && <button type="button" className="btn-secondary btn-sm" onClick={reset}>Cancel</button>}</div></form>
  </div>
}

/** ฟอร์ม EIGRP ตาม Design: อ่าน actual state ก่อนแก้และใช้ preview ทุก mutation */
function EigrpRoutingContent({ state, isLoading, error, onRefresh, onPreview, isPreviewing, previewError }: { state: EigrpStateResponse | null; isLoading: boolean; error: Error | null; onRefresh: () => void; onPreview: (intent: EigrpPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const [editing, setEditing] = useState<EigrpNetworkConfig | null>(null)
  const form = useForm<EigrpNetworkForm>({ resolver: zodResolver(eigrpNetworkSchema), defaultValues: { as_number: 100, router_id: '', network: '10.0.23.0', subnet_mask: '255.255.255.252' } })
  useEffect(() => { if (!editing && state?.enabled) form.reset({ as_number: state.as_number ?? 100, router_id: state.router_id ?? '', network: '', subnet_mask: '255.255.255.0' }) }, [editing, form, state])
  const reset = () => { setEditing(null); form.reset({ as_number: state?.as_number ?? 100, router_id: state?.router_id ?? '', network: '', subnet_mask: '255.255.255.0' }) }
  const submit = (data: EigrpNetworkForm) => { const desired: EigrpNetworkConfig = data; if (editing) onPreview({ mode: 'update', current: editing, desired }); else onPreview({ mode: 'add', payload: desired }) }
  return <div className="p-5 space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-3"><h4 className="text-lg font-semibold">EIGRP — Enhanced Interior Gateway Routing Protocol</h4><span className={`badge ${state?.enabled ? 'badge-green' : 'badge-gray'}`}><span className="badge-dot" />{state?.enabled ? 'Active' : 'Off'}</span></div><p className="text-sm text-gray-500">{state?.enabled ? `AS ${state.as_number} · Router-ID ${state.router_id} · ${state.networks.length} networks` : 'ยังไม่ได้กำหนด EIGRP process'}</p></div><div className="flex gap-2"><button type="button" className="btn-secondary btn-sm" onClick={onRefresh} disabled={isLoading}>Refresh</button>{state?.enabled && <button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove_process', state })}>Remove Protocol</button>}</div></div>
    {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด EIGRP ไม่สำเร็จ: {getApiMessage(error)}</div>}
    <div className="table-wrap overflow-auto"><table className="ds-table min-w-[660px]"><thead><tr><th>Network</th><th>Netmask</th><th>Status</th><th className="text-right">Actions</th></tr></thead><tbody>{state?.networks.length ? state.networks.map((entry) => <tr key={`${entry.network}-${entry.subnet_mask}`}><td className="font-mono text-xs">{entry.network}</td><td className="font-mono text-xs">{entry.subnet_mask}</td><td><span className="badge badge-green"><span className="badge-dot" />Applied</span></td><td><div className="flex justify-end gap-1"><button type="button" className="btn-ghost btn-sm" onClick={() => { setEditing(entry); form.reset(entry) }}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove', payload: entry })}>Delete</button></div></td></tr>) : <tr><td colSpan={4} className="text-center text-gray-500 py-10">{isLoading ? 'กำลังโหลด EIGRP...' : 'ยังไม่มี EIGRP network'}</td></tr>}</tbody></table></div>
    {editing && <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex justify-between"><span>กำลังแก้ network <strong className="font-mono">{editing.network}</strong></span><button type="button" className="btn-ghost btn-sm" onClick={reset}>Cancel</button></div>}
    <form onSubmit={form.handleSubmit(submit)} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"><h5 className="font-semibold text-sm">{editing ? 'Edit Network' : state?.enabled ? 'Add Network' : 'Enable EIGRP & Add Network'}</h5><div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3"><Field label="AS Number" error={form.formState.errors.as_number?.message}><input type="number" {...form.register('as_number', { valueAsNumber: true })} className="input-field" /></Field><Field label="Router ID" error={form.formState.errors.router_id?.message}><input {...form.register('router_id')} className="input-field font-mono" placeholder="2.2.2.2" /></Field><Field label="Network" error={form.formState.errors.network?.message}><input {...form.register('network')} className="input-field font-mono" placeholder="10.0.23.0" /></Field><Field label="Netmask" error={form.formState.errors.subnet_mask?.message}><input {...form.register('subnet_mask')} className="input-field font-mono" /></Field></div><div className="rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-800">Wildcard mask จะคำนวณจาก Netmask ใน backend และระบบจะตั้ง <code>no auto-summary</code></div>{previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}<div className="flex gap-2"><button type="submit" className="btn-primary btn-sm" disabled={isPreviewing}>{editing ? 'Preview Update' : 'Preview Changes'}</button>{editing && <button type="button" className="btn-secondary btn-sm" onClick={reset}>Cancel</button>}</div></form>
  </div>
}

/** ฟอร์ม BGP แยก neighbor และ advertised network ตาม Design reference */
function BgpRoutingContent({ state, isLoading, error, onRefresh, onPreview, isPreviewing, previewError }: { state: BgpStateResponse | null; isLoading: boolean; error: Error | null; onRefresh: () => void; onPreview: (intent: BgpPreviewIntent) => void; isPreviewing: boolean; previewError: Error | null }) {
  const [editingNeighbor, setEditingNeighbor] = useState<BgpNeighborConfig | null>(null)
  const [editingNetwork, setEditingNetwork] = useState<BgpNetworkConfig | null>(null)
  const neighborForm = useForm<BgpNeighborForm>({ resolver: zodResolver(bgpNeighborSchema), defaultValues: { local_as: 65001, router_id: '', neighbor_ip: '10.0.23.2', remote_as: 65002, description: '' } })
  const networkForm = useForm<BgpNetworkForm>({ resolver: zodResolver(bgpNetworkSchema), defaultValues: { local_as: 65001, network: '', subnet_mask: '255.255.255.0' } })
  useEffect(() => { if (state?.enabled) { neighborForm.setValue('local_as', state.local_as ?? 65001); neighborForm.setValue('router_id', state.router_id ?? ''); networkForm.setValue('local_as', state.local_as ?? 65001) } }, [neighborForm, networkForm, state])
  return <div className="p-5 space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-3"><h4 className="text-lg font-semibold">BGP — Border Gateway Protocol</h4><span className={`badge ${state?.enabled ? 'badge-green' : 'badge-gray'}`}><span className="badge-dot" />{state?.enabled ? 'Active' : 'Off'}</span></div><p className="text-sm text-gray-500">{state?.enabled ? `Local AS ${state.local_as} · Router-ID ${state.router_id}` : 'เพิ่ม neighbor เพื่อเปิด BGP process'}</p></div><div className="flex gap-2"><button type="button" className="btn-secondary btn-sm" onClick={onRefresh} disabled={isLoading}>Refresh</button>{state?.enabled && <button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'remove_process', state })}>Remove Protocol</button>}</div></div>
    {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">โหลด BGP ไม่สำเร็จ: {getApiMessage(error)}</div>}
    <div className="table-wrap overflow-auto"><table className="ds-table min-w-[700px]"><thead><tr><th>Neighbor</th><th>Remote AS</th><th>Description</th><th className="text-right">Actions</th></tr></thead><tbody>{state?.neighbors.length ? state.neighbors.map((entry) => <tr key={entry.neighbor_ip}><td className="font-mono text-xs">{entry.neighbor_ip}</td><td className="font-mono text-xs">{entry.remote_as}</td><td>{entry.description ?? '—'}</td><td className="text-right"><button type="button" className="btn-ghost btn-sm" onClick={() => { setEditingNeighbor(entry); neighborForm.reset(entry) }}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'neighbor_remove', payload: entry })}>Delete</button></td></tr>) : <tr><td colSpan={4} className="text-center text-gray-500 py-8">{isLoading ? 'กำลังโหลด BGP...' : 'ยังไม่มี BGP neighbor'}</td></tr>}</tbody></table></div>
    <form onSubmit={neighborForm.handleSubmit((data) => editingNeighbor ? onPreview({ mode: 'neighbor_update', current: editingNeighbor, desired: data }) : onPreview({ mode: 'neighbor_add', payload: data }))} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"><h5 className="font-semibold text-sm">{editingNeighbor ? 'Edit Neighbor' : state?.enabled ? 'Add Neighbor' : 'Enable BGP & Add Neighbor'}</h5><div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3"><Field label="Local AS" error={neighborForm.formState.errors.local_as?.message}><input type="number" {...neighborForm.register('local_as', { valueAsNumber: true })} className="input-field" /></Field><Field label="Router ID" error={neighborForm.formState.errors.router_id?.message}><input {...neighborForm.register('router_id')} className="input-field font-mono" /></Field><Field label="Neighbor IP" error={neighborForm.formState.errors.neighbor_ip?.message}><input {...neighborForm.register('neighbor_ip')} className="input-field font-mono" /></Field><Field label="Remote AS" error={neighborForm.formState.errors.remote_as?.message}><input type="number" {...neighborForm.register('remote_as', { valueAsNumber: true })} className="input-field" /></Field><Field label="Description"><input {...neighborForm.register('description')} className="input-field" /></Field></div><button type="submit" className="btn-primary btn-sm" disabled={isPreviewing}>{editingNeighbor ? 'Preview Update' : 'Preview Neighbor'}</button>{editingNeighbor && <button type="button" className="btn-secondary btn-sm ml-2" onClick={() => { setEditingNeighbor(null); neighborForm.reset() }}>Cancel</button>}</form>
    <div className="table-wrap overflow-auto"><table className="ds-table min-w-[600px]"><thead><tr><th>Advertised Network</th><th>Netmask</th><th className="text-right">Actions</th></tr></thead><tbody>{state?.networks.length ? state.networks.map((entry) => <tr key={`${entry.network}-${entry.subnet_mask}`}><td className="font-mono text-xs">{entry.network}</td><td className="font-mono text-xs">{entry.subnet_mask}</td><td className="text-right"><button type="button" className="btn-ghost btn-sm" onClick={() => { setEditingNetwork(entry); networkForm.reset(entry) }}>Edit</button><button type="button" className="btn-ghost btn-sm text-red-600" onClick={() => onPreview({ mode: 'network_remove', payload: entry })}>Delete</button></td></tr>) : <tr><td colSpan={3} className="text-center text-gray-500 py-8">ยังไม่มี advertised network</td></tr>}</tbody></table></div>
    <form onSubmit={networkForm.handleSubmit((data) => editingNetwork ? onPreview({ mode: 'network_update', current: editingNetwork, desired: data }) : onPreview({ mode: 'network_add', payload: data }))} className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"><h5 className="font-semibold text-sm">{editingNetwork ? 'Edit Advertised Network' : 'Add Advertised Network'}</h5><div className="grid grid-cols-1 md:grid-cols-3 gap-3"><Field label="Local AS" error={networkForm.formState.errors.local_as?.message}><input type="number" {...networkForm.register('local_as', { valueAsNumber: true })} className="input-field" disabled={!state?.enabled} /></Field><Field label="Network" error={networkForm.formState.errors.network?.message}><input {...networkForm.register('network')} className="input-field font-mono" disabled={!state?.enabled} /></Field><Field label="Netmask" error={networkForm.formState.errors.subnet_mask?.message}><input {...networkForm.register('subnet_mask')} className="input-field font-mono" disabled={!state?.enabled} /></Field></div>{previewError && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(previewError)}</div>}<button type="submit" className="btn-primary btn-sm" disabled={isPreviewing || !state?.enabled}>{editingNetwork ? 'Preview Update' : 'Preview Network'}</button>{editingNetwork && <button type="button" className="btn-secondary btn-sm ml-2" onClick={() => { setEditingNetwork(null); networkForm.reset() }}>Cancel</button>}</form>
  </div>
}

function ShowPanel({ selectedCommand, result, isLoading, error, onRun, onCopy, copied }: { selectedCommand: string; result: ShowResponse | null; isLoading: boolean; error: Error | null; onRun: (command: string) => void; onCopy: () => void; copied: boolean }) {
  return (
    <section className="card space-y-5">
      <div><h3 className="text-lg font-semibold">Show</h3><p className="text-sm text-gray-500">คำสั่งถูกจำกัดด้วย allowlist และไม่แก้ configuration</p></div>
      <div className="flex flex-wrap gap-2">{SHOW_COMMANDS.map((command) => <button key={command} type="button" onClick={() => onRun(command)} className={`btn-secondary btn-sm font-mono ${selectedCommand === command ? 'border-accent-DEFAULT text-accent-DEFAULT' : ''}`}>{command.replace('show ', '')}</button>)}</div>
      {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(error)}</div>}
      {isLoading && <LoadingState />}
      {result && !isLoading && <div className="space-y-3"><div className="flex items-center justify-between"><span className="badge badge-blue"><span className="badge-dot" />{result.command}</span><button type="button" className="btn-ghost btn-sm" onClick={onCopy}><Copy className="w-4 h-4" />{copied ? 'Copied' : 'Copy'}</button></div><pre className="terminal-area rounded-lg p-4 overflow-auto max-h-[480px] whitespace-pre-wrap">{result.output}</pre>{result.parsed && <div className="table-wrap overflow-auto"><table className="ds-table"><thead><tr>{Object.keys(result.parsed[0] ?? {}).map((key) => <th key={key}>{key}</th>)}</tr></thead><tbody>{result.parsed.map((row, index) => <tr key={index}>{Object.values(row).map((value, cellIndex) => <td key={cellIndex} className="font-mono text-xs">{value}</td>)}</tr>)}</tbody></table></div>}</div>}
    </section>
  )
}

function PreviewDrawer({ preview, applyResult, isApplying, error, onClose, onApply }: { preview: PreviewResponse; applyResult: ApplyResponse | null; isApplying: boolean; error: Error | null; onClose: () => void; onApply: () => void }) {
  return <><div className="drawer-overlay" onClick={onClose} /><aside className="drawer-panel" role="dialog" aria-modal="true" aria-label="Command Preview"><div className="p-5 border-b border-gray-200 flex items-center justify-between"><div><h3 className="font-semibold">Command Preview</h3><p className="text-xs text-gray-500 mt-1">หมดอายุ {new Date(preview.expires_at).toLocaleTimeString()}</p></div><button type="button" className="btn-icon hover:bg-gray-100" onClick={onClose} aria-label="ปิด"><X className="w-5 h-5" /></button></div><div className="p-5 flex-1 overflow-auto space-y-4"><div className="terminal-area rounded-lg p-4 text-sm space-y-1">{preview.commands.map((command, index) => <div key={`${command}-${index}`} className="flex gap-3"><span className="text-gray-500 select-none w-5 text-right">{index + 1}</span><code>{command}</code></div>)}</div><ul className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 list-disc list-inside">{preview.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>{error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{getApiMessage(error)}</div>}{applyResult && <div className={`rounded-lg border p-3 text-sm ${applyResult.overall_status === 'success' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}><p className="font-medium flex items-center gap-2">{applyResult.overall_status === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}สถานะ: {applyResult.overall_status}</p>{applyResult.results.map((item) => <div key={item.command} className="mt-2 font-mono text-xs">{item.status === 'success' ? '✓' : '✕'} {item.command}</div>)}</div>}</div><div className="p-5 border-t border-gray-200 flex gap-2"><button type="button" className="btn-secondary flex-1" onClick={onClose}>Cancel</button><button type="button" className="btn-primary flex-1 flex justify-center gap-2" disabled={isApplying || Boolean(applyResult)} onClick={onApply}>{isApplying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}Apply</button></div></aside></>
}

function ComingSoon({ title, detail }: { title: string; detail: string }) {
  return <section className="card py-16 text-center"><AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-3" /><h3 className="font-semibold text-gray-900">{title}</h3><p className="text-sm text-gray-500 mt-1">{detail}</p></section>
}
