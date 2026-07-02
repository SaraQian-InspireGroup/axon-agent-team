import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from '../api/client'
import { getStoredChatId, setStoredChatId } from '../lib/chatStorage'
import {
  applyStreamReasoning,
  applyStreamText,
  applyStreamToolCall,
  applyStreamToolResult,
  finalizeStreamLocalMessages,
  finalizeStreamReasoning,
  mergeMessagesFromApi,
} from '../lib/messageActivity'
import { StreamRegistry } from '../lib/streamRegistry'
import { formatUserFacingError } from '../lib/userFacingError'
import type { ChatSummary, Message } from '../types/agent'

export const YL_WORKER1_SLUG = 'yl-worker1'

function pickMostRecentChatId(rows: ChatSummary[]): string | null {
  if (rows.length === 0) return null
  const sorted = [...rows].sort((a, b) => {
    const aTime = a.updated_at ?? a.created_at ?? ''
    const bTime = b.updated_at ?? b.created_at ?? ''
    return bTime.localeCompare(aTime)
  })
  return sorted[0]?.id ?? null
}

export function useNovaChat(enabled: boolean) {
  const [agentId, setAgentId] = useState<string | null>(null)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [chatId, setChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [chatSessionLoading, setChatSessionLoading] = useState(false)
  const [chatHistory, setChatHistory] = useState<ChatSummary[]>([])
  const [chatHistoryLoading, setChatHistoryLoading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [turnSyncHint, setTurnSyncHint] = useState<string | null>(null)
  const [initialized, setInitialized] = useState(false)

  const streamRegistryRef = useRef(new StreamRegistry())
  const messagesRef = useRef(messages)
  const chatIdRef = useRef(chatId)
  const agentIdRef = useRef(agentId)
  const loadTaskRef = useRef<Promise<void> | null>(null)
  const openLoadGenRef = useRef(0)

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    chatIdRef.current = chatId
  }, [chatId])

  useEffect(() => {
    agentIdRef.current = agentId
  }, [agentId])

  const refreshChatHistory = useCallback(async (resolvedAgentId: string) => {
    setChatHistoryLoading(true)
    try {
      const rows = await api.listChats(resolvedAgentId)
      setChatHistory(rows)
    } catch {
      setChatHistory([])
    } finally {
      setChatHistoryLoading(false)
    }
  }, [])

  const openChatById = useCallback(
    async (resolvedAgentId: string, id: string) => {
      const loadGen = openLoadGenRef.current + 1
      openLoadGenRef.current = loadGen

      if (chatIdRef.current && chatIdRef.current !== id) {
        streamRegistryRef.current.abort(chatIdRef.current)
      }

      setChatSessionLoading(true)
      setError(null)
      if (chatIdRef.current !== id) {
        setMessages([])
      }

      try {
        const rows = await api.listMessages(id)
        if (loadGen !== openLoadGenRef.current) return
        setMessages(rows)
        setChatId(id)
        setInput('')
        setStoredChatId(resolvedAgentId, id)
        streamRegistryRef.current.bindChat(id, resolvedAgentId)
      } catch (e) {
        if (loadGen !== openLoadGenRef.current) return
        setError(e instanceof Error ? e.message : '加载会话失败')
        throw e
      } finally {
        if (loadGen === openLoadGenRef.current) {
          setChatSessionLoading(false)
        }
      }
    },
    [],
  )

  const createAndOpenChat = useCallback(
    async (resolvedAgentId: string) => {
      const chat = await api.createChat(resolvedAgentId)
      await openChatById(resolvedAgentId, chat.id)
      await refreshChatHistory(resolvedAgentId)
      return chat.id
    },
    [openChatById, refreshChatHistory],
  )

  const reloadMessagesAfterStream = useCallback(
    async (resolvedAgentId: string, id: string) => {
      const rows = await api.listMessages(id)
      setMessages((prev) => mergeMessagesFromApi(rows, prev))
      await refreshChatHistory(resolvedAgentId)
    },
    [refreshChatHistory],
  )

  const loadChat = useCallback(
    async (resolvedAgentId: string) => {
      setError(null)
      let rows: ChatSummary[] = []
      setChatHistoryLoading(true)
      try {
        rows = await api.listChats(resolvedAgentId)
        setChatHistory(rows)
      } catch {
        rows = []
        setChatHistory([])
      } finally {
        setChatHistoryLoading(false)
      }

      const storedChatId = getStoredChatId(resolvedAgentId)
      if (storedChatId && rows.some((row) => row.id === storedChatId)) {
        await openChatById(resolvedAgentId, storedChatId)
        return
      }

      const recentChatId = pickMostRecentChatId(rows)
      if (recentChatId) {
        await openChatById(resolvedAgentId, recentChatId)
        return
      }

      await createAndOpenChat(resolvedAgentId)
    },
    [createAndOpenChat, openChatById],
  )

  const ensureInitialized = useCallback(async () => {
    if (initialized) return
    if (loadTaskRef.current) {
      await loadTaskRef.current
      return
    }

    const task = (async () => {
      setAgentError(null)
      setChatSessionLoading(true)
      try {
        const agents = await api.listAgents()
        const agent = agents.find((row) => row.slug === YL_WORKER1_SLUG)
        if (!agent) {
          throw new Error(`未找到 agent：${YL_WORKER1_SLUG}`)
        }
        setAgentId(agent.id)
        await loadChat(agent.id)
        setInitialized(true)
      } catch (e) {
        setAgentError(formatUserFacingError(e, 'Nova 初始化失败'))
      } finally {
        setChatSessionLoading(false)
        loadTaskRef.current = null
      }
    })()

    loadTaskRef.current = task
    await task
  }, [initialized, loadChat])

  useEffect(() => {
    if (enabled) {
      void ensureInitialized()
    }
  }, [enabled, ensureInitialized])

  useEffect(() => {
    return () => {
      streamRegistryRef.current.abortAll()
    }
  }, [])

  const startNewSession = useCallback(async () => {
    const resolvedAgentId = agentIdRef.current
    if (!resolvedAgentId || loading || chatSessionLoading) return
    setHistoryOpen(false)
    setError(null)
    try {
      await createAndOpenChat(resolvedAgentId)
    } catch (e) {
      setError(formatUserFacingError(e, '创建新会话失败'))
    }
  }, [chatSessionLoading, createAndOpenChat, loading])

  const loadHistorySession = useCallback(
    async (id: string) => {
      const resolvedAgentId = agentIdRef.current
      if (!resolvedAgentId || chatSessionLoading) return
      if (loading && chatIdRef.current === id) return
      setHistoryOpen(false)
      setError(null)
      try {
        await openChatById(resolvedAgentId, id)
      } catch (e) {
        setError(formatUserFacingError(e, '加载会话失败'))
      }
    },
    [chatSessionLoading, loading, openChatById],
  )

  const stopStreaming = useCallback(async () => {
    const resolvedAgentId = agentIdRef.current
    const activeChatId = chatIdRef.current
    if (!resolvedAgentId || !activeChatId) return

    const stream = streamRegistryRef.current.get(activeChatId)
    const runId = stream?.runId ?? activeRunId
    if (!runId) return

    try {
      await api.cancelRun(runId)
    } catch {
      /* idempotent */
    }

    streamRegistryRef.current.abort(activeChatId)

    try {
      await reloadMessagesAfterStream(resolvedAgentId, activeChatId)
    } finally {
      setLoading(false)
      setActiveRunId(null)
      setTurnSyncHint(null)
    }
  }, [activeRunId, reloadMessagesAfterStream])

  const sendMessage = useCallback(async () => {
    const resolvedAgentId = agentIdRef.current
    if (!resolvedAgentId || loading) return

    const text = input.trim()
    if (!text) return

    setInput('')
    setLoading(true)
    setError(null)
    setTurnSyncHint(null)

    let activeChatId = chatIdRef.current
    try {
      if (!activeChatId) {
        activeChatId = await createAndOpenChat(resolvedAgentId)
      }
    } catch (e) {
      setLoading(false)
      setError(formatUserFacingError(e, '无法开始对话'))
      return
    }

    streamRegistryRef.current.bindChat(activeChatId, resolvedAgentId)
    streamRegistryRef.current.abort(activeChatId)

    setMessages((prev) =>
      prev.filter((msg) => !msg.metadata?.local || (msg.id.startsWith('tmp-') && msg.role === 'user')),
    )

    const optimistic: Message = {
      id: `tmp-${Date.now()}`,
      chat_id: activeChatId,
      role: 'user',
      message_type: 'text',
      content: text,
      metadata: {},
      parent_id: null,
      sequence: messagesRef.current.reduce((max, row) => Math.max(max, row.sequence), 0) + 1,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimistic])

    const generation = streamRegistryRef.current.nextGeneration(activeChatId)
    const abortController = new AbortController()
    const streamHandle = {
      chatId: activeChatId,
      agentId: resolvedAgentId,
      generation,
      abortController,
      segmentText: '',
      runId: null as string | null,
      streamIdleSeen: false,
      reloadedAfterStream: false,
    }
    streamRegistryRef.current.set(activeChatId, streamHandle)
    setActiveRunId(null)

    const patchMessages = (updater: (prev: Message[]) => Message[]) => {
      if (!streamRegistryRef.current.isActive(activeChatId, generation)) return
      setMessages(updater)
    }

    const finishTurnAfterStream = async () => {
      const handle = streamRegistryRef.current.get(activeChatId)
      if (!handle || handle.generation !== generation || handle.reloadedAfterStream) return
      handle.reloadedAfterStream = true
      try {
        if (!handle.streamIdleSeen) {
          setTurnSyncHint('正在保存对话…')
          patchMessages((prev) => finalizeStreamLocalMessages(prev))
        } else {
          setTurnSyncHint('正在保存对话…')
        }
        await reloadMessagesAfterStream(resolvedAgentId, activeChatId)
      } finally {
        if (streamRegistryRef.current.isActive(activeChatId, generation)) {
          setLoading(false)
          setActiveRunId(null)
          setTurnSyncHint(null)
        }
      }
    }

    try {
      await streamChat(
        activeChatId,
        text,
        (ev) => {
          if (!streamRegistryRef.current.isActive(activeChatId, generation)) return
          const handle = streamRegistryRef.current.get(activeChatId)!

          if (ev.event === 'run_started' && ev.data.run_id != null) {
            const id = String(ev.data.run_id)
            handle.runId = id
            setActiveRunId(id)
          }
          if (ev.event === 'text' && typeof ev.data.text === 'string') {
            const chunk = ev.data.text
            if (
              handle.segmentText === '' ||
              (chunk.length >= handle.segmentText.length && chunk.startsWith(handle.segmentText))
            ) {
              handle.segmentText = chunk
            } else if (chunk) {
              handle.segmentText += chunk
            }
            patchMessages((prev) => applyStreamText(prev, activeChatId, handle.segmentText))
          }
          if (ev.event === 'reasoning_done') {
            patchMessages((prev) => finalizeStreamReasoning(prev))
          }
          if (ev.event === 'reasoning' && typeof ev.data.text === 'string') {
            patchMessages((prev) => applyStreamReasoning(prev, activeChatId, ev.data.text as string))
          }
          if (ev.event === 'tool_call' && ev.data) {
            handle.segmentText = ''
            patchMessages((prev) => applyStreamToolCall(prev, activeChatId, ev.data))
          }
          if (ev.event === 'tool_result' && ev.data) {
            handle.segmentText = ''
            patchMessages((prev) => applyStreamToolResult(prev, activeChatId, ev.data))
          }
          if (ev.event === 'stream_idle') {
            handle.streamIdleSeen = true
            patchMessages((prev) => finalizeStreamLocalMessages(prev))
            setLoading(false)
            setActiveRunId(null)
            setTurnSyncHint('正在保存对话…')
          }
          if (ev.event === 'error') {
            throw new Error(formatUserFacingError(ev.data.error ?? ev.data, 'stream error'))
          }
        },
        abortController.signal,
      )

      if (!streamRegistryRef.current.isActive(activeChatId, generation)) return
      await finishTurnAfterStream()
    } catch (e) {
      if (!streamRegistryRef.current.isActive(activeChatId, generation)) return
      if (e instanceof Error && e.name === 'AbortError') return
      setError(formatUserFacingError(e, '发送消息失败'))
      setLoading(false)
      setActiveRunId(null)
      setTurnSyncHint(null)
      try {
        await reloadMessagesAfterStream(resolvedAgentId, activeChatId)
      } catch {
        /* ignore */
      }
    } finally {
      if (streamRegistryRef.current.get(activeChatId)?.generation === generation) {
        streamRegistryRef.current.delete(activeChatId)
      }
    }
  }, [createAndOpenChat, input, loading, reloadMessagesAfterStream])

  const toggleHistoryOpen = useCallback(() => {
    setHistoryOpen((value) => {
      const next = !value
      if (next && agentIdRef.current) {
        void refreshChatHistory(agentIdRef.current)
      }
      return next
    })
  }, [refreshChatHistory])

  const closeHistory = useCallback(() => {
    setHistoryOpen(false)
  }, [])

  return {
    agentError,
    chatId,
    messages,
    input,
    setInput,
    loading,
    chatSessionLoading,
    chatHistory,
    chatHistoryLoading,
    historyOpen,
    toggleHistoryOpen,
    closeHistory,
    error,
    turnSyncHint,
    startNewSession,
    loadHistorySession,
    sendMessage,
    stopStreaming,
  }
}
