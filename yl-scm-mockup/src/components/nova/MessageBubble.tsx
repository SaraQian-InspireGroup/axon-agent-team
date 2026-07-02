import type { Message } from '../../types/agent'
import { formatUserFacingError } from '../../lib/userFacingError'
import MarkdownContent from './MarkdownContent'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  if (message.message_type === 'run_cancelled') {
    return (
      <div className="nova-chat-cancel-row">
        <p className="nova-chat-cancel-notice">{message.content}</p>
      </div>
    )
  }

  if (message.message_type === 'error') {
    return (
      <div className="nova-chat-message-row nova-chat-message-row-assistant">
        <div className="nova-msg-assistant nova-msg-error">
          {formatUserFacingError(message.content, 'Assistant run failed')}
        </div>
      </div>
    )
  }

  if (message.message_type === 'cancelled' && message.metadata?.original_type === 'text') {
    return (
      <div className="nova-chat-message-row nova-chat-message-row-assistant">
        <div className="nova-msg-assistant nova-msg-cancelled">
          <MarkdownContent content={message.content ?? ''} />
        </div>
      </div>
    )
  }

  if (message.message_type !== 'text') {
    return null
  }

  const streaming = message.metadata?.streaming === true

  return (
    <div
      className={`nova-chat-message-row ${isUser ? 'nova-chat-message-row-user' : 'nova-chat-message-row-assistant'}`}
    >
      <div className={isUser ? 'nova-msg-user' : 'nova-msg-assistant'}>
        {isUser ? (
          <div className="nova-msg-content">{message.content}</div>
        ) : (
          <MarkdownContent content={message.content ?? ''} />
        )}
        {streaming ? <span className="nova-msg-stream-dot" aria-hidden /> : null}
      </div>
    </div>
  )
}
