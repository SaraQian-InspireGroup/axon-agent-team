import {
  draftBlockKey,
  draftBlockTitle,
  draftExtraTopLevel,
  draftRecordList,
  draftSectionKey,
  draftSections,
  draftSectionTitle,
  draftTopLevelEntries,
  feeSectionHasIntro,
  feeSectionMetadata,
  formatDraftJson,
  isFeeSection,
} from '../lib/proposalDraftView'

type Props = {
  draft: Record<string, unknown>
}

function DraftJsonCollapsible({ title, value }: { title: string; value: unknown }) {
  const json = formatDraftJson(value)
  if (!json) return null
  return (
    <details className="proposal-draft-section">
      <summary className="proposal-draft-section-summary">{title}</summary>
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
          <DraftJsonCollapsible
            key={draftBlockKey(block, index)}
            title={draftBlockTitle(block, index)}
            value={block}
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

  return (
    <div className="proposal-draft-fee-section">
      {Object.keys(metadata).length > 0 ? (
        <DraftJsonCollapsible title="section config" value={metadata} />
      ) : null}
      {feeSectionHasIntro(section) ? (
        <DraftJsonCollapsible title="intro" value={section.intro} />
      ) : null}
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
  if (isFeeSection(section)) {
    return (
      <details className="proposal-draft-section">
        <summary className="proposal-draft-section-summary">
          {draftSectionTitle(section, index)}
        </summary>
        <div className="proposal-draft-fee-section-wrap">
          <FeeSectionDraftView section={section} />
        </div>
      </details>
    )
  }

  return (
    <DraftJsonCollapsible title={draftSectionTitle(section, index)} value={section} />
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
