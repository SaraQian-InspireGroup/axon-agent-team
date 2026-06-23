import { useEffect } from 'react'
import { MarkdownContent } from './MarkdownContent'
import { DiagramArtifactViewer } from './DiagramArtifactViewer'
import { ArtifactCopyIcon } from './ArtifactCopyIcon'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import type { ArtifactSpec } from '../types/artifact'
import { copyArtifactSource, downloadArtifactFile, canDownloadDiagramPng } from '../lib/artifactDownload'

type Props = {
  open: boolean
  spec: ArtifactSpec | null
  embedded?: boolean
  onClose: () => void
}

export function ArtifactSidePanel({ open, spec, embedded = false, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  const panelClass = [
    'artifact-side-panel',
    open ? 'artifact-side-panel-open' : '',
    embedded ? 'artifact-side-panel-embedded' : '',
    embedded ? 'artifact-side-panel-shell-hosted' : '',
  ]
    .filter(Boolean)
    .join(' ')

  if (!spec) {
    return <aside className={panelClass} aria-hidden />
  }

  const isDiagram = spec.kind === 'diagram_svg'
  const canCopySource = Boolean(spec.source?.trim())
  const canDownloadPng = canDownloadDiagramPng(spec)

  return (
    <aside className={panelClass} aria-hidden={!open} aria-label={spec.title}>
      <div className="artifact-side-panel-inner">
        <div className="artifact-side-panel-header">
          <h2 className="artifact-side-panel-title" title={spec.title}>
            {spec.title}
          </h2>
          <div className="artifact-side-panel-actions">
            {canCopySource && (
              <button
                type="button"
                className="viz-widget-btn"
                aria-label="Copy source"
                title="Copy source"
                onClick={() => void copyArtifactSource(spec)}
              >
                <ArtifactCopyIcon />
              </button>
            )}
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Download SVG"
              title="Download SVG"
              onClick={() => void downloadArtifactFile(spec, 'default')}
            >
              <ArtifactDownloadIcon />
            </button>
            {canDownloadPng && (
              <button
                type="button"
                className="viz-widget-btn viz-widget-btn-text"
                aria-label="Download PNG"
                title="Download PNG"
                onClick={() => void downloadArtifactFile(spec, 'png')}
              >
                PNG
              </button>
            )}
            <button
              type="button"
              className="viz-widget-btn artifact-side-panel-close"
              onClick={onClose}
              aria-label="Close preview"
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
        <div className="artifact-side-panel-scroll artifact-side-panel-scroll-diagram">
          {isDiagram ? (
            <DiagramArtifactViewer spec={spec} />
          ) : (
            <MarkdownContent
              content={spec.content}
              className="markdown-body artifact-markdown-body"
              allowHtml
            />
          )}
        </div>
      </div>
    </aside>
  )
}
