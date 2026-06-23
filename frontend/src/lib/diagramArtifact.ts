import type { ArtifactSpec } from '../types/artifact'

export function isDiagramArtifact(spec: ArtifactSpec): boolean {
  return spec.kind === 'diagram_svg'
}

export function isProposalArtifact(spec: ArtifactSpec): boolean {
  return spec.kind.startsWith('proposal_')
}

/** PNG download URL — uses explicit field or derives from SVG URL. */
export function resolvePngDownloadUrl(spec: ArtifactSpec): string | null {
  if (!isDiagramArtifact(spec)) return null
  if (spec.png_download_url) return spec.png_download_url
  if (!spec.download_url) return null
  const joiner = spec.download_url.includes('?') ? '&' : '?'
  return `${spec.download_url}${joiner}format=png`
}

export function canDownloadDiagramPng(spec: ArtifactSpec): boolean {
  return Boolean(resolvePngDownloadUrl(spec))
}

export function resolvePngFilename(spec: ArtifactSpec): string {
  if (spec.png_filename) return spec.png_filename
  return spec.filename.replace(/\.svg$/i, '.png')
}
