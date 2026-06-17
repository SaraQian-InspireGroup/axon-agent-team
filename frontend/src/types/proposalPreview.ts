export type ProposalPreviewStatus = 'ok' | 'empty' | 'blocked' | 'error'

export type ProposalCompleteness = {
  missing_required: string[]
  ready_to_preview: boolean
  ready_to_generate: boolean
}

export type ProposalPreview = {
  chat_id?: string
  status: ProposalPreviewStatus
  title: string
  markdown: string
  filename: string
  state_fingerprint: string
  message?: string | null
  completeness: ProposalCompleteness
}
