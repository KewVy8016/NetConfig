// สถานะอุปกรณ์สื่อด้วยสี ไอคอน และข้อความ โดยคงความหมายเดิม
import { CircleCheck, CircleHelp, CircleX, LoaderCircle } from 'lucide-react'
type StatusType = 'connected' | 'unreachable' | 'checking' | 'unknown'

interface StatusBadgeProps {
  status: StatusType
  text?: string
}

export function StatusBadge({ status, text }: StatusBadgeProps) {
  const states = {
    connected: { style: 'badge-green', label: 'Connected', Icon: CircleCheck },
    unreachable: { style: 'badge-red', label: 'Unreachable', Icon: CircleX },
    checking: { style: 'badge-amber', label: 'Checking', Icon: LoaderCircle },
    unknown: { style: 'badge-gray', label: 'Unknown', Icon: CircleHelp },
  }
  const { style, label, Icon } = states[status]
  return <span className={`badge ${style}`}><Icon size={14} aria-hidden="true" />{text || label}</span>
}
