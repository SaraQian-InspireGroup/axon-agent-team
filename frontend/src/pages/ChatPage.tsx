import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from '../api/client'
import { AgentIcon } from '../components/AgentIcon'
import { ChatHistoryPanel } from '../components/ChatHistoryPanel'
import { MemoryPanel } from '../components/MemoryPanel'
import { ProposalLivePanel } from '../components/ProposalLivePanel'
import { ProposalPanelShell, readProposalPanelWidth, type ProposalPanelTab } from '../components/ProposalPanelShell'
import { ProposalStatePanel } from '../components/ProposalStatePanel'
import { ChatHistoryIcon } from '../components/ChatHistoryIcon'
import { ChatMessageList } from '../components/ChatMessageList'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { NewChatIcon } from '../components/NewChatIcon'
import { SidebarToggleIcon } from '../components/SidebarToggleIcon'
import { UserIcon } from '../components/UserIcon'
import { formatAgentSlugLabel } from '../lib/agentLabel'
import { formatApiError } from '../lib/apiErrorMessage'
import { getStoredChatId, setStoredChatId } from '../lib/chatStorage'
import {
  applyStreamArtifact,
  applyStreamReasoning,
  applyStreamText,
  applyStreamToolCall,
  applyStreamToolResult,
  applyStreamViz,
  finalizeStreamReasoning,
  mergeMessagesFromApi,
} from '../lib/messageActivity'
import type { ArtifactSpec } from '../types/artifact'
import type { VizSpec } from '../types/viz'
import type { ProposalPreview } from '../types/proposalPreview'
import type { ProposalDraftResponse } from '../types/proposalDraft'
import type { Agent, ChatSummary, Message } from '../types'

const SIDEBAR_COLLAPSED_KEY = 'agent-platform:sidebar-collapsed'
const PROPOSAL_COMPOSER_SLUG = 'proposal-composer'

function parseProposalPreview(data: Record<string, unknown>): ProposalPreview | null {
  if (typeof data.state_fingerprint !== 'string' || typeof data.title !== 'string') {
    return null
  }
  const completenessRaw = data.completeness
  const completeness =
    completenessRaw && typeof completenessRaw === 'object'
      ? {
          missing_required: Array.isArray((completenessRaw as ProposalPreview['completeness']).missing_required)
            ? ((completenessRaw as ProposalPreview['completeness']).missing_required as string[])
            : [],
          ready_to_preview: Boolean((completenessRaw as ProposalPreview['completeness']).ready_to_preview),
          ready_to_generate: Boolean((completenessRaw as ProposalPreview['completeness']).ready_to_generate),
        }
      : { missing_required: [], ready_to_preview: false, ready_to_generate: false }

  return {
    chat_id: typeof data.chat_id === 'string' ? data.chat_id : undefined,
    status: (data.status as ProposalPreview['status']) || 'empty',
    title: data.title,
    markdown: typeof data.markdown === 'string' ? data.markdown : '',
    filename: typeof data.filename === 'string' ? data.filename : 'proposal.md',
    state_fingerprint: data.state_fingerprint,
    message: typeof data.message === 'string' ? data.message : null,
    completeness,
  }
}

function shouldReplaceProposalPreview(
  prev: ProposalPreview | null,
  next: ProposalPreview,
): boolean {
  if (!prev) return true
  if (
    next.chat_id &&
    prev.chat_id &&
    next.chat_id !== prev.chat_id
  ) {
    return true
  }
  if (prev.markdown && !next.markdown && (next.status === 'empty' || next.status === 'blocked')) {
    return false
  }
  if (next.state_fingerprint !== prev.state_fingerprint) return true
  if (next.markdown !== prev.markdown) return true
  if (next.markdown && !prev.markdown) return true
  return !prev.markdown
}

function parseToolResultObject(result: unknown): Record<string, unknown> | null {
  if (result && typeof result === 'object' && !Array.isArray(result)) {
    return result as Record<string, unknown>
  }
  if (typeof result !== 'string') return null
  try {
    const parsed: unknown = JSON.parse(result)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null
  } catch {
    return null
  }
}

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}

export function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [agentsLoading, setAgentsLoading] = useState(true)
  const [agentsError, setAgentsError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [chatId, setChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatSummary[]>([])
  const [chatHistoryLoading, setChatHistoryLoading] = useState(false)
  const [chatSessionLoading, setChatSessionLoading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [memoryOpen, setMemoryOpen] = useState(false)
  const [proposalPanelCollapsed, setProposalPanelCollapsed] = useState(true)
  const [proposalPanelTab, setProposalPanelTab] = useState<ProposalPanelTab>('preview')
  const [proposalPanelWidth, setProposalPanelWidth] = useState(readProposalPanelWidth)
  const [proposalPreview, setProposalPreview] = useState<ProposalPreview | null>(null)
  const [proposalPreviewLoading, setProposalPreviewLoading] = useState(false)
  const [proposalTurnSyncing, setProposalTurnSyncing] = useState(false)
  const [proposalPreviewError, setProposalPreviewError] = useState<string | null>(null)
  const [proposalState, setProposalState] = useState<Record<string, unknown> | null>(null)
  const [proposalStateFingerprint, setProposalStateFingerprint] = useState<string | null>(null)
  const [proposalStateLoading, setProposalStateLoading] = useState(false)
  const [proposalStateError, setProposalStateError] = useState<string | null>(null)
  const proposalPreviewFetchGenRef = useRef(0)
  const proposalStateFetchGenRef = useRef(0)
  const chatIdRef = useRef<string | null>(null)
  const proposalPanelTabRef = useRef<ProposalPanelTab>('preview')
  const [memoryRefreshKey, setMemoryRefreshKey] = useState(0)
  const messagesScrollRef = useRef<HTMLDivElement>(null)
  const pinToBottomRef = useRef(true)
  const runIdRef = useRef<string | null>(null)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const streamGenRef = useRef(0)
  const streamAbortRef = useRef<AbortController | null>(null)
  const reloadInFlightRef = useRef<Promise<void> | null>(null)
  /** True when SSE proposal_updated already applied preview for the current turn. */
  const previewFreshFromStreamRef = useRef(false)

  const SCROLL_PIN_THRESHOLD_PX = 80

  const updateScrollPin = useCallback(() => {
    const el = messagesScrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    pinToBottomRef.current = distanceFromBottom <= SCROLL_PIN_THRESHOLD_PX
  }, [])

  const scrollToBottomIfPinned = useCallback(() => {
    const el = messagesScrollRef.current
    if (!el || !pinToBottomRef.current) return
    el.scrollTop = el.scrollHeight
  }, [])

  const selected = agents.find((a) => a.id === selectedId) ?? null
  const isProposalComposer = selected?.slug === PROPOSAL_COMPOSER_SLUG
  const showChat = !agentsLoading && selected != null

  const invalidateProposalPanelFetches = useCallback(() => {
    ++proposalPreviewFetchGenRef.current
    ++proposalStateFetchGenRef.current
    previewFreshFromStreamRef.current = false
  }, [])

  const fetchProposalPreview = useCallback(async (id: string) => {
    const generation = ++proposalPreviewFetchGenRef.current
    setProposalPreviewLoading(true)
    setProposalPreviewError(null)
    try {
      const preview = await api.getProposalPreview(id, true)
      if (generation !== proposalPreviewFetchGenRef.current) return
      if (chatIdRef.current !== id) return
      if (preview.chat_id && preview.chat_id !== id) return
      setProposalPreview((prev) =>
        shouldReplaceProposalPreview(prev, preview) ? preview : prev,
      )
    } catch (e) {
      if (generation !== proposalPreviewFetchGenRef.current) return
      setProposalPreviewError(e instanceof Error ? e.message : 'Failed to load proposal preview')
    } finally {
      if (generation === proposalPreviewFetchGenRef.current) {
        setProposalPreviewLoading(false)
      }
    }
  }, [])

  const fetchProposalState = useCallback(async (id: string) => {
    const generation = ++proposalStateFetchGenRef.current
    setProposalStateLoading(true)
    setProposalStateError(null)
    try {
      const payload: ProposalDraftResponse = await api.getProposalDraft(id)
      if (generation !== proposalStateFetchGenRef.current) return
      if (chatIdRef.current !== id) return
      if (payload.chat_id && payload.chat_id !== id) return
      setProposalState(payload.draft)
      setProposalStateFingerprint(payload.state_fingerprint)
    } catch (e) {
      if (generation !== proposalStateFetchGenRef.current) return
      setProposalStateError(formatApiError(e, 'Failed to load proposal draft'))
    } finally {
      if (generation === proposalStateFetchGenRef.current) {
        setProposalStateLoading(false)
      }
    }
  }, [])

  const applyProposalPreview = useCallback((preview: ProposalPreview, forChatId: string) => {
    if (chatIdRef.current !== forChatId) return
    if (preview.chat_id && preview.chat_id !== forChatId) return
    ++proposalPreviewFetchGenRef.current
    previewFreshFromStreamRef.current = true
    setProposalPreview((prev) =>
      shouldReplaceProposalPreview(prev, preview) ? preview : prev,
    )
    setProposalPreviewLoading(false)
    setProposalPreviewError(null)
    setProposalTurnSyncing(false)
    if (preview.markdown) {
      setProposalPanelCollapsed(false)
    }
  }, [])

  useEffect(() => {
    chatIdRef.current = chatId
  }, [chatId])

  useEffect(() => {
    proposalPanelTabRef.current = proposalPanelTab
  }, [proposalPanelTab])

  const collapseProposalPanel = useCallback(() => {
    setProposalPanelCollapsed(true)
  }, [])

  const expandProposalPanel = useCallback(
    (tab: ProposalPanelTab = 'preview') => {
      setProposalPanelCollapsed(false)
      setProposalPanelTab(tab)
      if (!chatId) return
      if (tab === 'preview') void fetchProposalPreview(chatId)
      if (tab === 'state') void fetchProposalState(chatId)
    },
    [chatId, fetchProposalPreview, fetchProposalState],
  )

  const handleProposalPanelTabChange = useCallback(
    (tab: ProposalPanelTab) => {
      setProposalPanelTab(tab)
      if (!chatId) return
      if (tab === 'preview') void fetchProposalPreview(chatId)
      if (tab === 'state') void fetchProposalState(chatId)
    },
    [chatId, fetchProposalPreview, fetchProposalState],
  )

  const handleExpandArtifact = useCallback(
    (_spec: ArtifactSpec) => {
      if (!isProposalComposer) return
      expandProposalPanel()
      setHistoryOpen(false)
      setMemoryOpen(false)
    },
    [expandProposalPanel, isProposalComposer],
  )

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0')
      } catch {
        /* ignore */
      }
      return next
    })
  }

  const refreshChatHistory = useCallback(async (agentId: string) => {
    setChatHistoryLoading(true)
    try {
      const rows = await api.listChats(agentId)
      setChatHistory(rows)
    } catch {
      setChatHistory([])
    } finally {
      setChatHistoryLoading(false)
    }
  }, [])

  const openChatById = useCallback(async (agentId: string, id: string) => {
    setError(null)
    invalidateProposalPanelFetches()
    setChatId(id)
    setProposalPreview(null)
    setProposalPreviewError(null)
    setProposalState(null)
    setProposalStateFingerprint(null)
    setProposalStateError(null)
    setStoredChatId(agentId, id)
    setInput('')
    const rows = await api.listMessages(id)
    setMessages(rows)
  }, [invalidateProposalPanelFetches])

  const loadChat = useCallback(
    async (agentId: string) => {
      setError(null)
      let id = getStoredChatId(agentId)
      if (!id) {
        const chat = await api.createChat(agentId)
        id = chat.id
        setStoredChatId(agentId, id)
      }
      await openChatById(agentId, id)
      await refreshChatHistory(agentId)
    },
    [openChatById, refreshChatHistory],
  )

  const selectAgent = useCallback(
    async (agent: Agent) => {
      setSelectedId(agent.id)
      setHistoryOpen(false)
      setInput('')
      try {
        await loadChat(agent.id)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load conversation')
      }
    },
    [loadChat],
  )

  const loadAgents = useCallback(
    async (options?: { autoSelect?: boolean }) => {
      setAgentsLoading(true)
      setAgentsError(null)
      try {
        const rows = await api.listAgents()
        setAgents(rows)
        if (rows.length > 0 && options?.autoSelect) {
          await selectAgent(rows[0])
        }
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Failed to load agents'
        setAgents([])
        setAgentsError(message)
      } finally {
        setAgentsLoading(false)
      }
    },
    [selectAgent],
  )

  useEffect(() => {
    void loadAgents({ autoSelect: true })
  }, [loadAgents])

  useEffect(() => {
    void api.getCurrentUser().then(
      (user) => setUserEmail(user.email),
      () => setUserEmail(null),
    )
  }, [])

  useEffect(() => {
    if (!isProposalComposer) {
      setProposalPanelCollapsed(true)
      setProposalPanelTab('preview')
      setProposalPreview(null)
      setProposalPreviewError(null)
      setProposalState(null)
      setProposalStateFingerprint(null)
      setProposalStateError(null)
      return
    }
    if (!chatId) return
    invalidateProposalPanelFetches()
    setProposalPanelCollapsed(false)
    setProposalPanelTab('preview')
    void fetchProposalPreview(chatId)
  }, [isProposalComposer, chatId, fetchProposalPreview, invalidateProposalPanelFetches])

  useEffect(() => {
    scrollToBottomIfPinned()
  }, [messages, scrollToBottomIfPinned])

  const reloadMessagesAfterStream = useCallback(
    async (id: string) => {
      const task = (async () => {
        const rows = await api.listMessages(id)
        setMessages((prev) => mergeMessagesFromApi(rows, prev))
        if (selectedId) {
          void refreshChatHistory(selectedId)
        }
      })()
      reloadInFlightRef.current = task
      try {
        await task
      } finally {
        if (reloadInFlightRef.current === task) {
          reloadInFlightRef.current = null
        }
      }
    },
    [refreshChatHistory, selectedId],
  )

  const stopStreaming = async () => {
    const runId = runIdRef.current ?? activeRunId
    if (!runId || !chatId) return

    try {
      await api.cancelRun(runId)
    } catch {
      /* idempotent */
    }

    streamAbortRef.current?.abort()

    try {
      await reloadMessagesAfterStream(chatId)
    } finally {
      setLoading(false)
      setProposalTurnSyncing(false)
      setActiveRunId(null)
      runIdRef.current = null
    }
  }

  const send = async () => {
    if (!chatId || !input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setLoading(true)
    setProposalTurnSyncing(false)
    previewFreshFromStreamRef.current = false
    pinToBottomRef.current = true
    setError(null)

    streamAbortRef.current?.abort()

    if (reloadInFlightRef.current) {
      try {
        await reloadInFlightRef.current
      } catch {
        /* reload may fail; still attempt send */
      }
    }

    setMessages((prev) => {
      const nextSequence = prev.reduce((max, row) => Math.max(max, row.sequence), 0) + 1
      const optimistic: Message = {
        id: `tmp-${Date.now()}`,
        chat_id: chatId,
        role: 'user',
        message_type: 'text',
        content: text,
        metadata: {},
        parent_id: null,
        sequence: nextSequence,
        created_at: new Date().toISOString(),
      }
      return [...prev, optimistic]
    })

    const generation = ++streamGenRef.current
    const abortController = new AbortController()
    streamAbortRef.current = abortController

    let segmentText = ''
    let reloadedAfterStream = false
    runIdRef.current = null
    setActiveRunId(null)

    const finishTurnAfterStream = async () => {
      if (generation !== streamGenRef.current || reloadedAfterStream) return
      reloadedAfterStream = true
      try {
        const previewTasks: Promise<void>[] = [reloadMessagesAfterStream(chatId)]
        if (isProposalComposer && chatId && !previewFreshFromStreamRef.current) {
          previewTasks.push(fetchProposalPreview(chatId))
        }
        await Promise.all(previewTasks)
        if (isProposalComposer && chatId && proposalPanelTabRef.current === 'state') {
          await fetchProposalState(chatId)
        }
      } finally {
        if (generation === streamGenRef.current) {
          setProposalTurnSyncing(false)
          setLoading(false)
          setActiveRunId(null)
          runIdRef.current = null
        }
      }
    }

    try {
      await streamChat(
        chatId,
        text,
        (ev) => {
          if (generation !== streamGenRef.current) return

          if (ev.event === 'memory_updated') {
            setMemoryRefreshKey((k) => k + 1)
          }
          if (ev.event === 'run_started' && ev.data.run_id != null) {
            const id = String(ev.data.run_id)
            runIdRef.current = id
            setActiveRunId(id)
          }
          if (ev.event === 'text' && typeof ev.data.text === 'string') {
            const chunk = ev.data.text
            if (
              segmentText === '' ||
              (chunk.length >= segmentText.length && chunk.startsWith(segmentText))
            ) {
              segmentText = chunk
            } else if (chunk) {
              segmentText += chunk
            }
            setMessages((prev) => applyStreamText(prev, chatId, segmentText))
          }
          if (ev.event === 'reasoning_done') {
            setMessages((prev) => finalizeStreamReasoning(prev))
          }
          if (ev.event === 'viz' && ev.data.spec && typeof ev.data.spec === 'object') {
            const spec = ev.data.spec as VizSpec
            setMessages((prev) => applyStreamViz(prev, chatId, spec))
          }
          if (ev.event === 'artifact' && ev.data.spec && typeof ev.data.spec === 'object') {
            const spec = ev.data.spec as ArtifactSpec
            setMessages((prev) => applyStreamArtifact(prev, chatId, spec))
          }
          if (ev.event === 'proposal_updated') {
            const preview = parseProposalPreview(ev.data)
            if (preview) {
              applyProposalPreview(preview, chatId)
            }
            if (proposalPanelTabRef.current === 'state' && chatId) {
              void fetchProposalState(chatId)
            }
          }
          const proposalDraftWriteTools = new Set([
            'initialize_proposal_draft',
            'patch_proposal_draft',
            'add_package_to_proposal_draft',
            'add_service_to_proposal_draft',
            'enable_proposal_draft_section',
          ])
          if (
            ev.event === 'tool_result' &&
            proposalDraftWriteTools.has(String(ev.data?.tool_name || '')) &&
            chatId &&
            isProposalComposer
          ) {
            const result = parseToolResultObject(ev.data?.result)
            if (result) {
              const draft = result.draft
              if (draft && typeof draft === 'object' && !Array.isArray(draft)) {
                setProposalState(draft as Record<string, unknown>)
              }
            }
            if (proposalPanelTabRef.current === 'state') {
              void fetchProposalState(chatId)
            }
          }
          if (ev.event === 'reasoning' && typeof ev.data.text === 'string') {
            setMessages((prev) => applyStreamReasoning(prev, chatId, ev.data.text as string))
          }
          if (ev.event === 'tool_call' && ev.data) {
            segmentText = ''
            setMessages((prev) => applyStreamToolCall(prev, chatId, ev.data))
          }
          if (ev.event === 'tool_result' && ev.data) {
            segmentText = ''
            setMessages((prev) => applyStreamToolResult(prev, chatId, ev.data))
          }
          if (ev.event === 'error') {
            throw new Error(String(ev.data.error ?? 'stream error'))
          }
        },
        abortController.signal,
      )

      if (generation !== streamGenRef.current) return
      await finishTurnAfterStream()
    } catch (e) {
      if (generation !== streamGenRef.current) return
      if (e instanceof Error && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : 'Failed to send message')
      try {
        await reloadMessagesAfterStream(chatId)
      } catch {
        /* ignore reload failure */
      }
      setProposalTurnSyncing(false)
      setLoading(false)
      setActiveRunId(null)
      runIdRef.current = null
    } finally {
      if (generation === streamGenRef.current && streamAbortRef.current === abortController) {
        streamAbortRef.current = null
      }
    }
  }

  const startNewChat = async () => {
    if (!selectedId || loading || chatSessionLoading) return
    setHistoryOpen(false)
    invalidateProposalPanelFetches()
    setProposalPreview(null)
    setProposalPreviewError(null)
    setProposalState(null)
    setProposalStateFingerprint(null)
    setProposalStateError(null)
    setProposalPanelTab('preview')
    setError(null)
    setChatSessionLoading(true)
    setMessages([])
    setInput('')
    try {
      const chat = await api.createChat(selectedId)
      setStoredChatId(selectedId, chat.id)
      setChatId(chat.id)
      await refreshChatHistory(selectedId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start new chat')
    } finally {
      setChatSessionLoading(false)
    }
  }

  const openHistoryChat = async (id: string) => {
    if (!selectedId || loading) return
    setHistoryOpen(false)
    try {
      await openChatById(selectedId, id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load conversation')
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <aside
        className={`agent-sidebar flex shrink-0 flex-col border-r border-border bg-surface-raised ${
          sidebarCollapsed ? 'agent-sidebar-collapsed' : ''
        }`}
      >
        <div
          className={`sidebar-brand-wrap${sidebarCollapsed ? ' sidebar-brand-wrap-collapsed' : ''}`}
        >
          <h1
            className="sidebar-brand"
            aria-label="Agent Platform"
            title={sidebarCollapsed ? 'Agent Platform' : undefined}
          >
            <img src="/cow.png" alt="" className="sidebar-brand-icon" />
            {!sidebarCollapsed && (
              <>
                <span className="sidebar-brand-agent">Agent</span>{' '}
                <span className="sidebar-brand-platform">Platform</span>
              </>
            )}
          </h1>
        </div>

        {!sidebarCollapsed && (
          <div className="px-4 pb-1 pt-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-subtle">
              Agents
            </p>
          </div>
        )}

        <ul
          className={`min-h-0 flex-1 overflow-y-auto pb-2 ${sidebarCollapsed ? 'px-1.5 pt-2' : 'px-2'}`}
        >
          {agentsLoading && !sidebarCollapsed && (
            <li className="px-2 py-3 text-[11px] text-muted">Loading…</li>
          )}
          {agentsError && !sidebarCollapsed && (
            <li className="space-y-2 px-2 py-3">
              <p className="text-[11px] leading-relaxed text-brand-700">
                Failed to load agents: {agentsError}
              </p>
              <p className="text-[10px] text-muted">
                Make sure the backend is running (http://127.0.0.1:8000)
              </p>
              <button
                type="button"
                className="btn btn-secondary text-[10px]"
                onClick={() => void loadAgents({ autoSelect: true })}
              >
                Retry
              </button>
            </li>
          )}
          {!agentsLoading && !agentsError && agents.length === 0 && !sidebarCollapsed && (
            <li className="px-2 py-3 text-[11px] leading-relaxed text-muted">
              No agents found. Add a directory and profile.yaml under backend/agents/, then restart
              the backend.
            </li>
          )}
          {!agentsLoading &&
            agents.map((agent) => {
            const active = agent.id === selectedId
            return (
              <li key={agent.id} className="mb-0.5">
                <button
                  type="button"
                  onClick={() => void selectAgent(agent)}
                  title={sidebarCollapsed ? formatAgentSlugLabel(agent) : undefined}
                  className={`agent-nav-item ${active ? 'agent-nav-item-active' : ''} ${
                    sidebarCollapsed ? 'agent-nav-item-collapsed' : ''
                  }`}
                >
                  <AgentIcon className="h-[18px] w-[18px] shrink-0" />
                  {!sidebarCollapsed && (
                    <span className="agent-nav-label">{formatAgentSlugLabel(agent)}</span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>

        <div className="agent-sidebar-footer">
          <div
            className="agent-sidebar-user"
            title={userEmail ?? undefined}
          >
            <span className="agent-sidebar-avatar">
              <UserIcon className="h-4 w-4" />
            </span>
            {!sidebarCollapsed && userEmail && (
              <span className="agent-sidebar-email">{userEmail}</span>
            )}
          </div>
          <button
            type="button"
            className="agent-sidebar-toggle-btn"
            onClick={toggleSidebar}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={sidebarCollapsed ? 'Expand' : 'Collapse'}
          >
            <SidebarToggleIcon collapsed={sidebarCollapsed} />
          </button>
        </div>
      </aside>

      <section className="chat-main flex min-w-0 flex-1 flex-col">
        {showChat && selected ? (
          <div className={`chat-main-layout${isProposalComposer ? ' chat-main-layout-proposal' : ''}`}>
            <div className="chat-main-inner">
            <div className="chat-header">
              <div className="chat-header-brand">
                <AgentIcon className="chat-header-icon h-[18px] w-[18px] shrink-0" />
                <h1 className="chat-header-title">{selected.name}</h1>
              </div>
              <div className="chat-header-actions">
                <div className="chat-header-action-wrap">
                  <button
                    type="button"
                    className={`chat-header-btn${chatSessionLoading ? ' chat-header-btn-busy' : ''}`}
                    aria-label="New Chat"
                    aria-busy={chatSessionLoading}
                    disabled={loading || chatSessionLoading}
                    onClick={() => void startNewChat()}
                  >
                    <NewChatIcon className="chat-header-action-icon" />
                  </button>
                  <span className="chat-header-tooltip">New Chat</span>
                </div>
                <div className="chat-header-action-wrap">
                  <button
                    type="button"
                    className={`chat-header-btn ${memoryOpen ? 'chat-header-btn-active' : ''}`}
                    aria-label="Memory"
                    aria-expanded={memoryOpen}
                    onClick={() => {
                      setMemoryOpen((open) => {
                        const next = !open
                        if (next) {
                          setHistoryOpen(false)
                        }
                        return next
                      })
                    }}
                  >
                    <img src="/alzheimer.png" alt="" className="chat-header-action-icon chat-header-memory-icon" />
                  </button>
                  <span className="chat-header-tooltip">Memory</span>
                </div>
                <div className="chat-header-action-wrap">
                  <button
                    type="button"
                    className={`chat-header-btn ${historyOpen ? 'chat-header-btn-active' : ''}`}
                    aria-label="Chat History"
                    aria-expanded={historyOpen}
                    onClick={() => {
                      setHistoryOpen((open) => {
                        const next = !open
                        if (next) {
                          setMemoryOpen(false)
                          if (selectedId) void refreshChatHistory(selectedId)
                        }
                        return next
                      })
                    }}
                  >
                    <ChatHistoryIcon className="chat-header-action-icon" />
                  </button>
                  <span className="chat-header-tooltip">Chat History</span>
                </div>
              </div>
            </div>

            <div className="chat-body-frame">
              <div className="chat-body-white">
                <div
                  ref={messagesScrollRef}
                  className="chat-messages-scroll"
                  onScroll={updateScrollPin}
                >
                  <div className="chat-content-column">
                    {chatSessionLoading ? (
                      <div
                        className="chat-session-loading"
                        aria-live="polite"
                        aria-label="Loading"
                      >
                        <LoadingSpinner size="lg" />
                      </div>
                    ) : (
                      <>
                        {messages.length === 0 && (
                          <div className="chat-messages-empty">
                            Send a message to start a conversation
                          </div>
                        )}
                        <ChatMessageList
                          messages={messages}
                          loading={loading}
                          liveProposalOpen={isProposalComposer && !proposalPanelCollapsed}
                          onExpandArtifact={handleExpandArtifact}
                        />
                      </>
                    )}
                  </div>
                </div>

                {error && (
                  <p className="chat-error-bar text-center text-[11px] text-brand-700">
                    <span className="chat-content-column inline-block">{error}</span>
                  </p>
                )}

                <div className="chat-composer-wrap">
                  <div className="chat-content-column">
                    <div className="chat-composer">
                      <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.nativeEvent.isComposing || e.keyCode === 229) {
                            return
                          }
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            if (!loading && !chatSessionLoading) void send()
                          }
                        }}
                        placeholder="question"
                        className="chat-composer-textarea"
                        disabled={loading || chatSessionLoading}
                      />
                      <div className="chat-composer-footer">
                        <button
                          type="button"
                          className="chat-composer-add"
                          disabled={loading || chatSessionLoading}
                          aria-label="Add attachment"
                          title="Coming soon"
                        >
                          +
                        </button>
                        <button
                          type="button"
                          onClick={() => (loading ? void stopStreaming() : void send())}
                          disabled={
                            chatSessionLoading || (loading ? !activeRunId : !input.trim())
                          }
                          className={`chat-send-btn${loading ? ' chat-send-btn-stop' : ''}`}
                          aria-label={loading ? 'Stop generating' : 'Send'}
                          title={loading ? 'Stop' : 'Send'}
                        >
                          {loading ? (
                            <svg
                              width="16"
                              height="16"
                              viewBox="0 0 24 24"
                              fill="currentColor"
                              aria-hidden
                            >
                              <rect x="5" y="5" width="14" height="14" rx="2" />
                            </svg>
                          ) : (
                            <svg
                              width="16"
                              height="16"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2.25"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden
                            >
                              <path d="M12 19V5" />
                              <path d="m5 12 7-7 7 7" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            </div>

            {isProposalComposer && (
              <ProposalPanelShell
                open={!proposalPanelCollapsed}
                width={proposalPanelWidth}
                activeTab={proposalPanelTab}
                syncing={proposalTurnSyncing}
                onTabChange={handleProposalPanelTabChange}
                onWidthChange={setProposalPanelWidth}
                onExpand={expandProposalPanel}
              >
                {proposalPanelTab === 'preview' ? (
                  <ProposalLivePanel
                    open
                    embedded
                    preview={proposalPreview}
                    loading={proposalPreviewLoading}
                    syncing={proposalTurnSyncing}
                    error={proposalPreviewError}
                    onCollapse={collapseProposalPanel}
                    onRefresh={() => {
                      if (chatId) void fetchProposalPreview(chatId)
                    }}
                  />
                ) : (
                  <ProposalStatePanel
                    open
                    embedded
                    state={proposalState}
                    fingerprint={proposalStateFingerprint}
                    loading={proposalStateLoading}
                    syncing={proposalTurnSyncing}
                    error={proposalStateError}
                    onCollapse={collapseProposalPanel}
                    onRefresh={() => {
                      if (chatId) void fetchProposalState(chatId)
                    }}
                  />
                )}
              </ProposalPanelShell>
            )}

            <MemoryPanel
              open={memoryOpen}
              agents={agents}
              activeAgentId={selected.id}
              refreshKey={memoryRefreshKey}
              onClose={() => setMemoryOpen(false)}
            />
            <ChatHistoryPanel
              open={historyOpen}
              chats={chatHistory}
              activeChatId={chatId}
              loading={chatHistoryLoading}
              onClose={() => setHistoryOpen(false)}
              onSelect={(id) => void openHistoryChat(id)}
            />
          </div>
        ) : (
          <div className="chat-main-placeholder">
            {agentsLoading ? (
              <LoadingSpinner size="lg" />
            ) : (
              <>
                <p className="chat-main-placeholder-title">Select an agent to start chatting</p>
                <p className="chat-main-placeholder-subtitle">
                  Agents are loaded from backend/agents/ profiles
                </p>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
