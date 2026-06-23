import type { ArtifactSpec } from '../types/artifact'
import { downloadBinaryUrl } from './downloadBinaryUrl'
import {
  canDownloadDiagramPng,
  isDiagramArtifact,
  isProposalArtifact,
  resolvePngDownloadUrl,
  resolvePngFilename,
} from './diagramArtifact'

function isProposalWord(spec: ArtifactSpec): boolean {
  return (
    spec.kind === 'proposal_word' ||
    spec.format === 'docx' ||
    spec.filename.toLowerCase().endsWith('.docx')
  )
}

export async function downloadArtifactFile(
  spec: ArtifactSpec,
  variant: 'default' | 'png' = 'default',
): Promise<void> {
  const url =
    variant === 'png' ? resolvePngDownloadUrl(spec) : spec.download_url
  const filename =
    variant === 'png' ? resolvePngFilename(spec) : spec.filename

  if (url) {
    if (isProposalWord(spec) || variant === 'png') {
      await downloadBinaryUrl(url, filename)
      return
    }
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    link.remove()
    return
  }

  if (variant === 'png') return

  const mime = isDiagramArtifact(spec) ? 'image/svg+xml;charset=utf-8' : 'text/markdown;charset=utf-8'
  const blob = new Blob([spec.content], { type: mime })
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename || 'artifact'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(blobUrl)
}

export async function copyArtifactSource(spec: ArtifactSpec): Promise<void> {
  const text = spec.source?.trim()
  if (!text) return
  await navigator.clipboard.writeText(text)
}

export { canDownloadDiagramPng, isDiagramArtifact, isProposalArtifact }
