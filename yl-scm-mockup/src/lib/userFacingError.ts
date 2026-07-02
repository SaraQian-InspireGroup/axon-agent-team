export function formatUserFacingError(raw: unknown, fallback = '请求失败，请稍后重试。'): string {
  if (raw instanceof Error) {
    return formatUserFacingError(raw.message, fallback)
  }
  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    return trimmed || fallback
  }
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    const message = (raw as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) return message.trim()
  }
  return fallback
}
