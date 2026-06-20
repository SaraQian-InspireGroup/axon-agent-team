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

export function feeSectionHasIntro(section: Record<string, unknown>): boolean {
  const intro = section.intro
  return Boolean(intro) && typeof intro === 'object' && !Array.isArray(intro)
}
