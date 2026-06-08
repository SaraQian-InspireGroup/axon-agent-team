import { ProcessStepCard } from './ProcessStepCard'
import { MessageBubble } from './MessageBubble'
import { groupMessages, shouldShowPendingIndicator, type ChatBlock } from '../lib/messageActivity'
import type { Message } from '../types'

type Props = {
  messages: Message[]
  streamingBlocks?: ChatBlock[]
  loading?: boolean
}

function PendingIndicator() {
  return (
    <div className="chat-pending-row" aria-live="polite" aria-label="Assistant is working">
      <span className="chat-pending-dot" />
    </div>
  )
}

function renderBlock(block: ChatBlock, key: string) {
  if (block.kind === 'bubble') {
    return <MessageBubble key={key} message={block.message} />
  }
  return (
    <div key={key} className="chat-process-row">
      <ProcessStepCard item={block.item} />
    </div>
  )
}

export function ChatMessageList({ messages, streamingBlocks = [], loading = false }: Props) {
  const blocks = [...groupMessages(messages), ...streamingBlocks]
  const showPending = shouldShowPendingIndicator(loading, streamingBlocks)

  return (
    <div className="chat-timeline">
      {blocks.map((block, index) =>
        renderBlock(block, block.kind === 'bubble' ? block.message.id : `${block.id}-${index}`),
      )}
      {showPending && <PendingIndicator />}
    </div>
  )
}
