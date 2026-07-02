import { useEffect, useRef, type KeyboardEvent } from 'react'
import {
  ArrowUp,
  List,
  MessageSquarePlus,
  Pause,
  X,
} from 'lucide-react'
import { useAgentChat } from '../../hooks/useAgentChat'
import { usePanelResize } from '../../hooks/usePanelResize'

interface AgentChatPanelProps {
  width: number
  onWidthChange: (width: number) => void
  onClose: () => void
}

export default function AgentChatPanel({
  width,
  onWidthChange,
  onClose,
}: AgentChatPanelProps) {
  const {
    historySessions,
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
  } = useAgentChat()

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
  }, [activeSession?.messages, isStreaming])

  const handleSubmit = () => {
    if (isStreaming) {
      pauseStreaming()
      return
    }
    sendMessage()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

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
          <button
            type="button"
            className={`agent-chat-header-btn${historyOpen ? ' agent-chat-header-btn-active' : ''}`}
            aria-label="历史会话"
            onClick={() => setHistoryOpen((value) => !value)}
          >
            <List size={18} />
          </button>
          <button
            type="button"
            className="agent-chat-header-btn"
            aria-label="新建会话"
            onClick={startNewSession}
          >
            <MessageSquarePlus size={18} />
          </button>
          <button
            type="button"
            className="agent-chat-header-btn"
            aria-label="关闭对话窗口"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="agent-chat-body">
        {historyOpen ? (
          <div className="agent-chat-history">
            <div className="agent-chat-history-title">历史会话</div>
            {[...historySessions].map((session) => (
              <button
                key={session.id}
                type="button"
                className="agent-chat-history-item"
                onClick={() => loadSession(session.id)}
              >
                <span className="agent-chat-history-item-title">{session.title}</span>
                <span className="agent-chat-history-item-time">{session.updatedAt}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="agent-chat-messages">
            {activeSession?.messages.map((message) => (
              <div
                key={message.id}
                className={`agent-chat-message agent-chat-message-${message.role}`}
              >
                <div className="agent-chat-message-bubble">{message.content}</div>
              </div>
            ))}
            {isStreaming ? (
              <div className="agent-chat-message agent-chat-message-assistant">
                <div className="agent-chat-message-bubble agent-chat-typing">
                  正在思考...
                </div>
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>
        )}
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
            disabled={isStreaming}
          />
          <button
            type="button"
            className="agent-chat-send-btn"
            aria-label={isStreaming ? '暂停' : '发送'}
            onClick={handleSubmit}
            disabled={!isStreaming && !input.trim()}
          >
            {isStreaming ? <Pause size={16} fill="currentColor" /> : <ArrowUp size={16} />}
          </button>
        </div>
      </div>
    </aside>
  )
}
