import { useEffect } from 'react'
import { MarkdownContent } from './MarkdownContent'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import type { ArtifactSpec } from '../types/artifact'

type Props = {
  open: boolean
  spec: ArtifactSpec | null
  onClose: () => void
}

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

export function ArtifactSidePanel({ open, spec, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!spec) {
    return (
      <aside
        className={`artifact-side-panel${open ? ' artifact-side-panel-open' : ''}`}
        aria-hidden
      />
    )
  }

  return (
    <aside
      className={`artifact-side-panel${open ? ' artifact-side-panel-open' : ''}`}
      aria-hidden={!open}
      aria-label={spec.title}
    >
      <div className="artifact-side-panel-inner">
        <div className="artifact-side-panel-header">
          <h2 className="artifact-side-panel-title" title={spec.title}>
            {spec.title}
          </h2>
          <div className="artifact-side-panel-actions">
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
              className="viz-widget-btn artifact-side-panel-close"
              onClick={onClose}
              aria-label="Close proposal preview"
              title="Close"
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden
              >
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="artifact-side-panel-scroll">
          <MarkdownContent
            content={spec.content}
            className="markdown-body artifact-markdown-body"
            allowHtml
          />
        </div>
      </div>
    </aside>
  )
}
