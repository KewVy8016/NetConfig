import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, ChevronRight, Loader2, Save, Server, ShieldAlert, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useForm as useRHForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { Topbar } from '../components/shared/Topbar'
import { createNode, scanSubnet, testNodeConnectionDraft } from '../lib/api'
import type { ConnectionStep, ScanResult } from '../lib/api'

// --- Validation Schemas ---
const step1Schema = z.object({
  hostname: z.string().min(1, 'ระบุชื่ออุปกรณ์').max(64, 'ยาวเกินไป').regex(/^[a-zA-Z0-9_\-.]+$/, 'ใช้ได้แค่ตัวอักษร ตัวเลข _ - . เท่านั้น'),
  device_kind: z.enum(['router', 'switch']),
})

const transportSchema = z.discriminatedUnion('transport', [
  z.object({
    transport: z.literal('ssh'),
    host: z.string().min(1, 'ระบุ IP หรือ Hostname'),
    port: z.number().min(1).max(65535),
    username: z.string().min(1, 'ระบุชื่อผู้ใช้'),
    password: z.string().min(1, 'ระบุรหัสผ่าน'),
    secret: z.string().optional(),
  }),
  z.object({
    transport: z.literal('telnet'),
    host: z.string().min(1, 'ระบุ IP หรือ Hostname'),
    port: z.number().min(1).max(65535),
    username: z.string().max(64, 'ยาวเกินไป').optional(),
    password: z.string().min(1, 'ระบุรหัสผ่าน'),
    secret: z.string().optional(),
  }),
  z.object({
    transport: z.literal('serial'),
    serial_port: z.string().regex(/^(COM\d+|\/dev\/tty\w+)$/i, 'รูปแบบ COMx หรือ /dev/ttyXxx'),
    baudrate: z.number().min(1200).max(115200),
    username: z.string().max(64, 'ยาวเกินไป').optional(),
    password: z.string().max(128, 'ยาวเกินไป').optional(),
    secret: z.string().optional(),
  }),
])

type Step1Data = z.infer<typeof step1Schema>
type TransportData = z.infer<typeof transportSchema>

export function AddNodePage({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (v: boolean) => void }) {
  const [step, setStep] = useState(1)
  const [step1Data, setStep1Data] = useState<Step1Data | null>(null)
  const [transportData, setTransportData] = useState<TransportData | null>(null)
  
  const [testResults, setTestResults] = useState<ConnectionStep[]>([])
  const [testOverall, setTestOverall] = useState<'pending' | 'success' | 'failed' | 'skipped'>('pending')
  const [hostnameDetected, setHostnameDetected] = useState<string | null>(null)
  const [scanSubnetValue, setScanSubnetValue] = useState('192.168.8.128/28')
  
  const queryClient = useQueryClient()

  // --- Mutations ---
  const saveMutation = useMutation({
    mutationFn: createNode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: testNodeConnectionDraft,
    onSuccess: (data) => {
      setTestResults(data.steps)
      setTestOverall(data.overall_status)
      if (data.hostname_detected) {
        setHostnameDetected(data.hostname_detected)
      }
    },
  })
  const scanMutation = useMutation({ mutationFn: scanSubnet })

  const selectScanResult = (result: ScanResult, port: number) => {
    form2.setValue('transport', port === 22 ? 'ssh' : 'telnet')
    form2.setValue('host', result.host)
    form2.setValue('port', port)
  }

  // --- Step 1 Form ---
  const form1 = useRHForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: step1Data || { device_kind: 'router', hostname: '' },
  })

  // --- Step 2 Form ---
  const form2 = useRHForm<TransportData>({
    resolver: zodResolver(transportSchema),
    defaultValues: transportData || {
      transport: 'ssh',
      host: '',
      port: 22,
      username: '',
      password: '',
      secret: '',
    },
  })

  const transportType = form2.watch('transport')

  const onStep1Submit = (data: Step1Data) => {
    setStep1Data(data)
    setStep(2)
  }

  const onStep2Submit = (data: TransportData) => {
    setTransportData(data)
    setTestResults([])
    setTestOverall('pending')
    setHostnameDetected(null)
    testMutation.reset()
    saveMutation.reset()
    setStep(3)
  }

  const handleTest = () => {
    if (!step1Data || !transportData) return
    testMutation.mutate({
      hostname: step1Data.hostname,
      device_kind: step1Data.device_kind,
      transport_config: transportData,
    })
  }

  const handleSave = () => {
    if (!step1Data || !transportData || testOverall !== 'success') return
    saveMutation.mutate({
      hostname: step1Data.hostname,
      device_kind: step1Data.device_kind,
      transport_config: transportData,
    })
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Topbar 
        collapsed={collapsed} 
        setCollapsed={setCollapsed} 
        title="Add Node"
        breadcrumbs={<Link to="/" className="hover:text-accent-DEFAULT transition-colors">Nodes</Link>}
      />

      <main className="p-6 max-w-4xl mx-auto w-full">
        {/* Progress Tracker */}
        <div className="flex items-center mb-8 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <StepIndicator num={1} title="Device Info" active={step >= 1} current={step === 1} />
          <ChevronRight className="w-5 h-5 text-gray-300 mx-4 flex-shrink-0" />
          <StepIndicator num={2} title="Protocol" active={step >= 2} current={step === 2} />
          <ChevronRight className="w-5 h-5 text-gray-300 mx-4 flex-shrink-0" />
          <StepIndicator num={3} title="Test & Save" active={step >= 3} current={step === 3} />
        </div>

        <div className="card">
          {/* STEP 1 */}
          {step === 1 && (
            <form onSubmit={form1.handleSubmit(onStep1Submit)} className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Information</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Hostname (Alias)</label>
                  <input
                    {...form1.register('hostname')}
                    type="text"
                    className={`input-field ${form1.formState.errors.hostname ? 'input-error' : ''}`}
                    placeholder="e.g. R1-Core"
                    autoFocus
                  />
                  {form1.formState.errors.hostname && (
                    <p className="error-msg">{form1.formState.errors.hostname.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Device Type</label>
                  <select {...form1.register('device_kind')} className="select-field">
                    <option value="router">Router</option>
                    <option value="switch">Switch</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t border-gray-100">
                <button type="submit" className="btn-primary flex items-center gap-2">
                  Next Step <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <form onSubmit={form2.handleSubmit(onStep2Submit)} className="space-y-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Protocol Settings</h2>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-sm text-muted hover:text-gray-900 flex items-center gap-1"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>
              </div>

              {/* Protocol selector */}
              <div className="flex bg-gray-100 p-1 rounded-lg">
                <label className={`flex-1 text-center py-2 text-sm font-medium rounded-md cursor-pointer transition-colors ${transportType === 'ssh' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                  <input type="radio" value="ssh" {...form2.register('transport')} className="sr-only" 
                    onChange={() => { form2.setValue('transport', 'ssh'); form2.setValue('port', 22) }} 
                  />
                  SSH
                </label>
                <label className={`flex-1 text-center py-2 text-sm font-medium rounded-md cursor-pointer transition-colors ${transportType === 'telnet' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                  <input type="radio" value="telnet" {...form2.register('transport')} className="sr-only" 
                    onChange={() => { form2.setValue('transport', 'telnet'); form2.setValue('port', 23) }}
                  />
                  Telnet
                </label>
                <label className={`flex-1 text-center py-2 text-sm font-medium rounded-md cursor-pointer transition-colors ${transportType === 'serial' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                  <input type="radio" value="serial" {...form2.register('transport')} className="sr-only" 
                    onChange={() => { form2.setValue('transport', 'serial'); form2.setValue('baudrate', 9600) }}
                  />
                  Serial
                </label>
              </div>
              
              {transportType === 'telnet' && (
                <div className="bg-amber-50 border border-amber-200 text-amber-800 p-3 rounded-lg text-sm flex gap-2">
                  <ShieldAlert className="w-5 h-5 flex-shrink-0 text-amber-600" />
                  <p><strong>Warning:</strong> Telnet sends credentials in plain text. Use SSH if possible.</p>
                </div>
              )}

              {transportType !== 'serial' && <section className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3" aria-label="ค้นหาอุปกรณ์ใน subnet"><div className="flex flex-wrap items-end gap-2"><div className="flex-1 min-w-[220px]"><label className="block text-xs font-medium text-gray-700 mb-1">Scan management subnet (สูงสุด /28)</label><input value={scanSubnetValue} onChange={(event) => setScanSubnetValue(event.target.value)} className="input-field font-mono" placeholder="192.168.8.128/28" /></div><button type="button" className="btn-secondary btn-sm" onClick={() => scanMutation.mutate(scanSubnetValue)} disabled={scanMutation.isPending}>{scanMutation.isPending ? 'กำลังค้นหา...' : 'Scan SSH/Telnet'}</button></div><p className="text-xs text-gray-500">ตรวจเฉพาะ TCP 22 และ 23, ไม่ login และยังกรอก IP เองได้เสมอ</p>{scanMutation.error && <p role="alert" className="text-sm text-red-700">{(scanMutation.error as { message_th?: string }).message_th ?? 'ค้นหาไม่สำเร็จ'}</p>}{scanMutation.data && <div className="space-y-1 text-sm">{scanMutation.data.results.length ? scanMutation.data.results.map((result) => <div key={result.host} className="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 bg-white p-2"><code>{result.host}</code><span className="flex gap-1">{result.open_ports.map((port) => <button key={port} type="button" className="btn-ghost btn-sm" onClick={() => selectScanResult(result, port)}>Use {port === 22 ? 'SSH' : 'Telnet'}:{port}</button>)}</span></div>) : <p className="text-gray-500">ไม่พบ TCP 22/23 — ใช้ Manual IP ด้านล่างได้</p>}</div>}</section>}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {transportType !== 'serial' ? (
                  <>
                    <div className="md:col-span-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">IP Address / Hostname</label>
                      {/* @ts-ignore */}
                      <input {...form2.register('host')} type="text" className={`input-field ${form2.formState.errors.host ? 'input-error' : ''}`} placeholder="192.168.1.1" />
                      {/* @ts-ignore */}
                      {form2.formState.errors.host && <p className="error-msg">{form2.formState.errors.host.message}</p>}
                    </div>
                    <div className="md:col-span-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                      {/* @ts-ignore */}
                      <input {...form2.register('port', { valueAsNumber: true })} type="number" className={`input-field ${form2.formState.errors.port ? 'input-error' : ''}`} />
                      {/* @ts-ignore */}
                      {form2.formState.errors.port && <p className="error-msg">{form2.formState.errors.port.message}</p>}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="md:col-span-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">COM Port</label>
                      {/* @ts-ignore */}
                      <input {...form2.register('serial_port')} type="text" className={`input-field ${form2.formState.errors.serial_port ? 'input-error' : ''}`} placeholder="COM3" />
                      {/* @ts-ignore */}
                      {form2.formState.errors.serial_port && <p className="error-msg">{form2.formState.errors.serial_port.message}</p>}
                    </div>
                    <div className="md:col-span-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Baud Rate</label>
                      {/* @ts-ignore */}
                      <select {...form2.register('baudrate', { valueAsNumber: true })} className="select-field">
                        <option value="9600">9600</option>
                        <option value="115200">115200</option>
                      </select>
                    </div>
                  </>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username {(transportType === 'telnet' || transportType === 'serial') && <span className="text-gray-400 font-normal">(Optional)</span>}
                  </label>
                  <input {...form2.register('username')} type="text" className={`input-field ${form2.formState.errors.username ? 'input-error' : ''}`} />
                  {form2.formState.errors.username && <p className="error-msg">{form2.formState.errors.username.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password {transportType === 'serial' && <span className="text-gray-400 font-normal">(Optional)</span>}
                  </label>
                  <input {...form2.register('password')} type="password" className={`input-field ${form2.formState.errors.password ? 'input-error' : ''}`} />
                  {form2.formState.errors.password && <p className="error-msg">{form2.formState.errors.password.message}</p>}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Enable Secret <span className="text-gray-400 font-normal">(Optional)</span></label>
                  <input {...form2.register('secret')} type="password" className="input-field" placeholder="Leave empty if same as password" />
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t border-gray-100">
                <button type="submit" className="btn-primary flex items-center gap-2">
                  Next Step <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Test Connection & Save</h2>
                {!saveMutation.isPending && !testMutation.isPending && (
                  <button
                    onClick={() => setStep(2)}
                    className="text-sm text-muted hover:text-gray-900 flex items-center gap-1"
                  >
                    <ArrowLeft className="w-4 h-4" /> Back
                  </button>
                )}
              </div>

              {saveMutation.error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm mb-4">
                  {(saveMutation.error as any).message_th || 'เกิดข้อผิดพลาดในการบันทึก'}
                </div>
              )}
              {testMutation.error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm mb-4">
                  {(testMutation.error as any).message_th || 'ไม่สามารถทดสอบการเชื่อมต่อได้'}
                </div>
              )}

              {/* Action buttons */}
              {testResults.length === 0 && !testMutation.isPending && !saveMutation.isSuccess && (
                <div className="bg-gray-50 p-6 rounded-xl flex flex-col items-center justify-center text-center">
                  <Server className="w-12 h-12 text-gray-300 mb-4" />
                  <h3 className="font-medium text-gray-900 mb-2">ตรวจสอบก่อนบันทึก</h3>
                  <p className="text-gray-500 text-sm mb-6 max-w-sm">
                    ระบบจะทดสอบ Ping, Port, Login และ Hostname ผ่าน {transportData?.transport.toUpperCase()} ก่อนบันทึก Node หากไม่ผ่านจะไม่บันทึกข้อมูล
                  </p>
                  
                  <button 
                    onClick={handleTest}
                    disabled={testMutation.isPending}
                    className="btn-primary flex items-center gap-2 px-6 py-2.5"
                  >
                    {testMutation.isPending ? (
                      <><Loader2 className="w-5 h-5 animate-spin" /> กำลังทดสอบ...</>
                    ) : (
                      <><Server className="w-5 h-5" /> Test Connection</>
                    )}
                  </button>
                </div>
              )}

              {testMutation.isPending && (
                <div className="bg-blue-50 border border-blue-100 text-blue-800 p-4 rounded-lg text-sm flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" /> กำลังตรวจสอบการเชื่อมต่อ — ยังไม่มีการบันทึก Node
                </div>
              )}

              {/* Test Results */}
              {testResults.length > 0 && (
                <div className="space-y-3 mt-6">
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-2">Connection Log</h3>
                  <div className={`p-3 rounded-lg border ${testOverall === 'success' ? 'bg-green-50 border-green-100 text-green-800' : 'bg-red-50 border-red-100 text-red-800'}`}>
                    <p className="font-medium">ผลการทดสอบ: {testOverall === 'success' ? 'สำเร็จ' : 'ไม่สำเร็จ'}</p>
                    {hostnameDetected && <p className="text-sm mt-1">Hostname จากอุปกรณ์: {hostnameDetected}</p>}
                  </div>
                  
                  {testResults.map((res, i) => (
                    <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${
                      res.status === 'success' ? 'bg-green-50 border-green-100' :
                      res.status === 'failed' ? 'bg-red-50 border-red-100' :
                      res.status === 'pending' ? 'bg-blue-50 border-blue-100' :
                      'bg-gray-50 border-gray-100 opacity-60'
                    }`}>
                      {res.status === 'success' ? <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" /> :
                       res.status === 'failed' ? <XCircle className="w-5 h-5 text-red-600 mt-0.5" /> :
                       res.status === 'pending' ? <Loader2 className="w-5 h-5 text-blue-600 animate-spin mt-0.5" /> :
                       <div className="w-5 h-5 flex items-center justify-center mt-0.5"><div className="w-2 h-2 bg-gray-400 rounded-full" /></div>}
                      
                      <div>
                        <p className={`text-sm font-medium ${
                          res.status === 'success' ? 'text-green-800' :
                          res.status === 'failed' ? 'text-red-800' : 'text-gray-700'
                        }`}>
                          <span className="uppercase text-xs font-bold mr-2 opacity-70">[{res.step}]</span>
                          {res.message}
                        </p>
                        {res.detail && (
                          <p className="text-xs font-mono text-gray-500 mt-1 mt-1 break-all bg-white/50 p-1 rounded">
                            {res.detail}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Summary Footer */}
                  <div className="pt-6 flex flex-wrap items-center justify-end gap-3">
                    {testOverall === 'success' && !saveMutation.isSuccess && (
                      <button
                        onClick={handleSave}
                        disabled={saveMutation.isPending}
                        className="btn-primary flex items-center gap-2"
                      >
                        {saveMutation.isPending ? (
                          <><Loader2 className="w-4 h-4 animate-spin" /> กำลังบันทึก...</>
                        ) : (
                          <><Save className="w-4 h-4" /> Save Node</>
                        )}
                      </button>
                    )}
                    {testOverall !== 'success' && !saveMutation.isSuccess && (
                      <>
                        <p className="text-sm text-red-700 mr-auto">ทดสอบไม่ผ่าน จึงยังไม่บันทึก Node</p>
                        <button onClick={handleTest} className="btn-secondary">Retry Test</button>
                      </>
                    )}
                    {saveMutation.isSuccess && (
                      <Link to="/" className="btn-secondary">Return to Dashboard</Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function StepIndicator({ num, title, active, current }: { num: number, title: string, active: boolean, current: boolean }) {
  return (
    <div className={`flex items-center gap-3 ${active ? 'text-accent-DEFAULT' : 'text-gray-400'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
        current ? 'bg-accent-DEFAULT text-white ring-4 ring-blue-100' :
        active ? 'bg-accent-soft text-accent-DEFAULT' :
        'bg-gray-100 text-gray-400'
      }`}>
        {num}
      </div>
      <span className={`font-medium ${current ? 'text-gray-900' : ''}`}>{title}</span>
    </div>
  )
}
