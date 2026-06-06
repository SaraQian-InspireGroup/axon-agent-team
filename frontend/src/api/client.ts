import type { Agent, Chat, ChatSummary, Message, StreamEvent, User } from '../types'

const API = '/api/v1'

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
  getCurrentUser: () => request<User>('/users/me'),
  listAgents: () => request<Agent[]>('/agents'),
  getAgent: (id: string) => request<Agent>(`/agents/${id}`),

  listChats: (agentId: string) =>
    request<ChatSummary[]>(`/chats?agent_id=${encodeURIComponent(agentId)}`),
  createChat: (agentId: string) =>
    request<Chat>('/chats', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId }),
    }),
  listMessages: (chatId: string) => request<Message[]>(`/chats/${chatId}/messages`),
}

export async function streamChat(
  chatId: string,
  content: string,
  onEvent: (ev: StreamEvent) => void,
): Promise<void> {
  const res = await fetch(`${API}/chats/${chatId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
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
