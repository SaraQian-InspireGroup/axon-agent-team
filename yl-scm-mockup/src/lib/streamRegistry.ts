export type ActiveStream = {
  chatId: string
  agentId: string
  generation: number
  abortController: AbortController
  segmentText: string
  runId: string | null
  streamIdleSeen: boolean
  reloadedAfterStream: boolean
}

export class StreamRegistry {
  private readonly streams = new Map<string, ActiveStream>()
  private readonly chatToAgent = new Map<string, string>()
  private readonly generations = new Map<string, number>()

  bindChat(chatId: string, agentId: string): void {
    this.chatToAgent.set(chatId.trim().toLowerCase(), agentId)
  }

  private key(chatId: string): string {
    return chatId.trim().toLowerCase()
  }

  nextGeneration(chatId: string): number {
    const id = this.key(chatId)
    const next = (this.generations.get(id) ?? 0) + 1
    this.generations.set(id, next)
    return next
  }

  get(chatId: string): ActiveStream | undefined {
    return this.streams.get(this.key(chatId))
  }

  set(chatId: string, stream: ActiveStream): void {
    this.streams.set(this.key(chatId), stream)
  }

  delete(chatId: string): void {
    this.streams.delete(this.key(chatId))
  }

  abort(chatId: string): void {
    this.streams.get(this.key(chatId))?.abortController.abort()
  }

  abortAll(): void {
    for (const stream of this.streams.values()) {
      stream.abortController.abort()
    }
    this.streams.clear()
  }

  isActive(chatId: string, generation: number): boolean {
    const stream = this.streams.get(this.key(chatId))
    return stream != null && stream.generation === generation
  }
}
