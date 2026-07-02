import type { Agent, Chat, ChatSummary, MemoryDocument, Message, StreamEvent } from '../types/agent'

const API = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  listAgents: () => request<Agent[]>('/agents'),
  listChats: (agentId: string) =>
    request<ChatSummary[]>(`/chats?agent_id=${encodeURIComponent(agentId)}`),
  createChat: (agentId: string) =>
    request<Chat>('/chats', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId }),
    }),
  listMessages: (chatId: string) => request<Message[]>(`/chats/${chatId}/messages`),
  cancelRun: (runId: string) =>
    request<{ run_id: string; chat_id: string; status: string }>(`/runs/${runId}/cancel`, {
      method: 'POST',
    }),
  getAgentMemory: (agentId: string) => request<MemoryDocument>(`/memories/agents/${agentId}`),
  appendMemory: (body: {
    scope: 'agent'
    agent_id: string
    lines: string[]
    is_constraint?: boolean
    source?: string
  }) =>
    request<MemoryDocument>('/memories/append', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  removeMemory: (body: { scope: 'agent'; agent_id: string; match: string }) =>
    request<MemoryDocument>('/memories/remove', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

export async function streamChat(
  chatId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API}/chats/${chatId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, attachment_ids: [] }),
    signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(await res.text())
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const lines = part.split('\n')
      let event = 'message'
      let data = ''
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) data = line.slice(5).trim()
      }
      if (data) {
        onEvent({ event, data: JSON.parse(data) as Record<string, unknown> })
      }
    }
  }
}
