import { useCallback, useEffect, useRef, type MouseEvent as ReactMouseEvent } from 'react'

interface UsePanelResizeOptions {
  width: number
  onWidthChange: (width: number) => void
  minWidth: number
  maxWidth: number
  /** Dragging left edge of a right-side panel: moving left increases width. */
  edge: 'left' | 'right'
}

export function usePanelResize({
  width,
  onWidthChange,
  minWidth,
  maxWidth,
  edge,
}: UsePanelResizeOptions) {
  const draggingRef = useRef(false)
  const startXRef = useRef(0)
  const startWidthRef = useRef(width)

  const onResizeStart = useCallback(
    (event: ReactMouseEvent) => {
      event.preventDefault()
      draggingRef.current = true
      startXRef.current = event.clientX
      startWidthRef.current = width
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    },
    [width],
  )

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      if (!draggingRef.current) return

      const delta = event.clientX - startXRef.current
      const nextWidth =
        edge === 'left'
          ? startWidthRef.current - delta
          : startWidthRef.current + delta

      onWidthChange(Math.min(maxWidth, Math.max(minWidth, nextWidth)))
    }

    const onMouseUp = () => {
      if (!draggingRef.current) return
      draggingRef.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [edge, maxWidth, minWidth, onWidthChange])

  return { onResizeStart }
}
