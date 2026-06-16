export type ArtifactKind = 'proposal_preview' | 'proposal_document'
export type ArtifactFormat = 'markdown'

export type ArtifactSpec = {
  kind: ArtifactKind
  title: string
  format: ArtifactFormat
  content: string
  filename: string
  artifact_id: string
  download_url?: string | null
  preview_truncated?: boolean
}
