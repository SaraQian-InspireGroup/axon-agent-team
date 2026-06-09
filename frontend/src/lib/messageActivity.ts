import type { Message } from '../types'

export type ActivityEntry = {
  id: string
  kind: 'reasoning' | 'tool' | 'mcp' | 'skill'
  title: string
  detail: string
  status: 'running' | 'done' | 'error' | 'cancelled'
}

export type ChatBlock =
  | { kind: 'bubble'; message: Message }
  | { kind: 'process'; id: string; item: ActivityEntry }

const PROCESS_SEPARATOR = '\n\n---\n\n'
const REASONING_TITLE = 'Reasoning'

function formatDetail(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    ) {
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2)
      } catch {
        return value
      }
    }
    return value
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function toolNameFromMessage(message: Message): string {
  const meta = message.metadata ?? {}
  const name = meta.tool_name ?? meta.name
  return name != null && String(name).trim() ? String(name).trim() : 'unknown'
}

function inferKind(messageType: string): ActivityEntry['kind'] {
  if (messageType.startsWith('skill_')) return 'skill'
  if (messageType === 'mcp_call' || messageType === 'mcp_result') return 'mcp'
  return 'tool'
}

function resultLooksLikeError(result: unknown): boolean {
  if (result == null) return false
  if (typeof result === 'string') {
    return result.toLowerCase().includes('error') || result.includes('not allowed')
  }
  if (typeof result === 'object') {
    const obj = result as Record<string, unknown>
    return typeof obj.error === 'string'
  }
  return false
}

function isEmptyDetail(value: string): boolean {
  const trimmed = value.trim()
  return !trimmed || trimmed === '{}' || trimmed === 'null'
}

function combineDetail(input: string, output: string): string {
  const hasInput = !isEmptyDetail(input)
  const hasOutput = !isEmptyDetail(output)
  if (hasInput && hasOutput) return `${input}${PROCESS_SEPARATOR}${output}`
  return hasInput ? input : output
}

function entryIdForMessage(message: Message): string {
  const type = message.message_type
  if (type === 'reasoning') return message.id
  const callId = message.metadata?.call_id
  if (callId != null && String(callId).trim()) return String(callId)
  return message.id
}

export function isActivityMessage(message: Message): boolean {
  const type = message.message_type
  if (type === 'cancelled' && message.metadata?.original_type === 'text') {
    return false
  }
  return (
    type === 'reasoning' ||
    type === 'cancelled' ||
    type === 'tool_call' ||
    type === 'tool_result' ||
    type === 'mcp_call' ||
    type === 'mcp_result' ||
    type.startsWith('skill_')
  )
}

export function messageToActivityEntry(message: Message): ActivityEntry {
  const type = message.message_type
  const meta = message.metadata ?? {}
  const entryId = entryIdForMessage(message)

  if (type === 'reasoning') {
    return {
      id: entryId,
      kind: 'reasoning',
      title: REASONING_TITLE,
      detail: message.content ?? '',
      status: 'done',
    }
  }

  if (type === 'cancelled') {
    const original = meta.original_type === 'reasoning' ? REASONING_TITLE : 'Partial response'
    return {
      id: entryId,
      kind: 'reasoning',
      title: `[Cancelled] ${original}`,
      detail: message.content ?? '',
      status: 'cancelled',
    }
  }

  const toolName = toolNameFromMessage(message)
  const kind = inferKind(type)

  if (type.startsWith('skill_')) {
    return {
      id: entryId,
      kind,
      title: toolName,
      detail: message.content ?? formatDetail(meta),
      status: 'done',
    }
  }

  if (type === 'tool_call' || type === 'mcp_call') {
    return {
      id: entryId,
      kind,
      title: toolName,
      detail: formatDetail(meta.arguments ?? meta),
      status: 'running',
    }
  }

  const result = meta.result ?? message.content
  const request = meta.arguments != null ? formatDetail(meta.arguments) : ''
  const response = formatDetail(result)
  return {
    id: entryId,
    kind,
    title: toolName,
    detail: combineDetail(request, response),
    status: resultLooksLikeError(result) ? 'error' : 'done',
  }
}

function findProcessBlockIndex(blocks: ChatBlock[], entryId: string): number {
  for (let i = blocks.length - 1; i >= 0; i -= 1) {
    const block = blocks[i]
    if (block.kind === 'process' && block.id === entryId) {
      return i
    }
  }
  return -1
}

function mergeActivityPair(existing: ActivityEntry, incoming: ActivityEntry): ActivityEntry {
  const inputPart = existing.detail.includes(PROCESS_SEPARATOR)
    ? existing.detail.split(PROCESS_SEPARATOR)[0]
    : existing.detail
  return {
    ...existing,
    title: existing.title !== 'unknown' ? existing.title : incoming.title,
    status: incoming.status === 'running' ? existing.status : incoming.status,
    detail:
      incoming.status === 'running'
        ? !isEmptyDetail(incoming.detail)
          ? incoming.detail
          : existing.detail
        : combineDetail(inputPart, incoming.detail),
  }
}

function mergeProcessBlock(blocks: ChatBlock[], entry: ActivityEntry): void {
  const idx = findProcessBlockIndex(blocks, entry.id)
  if (idx >= 0) {
    const block = blocks[idx]
    if (block.kind === 'process') {
      blocks[idx] = {
        kind: 'process',
        id: entry.id,
        item: mergeActivityPair(block.item, entry),
      }
    }
    return
  }
  blocks.push({ kind: 'process', id: entry.id, item: entry })
}

function isStreamingTextBubble(
  block: ChatBlock | undefined,
): block is { kind: 'bubble'; message: Message } {
  return block?.kind === 'bubble' && block.message.metadata?.streaming === true
}

function closeOpenStreamingText(blocks: ChatBlock[]): ChatBlock[] {
  const last = blocks[blocks.length - 1]
  if (!isStreamingTextBubble(last)) return blocks
  const next = [...blocks]
  next[next.length - 1] = {
    kind: 'bubble',
    message: {
      ...last.message,
      metadata: { ...last.message.metadata, streaming: false },
    },
  }
  return next
}

function createStreamingTextMessage(text: string): Message {
  return {
    id: `stream-text-${Date.now()}`,
    chat_id: '',
    role: 'assistant',
    message_type: 'text',
    content: text,
    metadata: { streaming: true },
    parent_id: null,
    sequence: 0,
    created_at: new Date().toISOString(),
  }
}

export function groupMessages(messages: Message[]): ChatBlock[] {
  const blocks: ChatBlock[] = []

  for (const message of messages) {
    if (isActivityMessage(message)) {
      mergeProcessBlock(blocks, messageToActivityEntry(message))
      continue
    }
    blocks.push({ kind: 'bubble', message })
  }

  for (const block of blocks) {
    if (
      block.kind === 'process' &&
      block.item.status === 'running' &&
      block.item.kind !== 'reasoning'
    ) {
      block.item = { ...block.item, status: 'done' }
    }
  }

  return blocks
}

export function applyStreamingText(blocks: ChatBlock[], text: string): ChatBlock[] {
  const last = blocks[blocks.length - 1]
  if (isStreamingTextBubble(last)) {
    const next = [...blocks]
    next[next.length - 1] = {
      kind: 'bubble',
      message: { ...last.message, content: text },
    }
    return next
  }
  return [...blocks, { kind: 'bubble', message: createStreamingTextMessage(text) }]
}

export function applyStreamingBlockActivity(
  blocks: ChatBlock[],
  entry: ActivityEntry,
): ChatBlock[] {
  let next = closeOpenStreamingText(blocks)

  if (entry.kind === 'reasoning' && entry.id === 'stream-reasoning') {
    const idx = next.findIndex((block) => block.kind === 'process' && block.id === 'stream-reasoning')
    if (idx >= 0) {
      const updated = [...next]
      const current = updated[idx]
      if (current.kind === 'process') {
        updated[idx] = {
          kind: 'process',
          id: 'stream-reasoning',
          item: {
            ...current.item,
            detail: `${current.item.detail}${entry.detail}`,
            status: 'running',
          },
        }
      }
      return updated
    }
    return [...next, { kind: 'process', id: entry.id, item: entry }]
  }

  if (entry.kind !== 'reasoning') {
    next = next.map((block) => {
      if (
        block.kind === 'process' &&
        block.id === 'stream-reasoning' &&
        block.item.status === 'running'
      ) {
        return { ...block, item: { ...block.item, status: 'done' as const } }
      }
      return block
    })
  }

  const idx = findProcessBlockIndex(next, entry.id)
  if (idx >= 0) {
    const updated = [...next]
    const current = updated[idx]
    if (current.kind === 'process') {
      updated[idx] = {
        kind: 'process',
        id: entry.id,
        item: mergeActivityPair(current.item, entry),
      }
    }
    return updated
  }

  return [...next, { kind: 'process', id: entry.id, item: entry }]
}

export function finalizeStreamingReasoning(blocks: ChatBlock[]): ChatBlock[] {
  return blocks.map((block) => {
    if (
      block.kind === 'process' &&
      block.id === 'stream-reasoning' &&
      block.item.status === 'running'
    ) {
      return { ...block, item: { ...block.item, status: 'done' as const } }
    }
    return block
  })
}

/** Mark all in-flight streaming UI as complete when the server signals run end. */
export function finalizeStreamingBlocks(blocks: ChatBlock[]): ChatBlock[] {
  let next = finalizeStreamingReasoning(blocks)
  next = closeOpenStreamingText(next)
  return next.map((block) => {
    if (block.kind === 'process' && block.item.status === 'running') {
      return { ...block, item: { ...block.item, status: 'done' as const } }
    }
    return block
  })
}

/** Show a breathing dot when the run is active but nothing is visibly streaming yet. */
export function shouldShowPendingIndicator(loading: boolean, blocks: ChatBlock[]): boolean {
  if (!loading) return false
  if (blocks.length === 0) return true
  const last = blocks[blocks.length - 1]
  if (last.kind === 'bubble') {
    const text = last.message.content?.trim() ?? ''
    if (text.length > 0) return false
    if (last.message.metadata?.streaming === true) return false
  }
  if (last.kind === 'process' && last.item.status === 'running') return false
  return true
}

export function createStreamingActivityEntry(
  event: 'reasoning' | 'tool_call' | 'tool_result',
  data: Record<string, unknown>,
): ActivityEntry | null {
  if (event === 'reasoning' && typeof data.text === 'string') {
    return {
      id: 'stream-reasoning',
      kind: 'reasoning',
      title: REASONING_TITLE,
      detail: data.text,
      status: 'running',
    }
  }

  if (event === 'tool_call') {
    const toolName = String(data.tool_name ?? '').trim() || 'unknown'
    const callId = String(data.call_id ?? `call-${Date.now()}`)
    return {
      id: callId,
      kind: 'tool',
      title: toolName,
      detail: formatDetail(data.arguments),
      status: 'running',
    }
  }

  if (event === 'tool_result') {
    const toolName = String(data.tool_name ?? '').trim() || 'unknown'
    const callId = String(data.call_id ?? `result-${Date.now()}`)
    const result = data.result
    return {
      id: callId,
      kind: 'tool',
      title: toolName,
      detail: formatDetail(result),
      status: resultLooksLikeError(result) ? 'error' : 'done',
    }
  }

  return null
}

