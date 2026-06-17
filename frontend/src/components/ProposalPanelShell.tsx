import {
  useCallback,
  useEffect,
  useRef,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react'

const MIN_PANEL_WIDTH = 320
const MAX_PANEL_RATIO = 0.72
const RESIZE_HANDLE_WIDTH = 6
const STORAGE_KEY = 'proposal-panel-width'

function readStoredWidth(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return 480
    const parsed = Number.parseInt(raw, 10)
    return Number.isFinite(parsed) && parsed >= MIN_PANEL_WIDTH ? parsed : 480
  } catch {
    return 480
  }
}

type Props = {
  open: boolean
  width: number
  onWidthChange: (width: number) => void
  onExpand: () => void
  children: ReactNode
}

export function ProposalPanelShell({
  open,
  width,
  onWidthChange,
  onExpand,
  children,
}: Props) {
  const shellRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(Math.round(width)))
    } catch {
      /* ignore quota / private mode */
    }
  }, [width])

  const clampWidth = useCallback((next: number) => {
    const layout = shellRef.current?.parentElement
    const max = layout
      ? Math.max(MIN_PANEL_WIDTH, layout.getBoundingClientRect().width * MAX_PANEL_RATIO)
      : 960
    return Math.min(Math.max(next, MIN_PANEL_WIDTH), max)
  }, [])

  const onResizePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!open) return
    event.preventDefault()
    dragRef.current = { startX: event.clientX, startWidth: width }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const onResizePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return
    const delta = dragRef.current.startX - event.clientX
    onWidthChange(clampWidth(dragRef.current.startWidth + delta))
  }

  const onResizePointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return
    dragRef.current = null
    event.currentTarget.releasePointerCapture(event.pointerId)
  }

  const onTabClick = () => {
    if (!open) onExpand()
  }

  const shellWidth = open ? width + RESIZE_HANDLE_WIDTH : 0

  return (
    <div
      ref={shellRef}
      className={`proposal-preview-shell${open ? ' proposal-preview-shell-open' : ''}`}
      style={{ width: shellWidth }}
    >
      <button
        type="button"
        role="tab"
        id="proposal-tab-proposal"
        aria-selected={open}
        aria-controls={open ? 'proposal-panel-content' : undefined}
        className={`proposal-panel-tab${open ? ' proposal-panel-tab-active' : ''}`}
        onClick={onTabClick}
        aria-label={open ? 'Proposal preview' : 'Show proposal preview'}
        title={open ? 'Proposal preview' : 'Show proposal preview'}
      >
        Proposal
      </button>

      {open && (
        <>
          <div
            className="proposal-resize-handle"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize proposal preview"
            style={{ width: RESIZE_HANDLE_WIDTH }}
            onPointerDown={onResizePointerDown}
            onPointerMove={onResizePointerMove}
            onPointerUp={onResizePointerUp}
            onPointerCancel={onResizePointerUp}
          />
          <div
            id="proposal-panel-content"
            role="tabpanel"
            aria-labelledby="proposal-tab-proposal"
            className="proposal-panel-content"
            style={{ width }}
          >
            {children}
          </div>
        </>
      )}
    </div>
  )
}

export { readStoredWidth as readProposalPanelWidth }
