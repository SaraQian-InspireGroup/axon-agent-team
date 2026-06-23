import type { ArtifactSpec } from '../types/artifact'
import { copyArtifactSource, downloadArtifactFile, canDownloadDiagramPng } from '../lib/artifactDownload'
import { ArtifactCopyIcon } from './ArtifactCopyIcon'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import { VizMaximizeIcon } from './VizMaximizeIcon'

type Props = {
  spec: ArtifactSpec
  expanded?: boolean
  onExpand?: (spec: ArtifactSpec) => void
}

export function DiagramArtifactCard({ spec, expanded = false, onExpand }: Props) {
  const canCopySource = Boolean(spec.source?.trim())
  const canDownloadPng = canDownloadDiagramPng(spec)

  return (
    <div
      className={`diagram-artifact-card${expanded ? ' diagram-artifact-card-expanded' : ''}`}
      aria-label={spec.title}
    >
      <h4 className="diagram-artifact-card-title" title={spec.title}>
        {spec.title}
      </h4>
      <div className="diagram-artifact-card-actions" role="toolbar" aria-label="Diagram actions">
        <button
          type="button"
          className="diagram-artifact-action-btn"
          aria-label="Copy PlantUML source"
          title="Copy source"
          disabled={!canCopySource}
          onClick={() => void copyArtifactSource(spec)}
        >
          <ArtifactCopyIcon />
          <span>Copy</span>
        </button>
        <button
          type="button"
          className="diagram-artifact-action-btn"
          aria-label="Download PNG"
          title="Download PNG"
          disabled={!canDownloadPng}
          onClick={() => void downloadArtifactFile(spec, 'png')}
        >
          <ArtifactDownloadIcon />
          <span>PNG</span>
        </button>
        <button
          type="button"
          className="diagram-artifact-action-btn"
          aria-label="Download SVG"
          title="Download SVG"
          onClick={() => void downloadArtifactFile(spec, 'default')}
        >
          <ArtifactDownloadIcon />
          <span>SVG</span>
        </button>
        <button
          type="button"
          className={`diagram-artifact-action-btn${expanded ? ' diagram-artifact-action-btn-active' : ''}`}
          aria-label={expanded ? 'Showing in side panel' : 'Open preview panel'}
          title={expanded ? 'Open in side panel' : 'Open preview panel'}
          aria-pressed={expanded}
          onClick={() => onExpand?.(spec)}
        >
          <VizMaximizeIcon />
          <span>Preview</span>
        </button>
      </div>
    </div>
  )
}
