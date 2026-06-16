import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ArtifactSpec } from '../types/artifact'
import { MarkdownContent } from './MarkdownContent'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import { VizCloseIcon } from './VizCloseIcon'
import { VizMaximizeIcon } from './VizMaximizeIcon'

type Props = {
  spec: ArtifactSpec
}

const PREVIEW_MAX_HEIGHT = 280

function downloadArtifact(spec: ArtifactSpec) {
  if (spec.download_url) {
    const link = document.createElement('a')
    link.href = spec.download_url
    link.download = spec.filename
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    link.remove()
    return
  }
  const blob = new Blob([spec.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = spec.filename || 'proposal.md'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function ArtifactBody({ spec, expanded = false }: { spec: ArtifactSpec; expanded?: boolean }) {
  return (
    <div
      className={`artifact-markdown-wrap${expanded ? ' artifact-markdown-wrap-expanded' : ''}`}
      style={expanded ? undefined : { maxHeight: PREVIEW_MAX_HEIGHT }}
    >
      <MarkdownContent content={spec.content} className="markdown-body artifact-markdown-body" />
    </div>
  )
}

function ArtifactMaximizeOverlay({ spec, onClose }: { spec: ArtifactSpec; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [onClose])

  return createPortal(
    <div className="viz-maximize-overlay" role="dialog" aria-modal="true" aria-label={spec.title}>
      <button type="button" className="viz-maximize-backdrop" aria-label="Close" onClick={onClose} />
      <div className="viz-maximize-panel artifact-maximize-panel">
        <div className="viz-maximize-header">
          <h3 className="viz-maximize-title">{spec.title}</h3>
          <div className="viz-widget-toolbar">
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Download"
              title="Download"
              onClick={() => downloadArtifact(spec)}
            >
              <ArtifactDownloadIcon />
            </button>
            <button type="button" className="viz-widget-btn" aria-label="Close" onClick={onClose}>
              <VizCloseIcon />
            </button>
          </div>
        </div>
        <div className="viz-widget-body viz-widget-body-expanded">
          <ArtifactBody spec={spec} expanded />
        </div>
      </div>
    </div>,
    document.body,
  )
}

export function ArtifactBubble({ spec }: Props) {
  const [maximized, setMaximized] = useState(false)
  const isDocument = spec.kind === 'proposal_document'

  return (
    <>
      <div className="viz-widget-frame artifact-widget-frame">
        <div className="viz-bubble-header">
          <h4 className="viz-bubble-title">{spec.title}</h4>
          <div className="viz-widget-toolbar">
            {isDocument && <span className="viz-bubble-badge">Download ready</span>}
            {spec.preview_truncated && !maximized && (
              <span className="viz-bubble-badge">Preview clipped</span>
            )}
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Download"
              title="Download"
              onClick={() => downloadArtifact(spec)}
            >
              <ArtifactDownloadIcon />
            </button>
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Maximize"
              title="Maximize"
              onClick={() => setMaximized(true)}
            >
              <VizMaximizeIcon />
            </button>
          </div>
        </div>
        <div className="viz-widget-body">
          <ArtifactBody spec={spec} />
        </div>
      </div>
      {maximized && (
        <ArtifactMaximizeOverlay spec={spec} onClose={() => setMaximized(false)} />
      )}
    </>
  )
}
