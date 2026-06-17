import type { ArtifactSpec } from '../types/artifact'
import { MarkdownContent } from './MarkdownContent'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import { VizMaximizeIcon } from './VizMaximizeIcon'

type Props = {
  spec: ArtifactSpec
  expanded?: boolean
  onExpand?: (spec: ArtifactSpec) => void
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

export function ArtifactBubble({ spec, expanded = false, onExpand }: Props) {
  const isDocument = spec.kind === 'proposal_document'

  return (
    <div className={`viz-widget-frame artifact-widget-frame${expanded ? ' artifact-widget-frame-expanded' : ''}`}>
      <div className="viz-bubble-header">
        <h4 className="viz-bubble-title">{spec.title}</h4>
        <div className="viz-widget-toolbar">
          {isDocument && <span className="viz-bubble-badge">Download ready</span>}
          {spec.preview_truncated && !expanded && (
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
            className={`viz-widget-btn${expanded ? ' viz-widget-btn-active' : ''}`}
            aria-label={expanded ? 'Showing in side panel' : 'Open side panel'}
            title={expanded ? 'Open in side panel' : 'Open side panel'}
            aria-pressed={expanded}
            onClick={() => onExpand?.(spec)}
          >
            <VizMaximizeIcon />
          </button>
        </div>
      </div>
      <div className="viz-widget-body">
        <div className="artifact-markdown-wrap" style={{ maxHeight: PREVIEW_MAX_HEIGHT }}>
          <MarkdownContent
            content={spec.content}
            className="markdown-body artifact-markdown-body"
            allowHtml
          />
        </div>
      </div>
    </div>
  )
}
