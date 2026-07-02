import { useEffect, useRef } from 'react'
import type { ChatSummary } from '../../types/agent'

interface NovaHistoryDropdownProps {
  open: boolean
  chats: ChatSummary[]
  activeChatId: string | null
  loading: boolean
  onClose: () => void
  onSelect: (chatId: string) => void
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const ts = new Date(iso).getTime()
  if (Number.isNaN(ts)) return ''

  const diffMs = Date.now() - ts
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`

  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  })
}

export default function NovaHistoryDropdown({
  open,
  chats,
  activeChatId,
  loading,
  onClose,
  onSelect,
}: NovaHistoryDropdownProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node
      if (panelRef.current && !panelRef.current.contains(target)) {
        onClose()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('mousedown', onPointerDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('mousedown', onPointerDown)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div ref={panelRef} className="nova-history-dropdown" role="menu" aria-label="最近会话">
      <div className="nova-history-dropdown-title">Recent chats</div>
      <div className="nova-history-dropdown-list">
        {loading ? <p className="nova-history-dropdown-empty">加载中…</p> : null}
        {!loading && chats.length === 0 ? (
          <p className="nova-history-dropdown-empty">暂无历史会话</p>
        ) : null}
        {!loading
          ? chats.map((chat) => {
              const active = chat.id === activeChatId
              return (
                <button
                  key={chat.id}
                  type="button"
                  role="menuitem"
                  className={`nova-history-dropdown-item${active ? ' nova-history-dropdown-item-active' : ''}`}
                  onClick={() => onSelect(chat.id)}
                >
                  <span className="nova-history-dropdown-item-title">
                    {chat.title || '新对话'}
                  </span>
                  <span className="nova-history-dropdown-item-time">
                    {formatRelativeTime(chat.updated_at ?? chat.created_at)}
                  </span>
                </button>
              )
            })
          : null}
      </div>
    </div>
  )
}
