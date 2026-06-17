import { useEffect } from 'react'
import { MarkdownContent } from './MarkdownContent'
import { ArtifactDownloadIcon } from './ArtifactDownloadIcon'
import type { ProposalPreview } from '../types/proposalPreview'

type Props = {
  open: boolean
  embedded?: boolean
  preview: ProposalPreview | null
  loading: boolean
  error: string | null
  onCollapse: () => void
  onRefresh: () => void
}

function downloadPreview(preview: ProposalPreview) {
  if (!preview.markdown) return
  const blob = new Blob([preview.markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = preview.filename || 'proposal.md'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function ProposalLivePanel({
  open,
  embedded = false,
  preview,
  loading,
  error,
  onCollapse,
  onRefresh,
}: Props) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCollapse()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onCollapse])

  const title = preview?.title || 'Proposal draft'
  const canDownload = Boolean(preview?.markdown)
  const missing = preview?.completeness.missing_required ?? []

  return (
    <aside
      className={`artifact-side-panel${open ? ' artifact-side-panel-open' : ''}${
        embedded ? ' artifact-side-panel-embedded' : ''
      }`}
      aria-hidden={!open}
      aria-label={title}
    >
      <div className="artifact-side-panel-inner">
        <div className="artifact-side-panel-header">
          <div className="proposal-live-panel-heading">
            <h2 className="artifact-side-panel-title" title={title}>
              {title}
            </h2>
            <p className="proposal-live-panel-subtitle">Current draft · live from state</p>
          </div>
          <div className="artifact-side-panel-actions">
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Refresh preview"
              title="Refresh"
              onClick={onRefresh}
              disabled={loading}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                <path d="M21 3v6h-6" />
              </svg>
            </button>
            <button
              type="button"
              className="viz-widget-btn"
              aria-label="Download draft"
              title="Download draft"
              onClick={() => preview && downloadPreview(preview)}
              disabled={!canDownload}
            >
              <ArtifactDownloadIcon />
            </button>
            <button
              type="button"
              className="viz-widget-btn artifact-side-panel-close"
              onClick={onCollapse}
              aria-label="Hide proposal draft"
              title="Hide"
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
          {loading && !preview?.markdown && (
            <p className="proposal-live-panel-placeholder">Loading proposal…</p>
          )}
          {error && <p className="proposal-live-panel-error">{error}</p>}
          {!loading && !error && preview?.status !== 'ok' && preview?.message && (
            <p className="proposal-live-panel-placeholder">{preview.message}</p>
          )}
          {!loading && !error && missing.length > 0 && (
            <p className="proposal-live-panel-hint">
              Draft preview — {missing.length} required field{missing.length === 1 ? '' : 's'}{' '}
              still open.
            </p>
          )}
          {preview?.markdown ? (
            <MarkdownContent
              content={preview.markdown}
              className="markdown-body artifact-markdown-body"
              allowHtml
            />
          ) : null}
        </div>
      </div>
    </aside>
  )
}
