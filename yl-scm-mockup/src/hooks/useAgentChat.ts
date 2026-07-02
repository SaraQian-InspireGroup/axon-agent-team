import { useCallback, useRef, useState } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface ChatSession {
  id: string
  title: string
  updatedAt: string
  messages: ChatMessage[]
}

const MOCK_HISTORY: ChatSession[] = [
  {
    id: 'hist-1',
    title: '全国库存缺口分析',
    updatedAt: '2026-07-02 09:12',
    messages: [
      {
        id: 'm1',
        role: 'user',
        content: '帮我看一下天津销售仓的缺口情况',
      },
      {
        id: 'm2',
        role: 'assistant',
        content: '天津销售仓当前有 3 个 SKU 存在分配后缺口，建议优先查看中老年系列奶粉。',
      },
    ],
  },
  {
    id: 'hist-2',
    title: '分仓补录单批量导出',
    updatedAt: '2026-07-01 16:40',
    messages: [
      {
        id: 'm3',
        role: 'user',
        content: '如何批量导出未生成调拨单的分仓补录单？',
      },
      {
        id: 'm4',
        role: 'assistant',
        content: '在分仓补录单页面勾选目标单据后，点击「导出」即可导出所选记录。',
      },
    ],
  },
]

function createSession(title = '新对话'): ChatSession {
  const now = new Date()
  const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  return {
    id: `session-${Date.now()}`,
    title,
    updatedAt: stamp,
    messages: [],
  }
}

export function useAgentChat() {
  const initialSession = createSession()
  const [sessions, setSessions] = useState<ChatSession[]>([initialSession])
  const [activeSessionId, setActiveSessionId] = useState(initialSession.id)
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const streamTimerRef = useRef<number | null>(null)

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? sessions[0]

  const updateSession = useCallback((sessionId: string, updater: (session: ChatSession) => ChatSession) => {
    setSessions((prev) =>
      prev.map((session) => (session.id === sessionId ? updater(session) : session)),
    )
  }, [])

  const startNewSession = useCallback(() => {
    const session = createSession()
    setSessions((prev) => [session, ...prev])
    setActiveSessionId(session.id)
    setInput('')
    setHistoryOpen(false)
    setIsStreaming(false)
    if (streamTimerRef.current) {
      window.clearTimeout(streamTimerRef.current)
      streamTimerRef.current = null
    }
  }, [])

  const loadSession = useCallback((sessionId: string) => {
    const target = MOCK_HISTORY.find((session) => session.id === sessionId)
    if (target) {
      setSessions((prev) => {
        if (prev.some((session) => session.id === sessionId)) return prev
        return [target, ...prev]
      })
    }
    setActiveSessionId(sessionId)
    setHistoryOpen(false)
    setInput('')
    setIsStreaming(false)
    if (streamTimerRef.current) {
      window.clearTimeout(streamTimerRef.current)
      streamTimerRef.current = null
    }
  }, [])

  const pauseStreaming = useCallback(() => {
    if (streamTimerRef.current) {
      window.clearTimeout(streamTimerRef.current)
      streamTimerRef.current = null
    }
    setIsStreaming(false)
  }, [])

  const sendMessage = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || !activeSession || isStreaming) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    }

    const sessionTitle =
      activeSession.messages.length === 0 ? trimmed.slice(0, 24) : activeSession.title

    const sessionId = activeSession.id

    updateSession(sessionId, (session) => ({
      ...session,
      title: sessionTitle,
      updatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
      messages: [...session.messages, userMessage],
    }))
    setInput('')
    setIsStreaming(true)

    streamTimerRef.current = window.setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content:
          '我已收到您的问题。这是 mockup 演示回复：后续可接入真实 Agent，支持库存分析、分货建议与分仓补录单操作指引。',
      }
      updateSession(sessionId, (session) => ({
        ...session,
        updatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
        messages: [...session.messages, assistantMessage],
      }))
      setIsStreaming(false)
      streamTimerRef.current = null
    }, 1200)
  }, [activeSession, input, isStreaming, updateSession])

  return {
    sessions,
    historySessions: MOCK_HISTORY,
    activeSession,
    input,
    setInput,
    isStreaming,
    historyOpen,
    setHistoryOpen,
    startNewSession,
    loadSession,
    sendMessage,
    pauseStreaming,
  }
}
