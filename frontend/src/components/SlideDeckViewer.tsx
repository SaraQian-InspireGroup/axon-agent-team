import { useEffect, useState, type SyntheticEvent } from 'react'
import type { ArtifactSpec } from '../types/artifact'
import { LoadingSpinner } from './LoadingSpinner'

type Props = {
  spec: ArtifactSpec
}

/** Slidev router breaks when the iframe URL ends with /index.html — use /preview/ instead. */
export function normalizeSlidePreviewUrl(url: string): string {
  const trimmed = url.trim()
  if (!trimmed) return trimmed
  return trimmed.replace(/\/index\.html\/?$/i, '/')
}

export function SlideDeckViewer({ spec }: Props) {
  const previewUrl = spec.preview_url ? normalizeSlidePreviewUrl(spec.preview_url) : null
  const [iframeState, setIframeState] = useState<'loading' | 'ready' | 'error'>(
    previewUrl ? 'loading' : 'ready',
  )

  useEffect(() => {
    setIframeState(previewUrl ? 'loading' : 'ready')
  }, [previewUrl])

  const handleIframeLoad = (event: SyntheticEvent<HTMLIFrameElement>) => {
    const iframe = event.currentTarget
    try {
      const bodyText = iframe.contentDocument?.body?.innerText ?? ''
      if (/\b404\b/.test(bodyText) && /not found/i.test(bodyText)) {
        setIframeState('error')
        return
      }
    } catch {
      // Cross-origin iframe — cannot inspect document.
    }
    setIframeState('ready')
  }

  if (previewUrl) {
    return (
      <div className="slide-deck-viewer-wrap">
        {iframeState === 'loading' ? (
          <div className="slide-deck-viewer-loading" aria-live="polite">
            <LoadingSpinner size="lg" />
            <p className="panel-loading-caption">Loading slide preview…</p>
          </div>
        ) : null}
        {iframeState === 'error' ? (
          <div className="slide-deck-viewer-error" role="alert">
            <p>Slide preview failed to load.</p>
            <p className="panel-loading-caption">Try re-running render_slidev or open Download for the source.</p>
          </div>
        ) : null}
        <iframe
          className="slide-deck-viewer"
          title={spec.title}
          src={previewUrl}
          sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
          referrerPolicy="no-referrer"
          aria-hidden={iframeState === 'error'}
          onLoad={handleIframeLoad}
          onError={() => setIframeState('error')}
        />
      </div>
    )
  }

  if (!spec.content) {
    return (
      <div className="panel-loading-state">
        <p>Slide preview is not available yet.</p>
      </div>
    )
  }

  return (
    <pre className="slide-deck-source-fallback">{spec.content}</pre>
  )
}
