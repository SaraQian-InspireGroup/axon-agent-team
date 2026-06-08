import type { Message } from '../types'
import { MarkdownContent } from './MarkdownContent'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  if (message.message_type === 'run_cancelled') {
    return (
      <div className="flex justify-center">
        <p className="chat-cancel-notice">{message.content}</p>
      </div>
    )
  }

  if (message.message_type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="msg-assistant max-w-[78%] rounded-sm border border-brand-200 px-3 py-2 text-[12px] text-brand-700">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.message_type === 'cancelled' && message.metadata?.original_type === 'text') {
    return (
      <div className="flex justify-start">
        <div className="msg-assistant msg-assistant-cancelled max-w-[78%] rounded-sm px-3 py-2 text-[12px] leading-relaxed">
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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[78%] rounded-sm px-3 py-2 text-[12px] leading-relaxed ${
          isUser ? 'msg-user' : 'msg-assistant'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <MarkdownContent content={message.content ?? ''} />
            {streaming && (
              <span className="mt-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" />
            )}
          </>
        )}
      </div>
    </div>
  )
}
