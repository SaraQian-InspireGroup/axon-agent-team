import { useEffect, useRef, type KeyboardEvent } from 'react'
import { ArrowUp, List, MessageSquarePlus, Pause, X } from 'lucide-react'
import { ChatMessageList } from '../nova/ChatMessageList'
import NovaHistoryDropdown from '../nova/NovaHistoryDropdown'
import type { useNovaChat } from '../../hooks/useNovaChat'
import { usePanelResize } from '../../hooks/usePanelResize'

type NovaChatState = ReturnType<typeof useNovaChat>

interface AgentChatPanelProps {
  width: number
  onWidthChange: (width: number) => void
  onClose: () => void
  chat: NovaChatState
}

export default function AgentChatPanel({
  width,
  onWidthChange,
  onClose,
  chat,
}: AgentChatPanelProps) {
  const {
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
  } = chat

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const maxWidth = typeof window !== 'undefined' ? window.innerWidth * 0.4 : 640

  const { onResizeStart } = usePanelResize({
    width,
    onWidthChange,
    minWidth: 320,
    maxWidth,
    edge: 'left',
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, turnSyncHint])

  const handleSubmit = () => {
    if (loading) {
      void stopStreaming()
      return
    }
    void sendMessage()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

  const panelError = agentError ?? error
  const isBusy = loading || chatSessionLoading

  return (
    <aside className="agent-chat-panel" style={{ width }}>
      <button
        type="button"
        className="agent-chat-resize-handle"
        aria-label="调整对话窗口宽度"
        onMouseDown={onResizeStart}
      />

      <div className="agent-chat-header">
        <div className="agent-chat-header-title">
          <span className="agent-chat-header-icon">
            <img src="/artificial-intellegence.png" alt="" className="agent-chat-header-icon-img" />
          </span>
          <span>Nova</span>
        </div>
        <div className="agent-chat-header-actions">
          <div className="agent-chat-header-action-wrap">
            <button
              type="button"
              className={`agent-chat-header-btn${historyOpen ? ' agent-chat-header-btn-active' : ''}`}
              aria-label="历史会话"
              aria-expanded={historyOpen}
              onClick={() => toggleHistoryOpen()}
            >
              <List size={18} />
            </button>
            <NovaHistoryDropdown
              open={historyOpen}
              chats={chatHistory}
              activeChatId={chatId}
              loading={chatHistoryLoading}
              onClose={closeHistory}
              onSelect={(id) => void loadHistorySession(id)}
            />
          </div>
          <button
            type="button"
            className="agent-chat-header-btn"
            aria-label="新建会话"
            onClick={() => {
              closeHistory()
              void startNewSession()
            }}
            disabled={isBusy || Boolean(agentError)}
          >
            <MessageSquarePlus size={18} />
          </button>
          <button type="button" className="agent-chat-header-btn" aria-label="关闭对话窗口" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="agent-chat-body">
        <div className="agent-chat-messages">
          {agentError ? <div className="agent-chat-error-banner">{agentError}</div> : null}
          {chatSessionLoading && messages.length === 0 ? (
            <div className="agent-chat-history-empty">加载会话中…</div>
          ) : (
            <>
              <ChatMessageList messages={messages} loading={loading} turnSyncHint={turnSyncHint} />
              {panelError && !agentError ? (
                <div className="agent-chat-error-banner">{panelError}</div>
              ) : null}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="agent-chat-composer">
        <div className="agent-chat-input-wrap">
          <textarea
            className="agent-chat-input"
            rows={3}
            placeholder="question"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={Boolean(agentError) || (loading && !chatId)}
          />
          <button
            type="button"
            className="agent-chat-send-btn"
            aria-label={loading ? '暂停' : '发送'}
            onClick={handleSubmit}
            disabled={Boolean(agentError) || (!loading && !input.trim())}
          >
            {loading ? <Pause size={16} fill="currentColor" /> : <ArrowUp size={16} />}
          </button>
        </div>
      </div>
    </aside>
  )
}
