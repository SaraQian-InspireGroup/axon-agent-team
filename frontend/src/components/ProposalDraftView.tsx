import { useEffect, useRef, useState } from 'react'
import {
  draftBlockKey,
  draftBlockTitle,
  draftExtraTopLevel,
  draftRecordList,
  draftSectionFlags,
  draftSectionKey,
  draftSections,
  draftSectionTitle,
  draftTopLevelEntries,
  feeSectionIntroBlock,
  feeSectionMetadata,
  formatDraftJson,
  isFeeSection,
  isMarkdownBlockNode,
  isMarkdownBlockSection,
  markdownBlockContent,
} from '../lib/proposalDraftView'
import { MarkdownContent } from './MarkdownContent'

type Props = {
  draft: Record<string, unknown>
}

function DraftSectionStatusBadges({
  enabled,
  required,
}: {
  enabled: boolean
  required: boolean
}) {
  return (
    <span className="proposal-draft-section-badges">
      <span
        className={`proposal-draft-bagel${enabled ? ' proposal-draft-bagel-true' : ''}`}
        aria-label={`enabled ${enabled}`}
      >
        enabled
      </span>
      <span
        className={`proposal-draft-bagel${required ? ' proposal-draft-bagel-true' : ''}`}
        aria-label={`required ${required}`}
      >
        required
      </span>
    </span>
  )
}

function DraftJsonInfoButton({ value }: { value: unknown }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLSpanElement>(null)
  const json = formatDraftJson(value)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  if (!json) return null

  return (
    <span ref={wrapRef} className="proposal-draft-json-info-wrap">
      <button
        type="button"
        className="proposal-draft-json-info-btn"
        aria-label="Show raw JSON"
        aria-expanded={open}
        title="Show raw JSON"
        onClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          setOpen((prev) => !prev)
        }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        i
      </button>
      {open ? (
        <div className="proposal-draft-json-info-popover" role="dialog" aria-label="Raw JSON">
          <pre className="proposal-state-json proposal-draft-section-json">{json}</pre>
        </div>
      ) : null}
    </span>
  )
}

function DraftSectionSummary({
  title,
  flags,
  infoValue,
}: {
  title: string
  flags?: { enabled: boolean; required: boolean }
  infoValue?: unknown
}) {
  return (
    <>
      <span className="proposal-draft-section-summary-title">{title}</span>
      {flags ? <DraftSectionStatusBadges enabled={flags.enabled} required={flags.required} /> : null}
      {infoValue !== undefined ? <DraftJsonInfoButton value={infoValue} /> : null}
    </>
  )
}

function DraftMarkdownBlockBody({ block }: { block: Record<string, unknown> }) {
  const content = markdownBlockContent(block)
  return (
    <div className="proposal-draft-markdown-block-body">
      {content.trim() ? (
        <MarkdownContent
          content={content}
          className="markdown-body proposal-draft-markdown-body"
        />
      ) : (
        <p className="proposal-draft-markdown-empty">No content</p>
      )}
    </div>
  )
}

function DraftBlockCollapsible({
  block,
  index,
}: {
  block: Record<string, unknown>
  index: number
}) {
  const title = draftBlockTitle(block, index)
  if (isMarkdownBlockNode(block)) {
    return (
      <details className="proposal-draft-section">
        <summary className="proposal-draft-section-summary">
          <DraftSectionSummary title={title} infoValue={block} />
        </summary>
        <DraftMarkdownBlockBody block={block} />
      </details>
    )
  }
  return <DraftJsonCollapsible title={title} value={block} />
}

function DraftJsonCollapsible({ title, value }: { title: string; value: unknown }) {
  const json = formatDraftJson(value)
  if (!json) return null
  return (
    <details className="proposal-draft-section">
      <summary className="proposal-draft-section-summary">
        <DraftSectionSummary title={title} infoValue={value} />
      </summary>
      <pre className="proposal-state-json proposal-draft-section-json">{json}</pre>
    </details>
  )
}

function DraftBlockGroup({
  label,
  blocks,
}: {
  label: string
  blocks: Record<string, unknown>[]
}) {
  if (blocks.length === 0) return null
  return (
    <section className="proposal-draft-sections-wrap proposal-draft-nested-group">
      <h4 className="proposal-draft-root-label">{label}</h4>
      <div className="proposal-draft-section-list proposal-draft-section-list-nested">
        {blocks.map((block, index) => (
          <DraftBlockCollapsible
            key={draftBlockKey(block, index)}
            block={block}
            index={index}
          />
        ))}
      </div>
    </section>
  )
}

function FeeSectionDraftView({ section }: { section: Record<string, unknown> }) {
  const metadata = feeSectionMetadata(section)
  const narratives = draftRecordList(section.narratives)
  const tables = draftRecordList(section.tables)
  const introBlock = feeSectionIntroBlock(section)

  return (
    <div className="proposal-draft-fee-section">
      {Object.keys(metadata).length > 0 ? (
        <DraftJsonCollapsible title="section config" value={metadata} />
      ) : null}
      {introBlock ? <DraftBlockCollapsible block={introBlock} index={0} /> : null}
      <DraftBlockGroup label="narratives" blocks={narratives} />
      <DraftBlockGroup label="Fees" blocks={tables} />
    </div>
  )
}

function DocumentSectionDraftView({
  section,
  index,
}: {
  section: Record<string, unknown>
  index: number
}) {
  const title = draftSectionTitle(section, index)
  const flags = draftSectionFlags(section)
  const summary = (
    <DraftSectionSummary title={title} flags={flags} infoValue={section} />
  )

  if (isFeeSection(section)) {
    return (
      <details className="proposal-draft-section">
        <summary className="proposal-draft-section-summary">{summary}</summary>
        <div className="proposal-draft-fee-section-wrap">
          <FeeSectionDraftView section={section} />
        </div>
      </details>
    )
  }

  if (isMarkdownBlockSection(section)) {
    return (
      <details className="proposal-draft-section">
        <summary className="proposal-draft-section-summary">{summary}</summary>
        <DraftMarkdownBlockBody block={section} />
      </details>
    )
  }

  const json = formatDraftJson(section)
  if (!json) return null
  return (
    <details className="proposal-draft-section">
      <summary className="proposal-draft-section-summary">{summary}</summary>
      <pre className="proposal-state-json proposal-draft-section-json">{json}</pre>
    </details>
  )
}

export function ProposalDraftView({ draft }: Props) {
  const topLevel = draftTopLevelEntries(draft)
  const extra = draftExtraTopLevel(draft)
  const sections = draftSections(draft)

  return (
    <div className="proposal-draft-view">
      <div className="proposal-draft-section-list">
        {topLevel.map(({ key, value }) => (
          <DraftJsonCollapsible key={key} title={key} value={value} />
        ))}

        {extra ? <DraftJsonCollapsible title="extra" value={extra} /> : null}
      </div>

      {sections.length > 0 ? (
        <section className="proposal-draft-sections-wrap">
          <h3 className="proposal-draft-root-label">sections</h3>
          <div className="proposal-draft-section-list">
            {sections.map((section, index) => (
              <DocumentSectionDraftView
                key={draftSectionKey(section, index)}
                section={section}
                index={index}
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
