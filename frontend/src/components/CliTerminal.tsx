// เทอร์มินัล CLI สำหรับ Node ที่บันทึกไว้ ใช้ WebSocket session ชั่วคราว
// คำสั่งถูกส่งทีละบรรทัดและบันทึกผลการใช้งานใน History

import { AlertCircle, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

type SessionStatus = 'connecting' | 'connected' | 'disconnected'
type CliMessage = {
  type: 'ready' | 'result' | 'error'
  prompt?: string
  output?: string
  message?: string
  password_prompt?: boolean
  status?: 'success' | 'failed'
}

/** แสดง prompt/output, ประวัติคำสั่ง ↑↓ และปุ่มจัดการ session โดยไม่เก็บรหัสในประวัติคำสั่ง */
export function CliTerminal({ nodeId, hostname, endpoint, transport, onCommandResult }: { nodeId: string; hostname: string; endpoint: string; transport: string; onCommandResult: () => void }) {
  const socketRef = useRef<WebSocket | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const commandHistory = useRef<string[]>([])
  const historyIndex = useRef(-1)
  const [attempt, setAttempt] = useState(0)
  const [status, setStatus] = useState<SessionStatus>('connecting')
  const [prompt, setPrompt] = useState('>')
  const [input, setInput] = useState('')
  const [passwordPrompt, setPasswordPrompt] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [lines, setLines] = useState<string[]>([])
  const [error, setError] = useState('')
  const outputRef = useRef<HTMLPreElement>(null)
  const onCommandResultRef = useRef(onCommandResult)
  useEffect(() => { onCommandResultRef.current = onCommandResult }, [onCommandResult])

  useEffect(() => {
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${scheme}//${window.location.host}/nodes/${encodeURIComponent(nodeId)}/cli`)
    socketRef.current = socket
    socket.onmessage = (event: MessageEvent<string>) => {
      if (socketRef.current !== socket) return
      const message = JSON.parse(event.data) as CliMessage
      if (message.type === 'ready') {
        setStatus('connected')
        setPrompt(message.prompt ?? '>')
        setError('')
        inputRef.current?.focus()
      } else if (message.type === 'result') {
        setWaiting(false)
        setPrompt(message.prompt ?? '>')
        setPasswordPrompt(Boolean(message.password_prompt))
        if (message.output) setLines((current) => [...current, message.output ?? ''])
        setError(message.status === 'failed' ? 'อุปกรณ์ปฏิเสธคำสั่ง ตรวจผลลัพธ์ใน terminal' : '')
        onCommandResultRef.current()
        inputRef.current?.focus()
      } else {
        setWaiting(false)
        setError(message.message ?? 'CLI เกิดข้อผิดพลาด')
      }
    }
    socket.onerror = () => {
      if (socketRef.current === socket) setError((current) => current || 'เชื่อมต่อ CLI ไม่สำเร็จ กรุณาตรวจสอบ backend และอุปกรณ์')
    }
    socket.onclose = (event) => {
      if (socketRef.current !== socket) return
      setStatus('disconnected')
      setWaiting(false)
      if (event.code !== 1000) setError((current) => current || 'Session CLI หลุด กรุณากด Reconnect')
      socketRef.current = null
    }
    return () => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action: 'disconnect' }))
      socket.close()
      if (socketRef.current === socket) socketRef.current = null
    }
  }, [nodeId, attempt])

  useEffect(() => { outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight }) }, [lines])

  const send = () => {
    const command = input.trim()
    if (!command || waiting || status !== 'connected') return
    if (command.length > 256 || /[\r\n\0]/.test(command)) {
      setError('พิมพ์คำสั่งหนึ่งบรรทัด ความยาวไม่เกิน 256 ตัวอักษร')
      return
    }
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setStatus('disconnected')
      setError('Session CLI หลุด กรุณากด Reconnect')
      return
    }
    const masked = passwordPrompt || /\b(?:password|secret)\b/i.test(command)
    try {
      socket.send(JSON.stringify({ command }))
    } catch {
      setStatus('disconnected')
      setError('ส่งคำสั่งไม่สำเร็จ กรุณากด Reconnect')
      return
    }
    if (!masked) commandHistory.current.push(command)
    historyIndex.current = -1
    setLines((current) => [...current, `${prompt} ${masked ? '••••' : command}`])
    setInput('')
    setPasswordPrompt(false)
    setError('')
    setWaiting(true)
  }

  const onInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') { event.preventDefault(); send(); return }
    if (event.key === 'Escape') { setInput(''); return }
    if (passwordPrompt || commandHistory.current.length === 0) return
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      historyIndex.current = Math.min(historyIndex.current + 1, commandHistory.current.length - 1)
      setInput(commandHistory.current[commandHistory.current.length - 1 - historyIndex.current])
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      historyIndex.current = Math.max(historyIndex.current - 1, -1)
      setInput(historyIndex.current < 0 ? '' : commandHistory.current[commandHistory.current.length - 1 - historyIndex.current])
    }
  }

  const reconnect = () => {
    setStatus('connecting')
    setError('')
    setInput('')
    setPasswordPrompt(false)
    setAttempt((current) => current + 1)
  }

  return <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm" aria-label="CLI Terminal">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-5 py-4">
      <div>
        <h3 className="text-base font-semibold text-slate-900">Device CLI</h3>
        <p className="mt-0.5 font-mono text-xs text-slate-500">{hostname} <span className="mx-1 text-slate-300">/</span> {transport.toUpperCase()} <span className="mx-1 text-slate-300">/</span> {endpoint}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span role="status" className={`badge ${status === 'connected' ? 'badge-green' : status === 'connecting' ? 'badge-amber' : 'badge-gray'}`}><span className="badge-dot" />{status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting' : 'Disconnected'}</span>
        <span className="mx-1 hidden h-5 w-px bg-gray-200 sm:block" aria-hidden="true" />
        <button type="button" className="btn-ghost btn-sm disabled:cursor-not-allowed disabled:opacity-40" onClick={() => navigator.clipboard.writeText(lines.join('\n'))} disabled={lines.length === 0}>Copy</button>
        <button type="button" className="btn-ghost btn-sm disabled:cursor-not-allowed disabled:opacity-40" onClick={() => setLines([])} disabled={lines.length === 0}>Clear</button>
        {status === 'disconnected'
          ? <button type="button" className="btn-secondary btn-sm" onClick={reconnect}>Reconnect</button>
          : <button type="button" className="btn-secondary btn-sm" onClick={() => socketRef.current?.send(JSON.stringify({ action: 'disconnect' }))} disabled={status !== 'connected'}>Disconnect</button>}
      </div>
    </header>

    <div className="flex items-start gap-2 border-b border-amber-100 bg-amber-50 px-5 py-2.5 text-xs text-amber-900">
      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>คำสั่ง CLI ส่งทันที ไม่มี Preview · การบันทึกถาวรใช้ Save Config แยกต่างหาก</span>
    </div>

    <div className="bg-[var(--terminal-bg)] text-[var(--terminal-text)]">
      <pre ref={outputRef} role="log" aria-live="polite" aria-label="ผลลัพธ์ CLI" className="h-[min(52vh,560px)] min-h-80 overflow-auto px-5 py-5 font-mono text-[13px] leading-6 whitespace-pre-wrap break-words">{lines.join('\n') || (status === 'connected' ? 'พร้อมรับคำสั่ง' : status === 'connecting' ? 'กำลังเชื่อมต่ออุปกรณ์…' : 'ไม่มีการเชื่อมต่อ')}</pre>
      {error && <p role="alert" className="flex items-center gap-2 border-t border-red-900/50 bg-red-950/40 px-5 py-2 text-xs text-red-200"><AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />{error}</p>}
      <div className="flex items-center gap-3 border-t border-slate-700 px-5 py-3">
        <label htmlFor="cli-command" className="shrink-0 font-mono text-sm text-green-400">{prompt}</label>
        <input ref={inputRef} id="cli-command" className="min-w-0 flex-1 rounded-sm bg-transparent font-mono text-sm text-slate-100 outline-none placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-blue-400 disabled:cursor-not-allowed disabled:opacity-50" type={passwordPrompt ? 'password' : 'text'} autoComplete="off" autoCapitalize="off" spellCheck={false} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={onInputKeyDown} disabled={status !== 'connected' || waiting} placeholder={passwordPrompt ? 'Enable password' : status === 'connected' ? 'พิมพ์คำสั่ง IOS' : 'เชื่อมต่อก่อนส่งคำสั่ง'} />
        <button type="button" className="rounded-md border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-400 hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-blue-400 disabled:cursor-not-allowed disabled:opacity-40" onClick={send} disabled={status !== 'connected' || waiting || !input.trim()}>{waiting ? <Loader2 className="h-4 w-4 animate-spin" aria-label="กำลังรอผล" /> : 'Send ↵'}</button>
      </div>
    </div>

    <footer className="flex flex-wrap items-center justify-between gap-1 px-5 py-2.5 text-xs text-slate-500">
      <span>ผลคำสั่งถูกบันทึกใน History โดยไม่เก็บเนื้อหา CLI</span>
      <span className="font-mono">Enter ส่ง · ↑↓ ย้อนคำสั่ง · Esc ล้างช่องพิมพ์</span>
    </footer>
  </section>
}
