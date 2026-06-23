import {
  useCallback,
  useEffect,
  useRef,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react'

const MIN_PANEL_WIDTH = 360
const MAX_PANEL_RATIO = 0.82
const RESIZE_HANDLE_WIDTH = 6
const STORAGE_KEY = 'diagram-panel-width'

function readStoredWidth(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return 520
    const parsed = Number.parseInt(raw, 10)
    return Number.isFinite(parsed) && parsed >= MIN_PANEL_WIDTH ? parsed : 520
  } catch {
    return 520
  }
}

type Props = {
  open: boolean
  width: number
  onWidthChange: (width: number) => void
  children: ReactNode
}

export function DiagramPanelShell({ open, width, onWidthChange, children }: Props) {
  const shellRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(Math.round(width)))
    } catch {
      /* ignore */
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

  const shellWidth = open ? width + RESIZE_HANDLE_WIDTH : 0

  return (
    <div
      ref={shellRef}
      className={`diagram-panel-shell${open ? ' diagram-panel-shell-open' : ''}`}
      style={{ width: shellWidth }}
    >
      {open && (
        <>
          <div
            className="diagram-resize-handle"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize diagram panel"
            style={{ width: RESIZE_HANDLE_WIDTH }}
            onPointerDown={onResizePointerDown}
            onPointerMove={onResizePointerMove}
            onPointerUp={onResizePointerUp}
            onPointerCancel={onResizePointerUp}
          />
          <div className="diagram-panel-content" style={{ width }}>
            {children}
          </div>
        </>
      )}
    </div>
  )
}

export { readStoredWidth as readDiagramPanelWidth }
