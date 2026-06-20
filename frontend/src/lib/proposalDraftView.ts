const TOP_LEVEL_KEYS = ['version', 'meta', 'facts'] as const

export type DraftTopLevelKey = (typeof TOP_LEVEL_KEYS)[number]

export function formatDraftJson(value: unknown): string {
  if (value === undefined) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function draftTopLevelEntries(
  draft: Record<string, unknown>,
): Array<{ key: DraftTopLevelKey; value: unknown }> {
  return TOP_LEVEL_KEYS.filter((key) => key in draft).map((key) => ({
    key,
    value: draft[key],
  }))
}

export function draftExtraTopLevel(draft: Record<string, unknown>): Record<string, unknown> | null {
  const extra: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(draft)) {
    if (TOP_LEVEL_KEYS.includes(key as DraftTopLevelKey) || key === 'document') continue
    extra[key] = value
  }
  return Object.keys(extra).length > 0 ? extra : null
}

export function draftSections(draft: Record<string, unknown>): Record<string, unknown>[] {
  const document = draft.document
  if (!document || typeof document !== 'object' || Array.isArray(document)) return []
  const sections = (document as Record<string, unknown>).sections
  if (!Array.isArray(sections)) return []
  return sections.filter(
    (section): section is Record<string, unknown> =>
      Boolean(section) && typeof section === 'object' && !Array.isArray(section),
  )
}

export function draftSectionTitle(section: Record<string, unknown>, index: number): string {
  const title = section.title
  if (typeof title === 'string' && title.trim()) return title.trim()
  const id = section.id
  if (typeof id === 'string' && id.trim()) return id.trim()
  return `Section ${index + 1}`
}

export function draftSectionFlags(section: Record<string, unknown>): {
  enabled: boolean
  required: boolean
} {
  return {
    enabled: section.enabled === true,
    required: section.required === true,
  }
}

export function draftSectionKey(section: Record<string, unknown>, index: number): string {
  const id = section.id
  if (typeof id === 'string' && id.trim()) return id.trim()
  return `section-${index}`
}

export function isFeeSection(section: Record<string, unknown>): boolean {
  return section.kind === 'fee_section'
}

export function isMarkdownBlockNode(node: Record<string, unknown>): boolean {
  const kind = node.kind
  return kind === 'markdown_block' || kind === 'package_narrative'
}

/** Document-level markdown section (same shape as fee_section.narratives[] items). */
export function isMarkdownBlockSection(section: Record<string, unknown>): boolean {
  return isMarkdownBlockNode(section)
}

export function markdownBlockContent(section: Record<string, unknown>): string {
  const content = section.content
  return typeof content === 'string' ? content : ''
}

export function draftBlockTitle(block: Record<string, unknown>, index: number): string {
  const title = block.title
  if (typeof title === 'string' && title.trim()) return title.trim()
  const id = block.id
  if (typeof id === 'string' && id.trim()) return id.trim()
  return `Item ${index + 1}`
}

export function draftBlockKey(block: Record<string, unknown>, index: number): string {
  const id = block.id
  if (typeof id === 'string' && id.trim()) return id.trim()
  return `block-${index}`
}

export function draftRecordList(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return []
  return value.filter(
    (item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === 'object' && !Array.isArray(item),
  )
}

export function feeSectionMetadata(section: Record<string, unknown>): Record<string, unknown> {
  const metadata: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(section)) {
    if (key === 'intro' || key === 'narratives' || key === 'tables') continue
    metadata[key] = value
  }
  return metadata
}

export function feeSectionIntroBlock(section: Record<string, unknown>): Record<string, unknown> | null {
  const intro = section.intro
  if (!intro || typeof intro !== 'object' || Array.isArray(intro)) return null
  const block = intro as Record<string, unknown>
  if (isMarkdownBlockNode(block)) return block

  const content = typeof block.content === 'string' ? block.content : ''
  const source = block.source
  const hasSource = Boolean(source) && typeof source === 'object' && !Array.isArray(source)
  if (!content.trim() && !hasSource) return null

  const legacyEditState = block.edit_state
  let contentEditState = 'empty'
  if (typeof legacyEditState === 'object' && legacyEditState && !Array.isArray(legacyEditState)) {
    contentEditState = String((legacyEditState as Record<string, unknown>).content || 'empty')
  } else if (legacyEditState === 'source' || content.trim()) {
    contentEditState = 'source'
  }

  return {
    id: typeof block.id === 'string' ? block.id : 'intro',
    kind: 'markdown_block',
    title: typeof block.title === 'string' ? block.title : 'Intro',
    content,
    source: hasSource ? source : {},
    policy: {
      editable: block.editable !== false,
      removable: false,
    },
    edit_state: { content: contentEditState },
  }
}

export function feeSectionHasIntro(section: Record<string, unknown>): boolean {
  return feeSectionIntroBlock(section) !== null
}

export function isFeeTableBlock(block: Record<string, unknown>): boolean {
  return block.kind === 'fee_table'
}

export function feeTablePackageId(table: Record<string, unknown>): string | null {
  const source = table.source
  if (!source || typeof source !== 'object' || Array.isArray(source)) return null
  const packageId = (source as Record<string, unknown>).package_id
  return typeof packageId === 'string' && packageId.trim() ? packageId.trim() : null
}

export type FeeRowSummary = {
  id: string
  sku: string
  label: string
  amount: string | null
  description: string | null
  sow: string | null
  department: string | null
  footnote: string | null
  pricingType: string | null
  billingFrequency: string | null
}

export function formatBillingFrequencyLabel(frequency: string): string {
  const normalized = frequency.trim().toUpperCase()
  const labels: Record<string, string> = {
    ONE_TIME: 'one-time',
    MONTHLY: 'monthly',
    QUARTERLY: 'quarterly',
    ANNUALLY: 'annually',
  }
  return labels[normalized] ?? frequency.trim().toLowerCase().replace(/_/g, ' ')
}

function formatDraftMoney(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${currency} ${amount.toFixed(2)}`
  }
}

export function summarizeFeeRow(row: Record<string, unknown>): FeeRowSummary {
  const source =
    row.source && typeof row.source === 'object' && !Array.isArray(row.source)
      ? (row.source as Record<string, unknown>)
      : {}
  const price =
    row.price && typeof row.price === 'object' && !Array.isArray(row.price)
      ? (row.price as Record<string, unknown>)
      : {}

  const sku = typeof source.sku === 'string' ? source.sku.trim() : ''
  const serviceName = typeof row.service_name === 'string' ? row.service_name.trim() : ''
  const description = typeof row.description === 'string' ? row.description.trim() : ''
  const sow = typeof row.scope_of_work === 'string' ? row.scope_of_work.trim() : ''
  const label = serviceName || description || sku || String(row.id || 'Row')

  const currency = typeof price.currency === 'string' && price.currency.trim() ? price.currency : 'USD'
  let amount: string | null = null
  if (typeof price.amount === 'number' && !Number.isNaN(price.amount)) {
    amount = formatDraftMoney(price.amount, currency)
  } else if (typeof price.fee_raw === 'string' && price.fee_raw.trim()) {
    amount = price.fee_raw.trim()
  }

  const footnote =
    typeof row.footnotes === 'string' && row.footnotes.trim() ? row.footnotes.trim() : null
  const department =
    typeof row.department_team === 'string' && row.department_team.trim()
      ? row.department_team.trim()
      : null
  const pricingType =
    typeof price.pricing_type === 'string' && price.pricing_type.trim()
      ? price.pricing_type.trim()
      : null
  const billingFrequency =
    typeof price.frequency === 'string' && price.frequency.trim()
      ? price.frequency.trim()
      : typeof row.billing_frequency === 'string' && row.billing_frequency.trim()
        ? row.billing_frequency.trim()
        : null

  return {
    id: typeof row.id === 'string' ? row.id : sku || label,
    sku,
    label,
    amount,
    description: description || null,
    sow: sow || null,
    department,
    footnote,
    pricingType,
    billingFrequency,
  }
}

export function collectFeeTableFootnotes(rows: Record<string, unknown>[]): string[] {
  const seen = new Set<string>()
  const notes: string[] = []
  for (const row of rows) {
    const note = typeof row.footnotes === 'string' ? row.footnotes.trim() : ''
    if (!note || seen.has(note)) continue
    seen.add(note)
    notes.push(note)
  }
  return notes
}
