type StatusType = 'connected' | 'unreachable' | 'checking' | 'unknown'

interface StatusBadgeProps {
  status: StatusType
  text?: string
}

export function StatusBadge({ status, text }: StatusBadgeProps) {
  let badgeClass = 'badge-gray'
  let label = text || 'Unknown'

  switch (status) {
    case 'connected':
      badgeClass = 'badge-green'
      label = text || 'Connected'
      break
    case 'unreachable':
      badgeClass = 'badge-red'
      label = text || 'Unreachable'
      break
    case 'checking':
      badgeClass = 'badge-amber'
      label = text || 'Checking'
      break
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <span className="badge-dot" />
      {label}
    </span>
  )
}
