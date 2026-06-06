import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from '../api/client'
import { AgentIcon } from '../components/AgentIcon'
import { ChatHistoryPanel } from '../components/ChatHistoryPanel'
import { ChatHistoryIcon } from '../components/ChatHistoryIcon'
import { ChatMessageList } from '../components/ChatMessageList'
import { NewChatIcon } from '../components/NewChatIcon'
import { SidebarToggleIcon } from '../components/SidebarToggleIcon'
import { UserIcon } from '../components/UserIcon'
import { formatAgentSlugLabel } from '../lib/agentLabel'
import { getStoredChatId, setStoredChatId } from '../lib/chatStorage'
import {
  applyStreamingBlockActivity,
  applyStreamingText,
  createStreamingActivityEntry,
  finalizeStreamingReasoning,
  type ChatBlock,
} from '../lib/messageActivity'
import type { Agent, ChatSummary, Message } from '../types'

const SIDEBAR_COLLAPSED_KEY = 'agent-platform:sidebar-collapsed'

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
  const [streamingBlocks, setStreamingBlocks] = useState<ChatBlock[]>([])
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatSummary[]>([])
  const [chatHistoryLoading, setChatHistoryLoading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

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

  const selected = agents.find((a) => a.id === selectedId) ?? null

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
    setChatId(id)
    setStoredChatId(agentId, id)
    setStreamingBlocks([])
    setInput('')
    const rows = await api.listMessages(id)
    setMessages(rows)
  }, [])

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
      setStreamingBlocks([])
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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingBlocks])

  const send = async () => {
    if (!chatId || !input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setLoading(true)
    setStreamingBlocks([])
    setError(null)

    const optimistic: Message = {
      id: `tmp-${Date.now()}`,
      chat_id: chatId,
      role: 'user',
      message_type: 'text',
      content: text,
      metadata: {},
      parent_id: null,
      sequence: messages.length + 1,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimistic])

    let segmentText = ''
    try {
      await streamChat(chatId, text, (ev) => {
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
          setStreamingBlocks((prev) => applyStreamingText(prev, segmentText))
        }
        if (ev.event === 'reasoning_done') {
          setStreamingBlocks((prev) => finalizeStreamingReasoning(prev))
        }
        if (
          (ev.event === 'reasoning' ||
            ev.event === 'tool_call' ||
            ev.event === 'tool_result') &&
          ev.data
        ) {
          if (ev.event === 'tool_call' || ev.event === 'tool_result') {
            segmentText = ''
          }
          const entry = createStreamingActivityEntry(
            ev.event as 'reasoning' | 'tool_call' | 'tool_result',
            ev.data,
          )
          if (entry) {
            setStreamingBlocks((prev) => applyStreamingBlockActivity(prev, entry))
          }
        }
        if (ev.event === 'error') {
          throw new Error(String(ev.data.error ?? 'stream error'))
        }
      })
      const rows = await api.listMessages(chatId)
      setMessages(rows)
      setStreamingBlocks([])
      if (selectedId) {
        await refreshChatHistory(selectedId)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message')
      setStreamingBlocks([])
    } finally {
      setLoading(false)
    }
  }

  const startNewChat = async () => {
    if (!selectedId || loading) return
    setHistoryOpen(false)
    setError(null)
    try {
      const chat = await api.createChat(selectedId)
      setStoredChatId(selectedId, chat.id)
      setChatId(chat.id)
      setMessages([])
      setStreamingBlocks([])
      setInput('')
      await refreshChatHistory(selectedId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start new chat')
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
        {!sidebarCollapsed && (
          <div className="sidebar-brand-wrap">
            <h1 className="sidebar-brand">
              <span className="sidebar-brand-agent">Agent</span>{' '}
              <span className="sidebar-brand-platform">Platform</span>
            </h1>
          </div>
        )}

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
                无法加载 Agent 列表：{agentsError}
              </p>
              <p className="text-[10px] text-muted">请确认后端已启动（http://127.0.0.1:8000）</p>
              <button
                type="button"
                className="btn btn-secondary text-[10px]"
                onClick={() => void loadAgents({ autoSelect: true })}
              >
                重试
              </button>
            </li>
          )}
          {!agentsLoading && !agentsError && agents.length === 0 && !sidebarCollapsed && (
            <li className="px-2 py-3 text-[11px] leading-relaxed text-muted">
              未发现 Agent。请在 backend/agents/ 下添加目录和 profile.yaml，然后重启后端。
            </li>
          )}
          {agents.map((agent) => {
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
            title={sidebarCollapsed ? '展开' : '折叠'}
          >
            <SidebarToggleIcon collapsed={sidebarCollapsed} />
          </button>
        </div>
      </aside>

      <section className="chat-main flex min-w-0 flex-1 flex-col">
        {selected ? (
          <div className="chat-main-layout">
            <div className="chat-main-inner">
            <div className="chat-header">
              <div className="chat-header-brand">
                <AgentIcon className="chat-header-icon h-[18px] w-[18px] shrink-0" />
                <h1 className="chat-header-title">{selected.name}</h1>
              </div>
              <div className="chat-header-actions">
                <button
                  type="button"
                  className="chat-header-btn"
                  aria-label="New chat"
                  title="New chat"
                  disabled={loading}
                  onClick={() => void startNewChat()}
                >
                  <NewChatIcon />
                </button>
                <button
                  type="button"
                  className={`chat-header-btn ${historyOpen ? 'chat-header-btn-active' : ''}`}
                  aria-label="Chat history"
                  title="Chat history"
                  aria-expanded={historyOpen}
                  onClick={() => {
                    setHistoryOpen((open) => {
                      const next = !open
                      if (next && selectedId) {
                        void refreshChatHistory(selectedId)
                      }
                      return next
                    })
                  }}
                >
                  <ChatHistoryIcon />
                </button>
              </div>
            </div>

            <div className="chat-body-frame">
              <div className="chat-body-white">
                <div className="chat-messages-scroll">
                  <div className="chat-content-column">
                    {messages.length === 0 && streamingBlocks.length === 0 && (
                      <div className="flex h-full min-h-[12rem] items-center justify-center text-[12px] text-muted">
                        发送消息开始对话
                      </div>
                    )}
                    <ChatMessageList messages={messages} streamingBlocks={streamingBlocks} />
                    <div ref={bottomRef} />
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
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            void send()
                          }
                        }}
                        placeholder="question"
                        className="chat-composer-textarea"
                        disabled={loading}
                      />
                      <div className="chat-composer-footer">
                        <button
                          type="button"
                          className="chat-composer-add"
                          disabled={loading}
                          aria-label="Add attachment"
                          title="Coming soon"
                        >
                          +
                        </button>
                        <button
                          type="button"
                          onClick={() => void send()}
                          disabled={loading || !input.trim()}
                          className="chat-send-btn"
                          aria-label="Send"
                        >
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
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            </div>

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
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted">
            <p className="text-[13px]">选择一个 Agent 开始对话</p>
            <p className="text-[11px] text-subtle">左侧列表来自 backend/agents/ 下的 profile</p>
          </div>
        )}
      </section>
    </div>
  )
}
