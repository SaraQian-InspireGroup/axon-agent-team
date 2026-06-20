/** Attachment limits — defaults match backend; override via GET /config/attachments */

import type { ChatAttachment } from '../types'

export const DEFAULT_ATTACHMENT_LIMITS = {
  max_files_per_message: 5,
  max_bytes_per_file: 50 * 1024 * 1024,
  max_total_bytes_per_message: 50 * 1024 * 1024,
} as const

export type AttachmentLimits = {
  max_files_per_message: number
  max_bytes_per_file: number
  max_total_bytes_per_message: number
}

export const SUPPORTED_ATTACHMENT_ACCEPT =
  '.pdf,.txt,.md,.csv,.json,.png,.jpg,.jpeg,.gif,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx'

export const SUPPORTED_ATTACHMENT_LABEL =
  'PDF, text, CSV, JSON, images (PNG/JPEG/GIF/WebP), Word/Excel/PowerPoint'

export function formatAttachmentLimitMb(bytes: number): number {
  return bytes / (1024 * 1024)
}

export function validatePendingAttachments(
  current: { size_bytes: number }[],
  incomingBytes: number,
  limits: AttachmentLimits = DEFAULT_ATTACHMENT_LIMITS,
): string | null {
  if (current.length >= limits.max_files_per_message) {
    return `At most ${limits.max_files_per_message} attachments per message`
  }
  if (incomingBytes > limits.max_bytes_per_file) {
    return `Each file must be under ${formatAttachmentLimitMb(limits.max_bytes_per_file)} MB`
  }
  const total = current.reduce((sum, item) => sum + item.size_bytes, 0) + incomingBytes
  if (total > limits.max_total_bytes_per_message) {
    return `Combined attachments must stay under ${formatAttachmentLimitMb(limits.max_total_bytes_per_message)} MB per message`
  }
  return null
}

/** Pending attachment before send — local file (no chat yet) or uploaded to provider. */
export type PendingAttachment =
  | { kind: 'local'; localId: string; file: File }
  | { kind: 'uploaded'; attachment: ChatAttachment }

export function pendingAttachmentId(item: PendingAttachment): string {
  return item.kind === 'local' ? item.localId : item.attachment.id
}

export function pendingAttachmentFilename(item: PendingAttachment): string {
  return item.kind === 'local' ? item.file.name : item.attachment.filename
}

export function pendingAttachmentSize(item: PendingAttachment): number {
  return item.kind === 'local' ? item.file.size : item.attachment.size_bytes
}

export function pendingAttachmentsForValidation(items: PendingAttachment[]): { size_bytes: number }[] {
  return items.map((item) => ({ size_bytes: pendingAttachmentSize(item) }))
}
