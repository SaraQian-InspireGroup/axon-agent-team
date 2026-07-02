export interface Agent {
  id: string
  slug: string | null
  name: string
  description: string | null
  model_provider: string
  model_name: string
}

export interface Chat {
  id: string
  user_id: string
  agent_id: string
  title: string | null
}

export interface ChatSummary {
  id: string
  agent_id: string
  title: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Message {
  id: string
  chat_id: string
  role: string
  message_type: string
  content: string | null
  metadata: Record<string, unknown>
  parent_id: string | null
  sequence: number
  created_at: string | null
}

export interface StreamEvent {
  event: string
  data: Record<string, unknown>
}
