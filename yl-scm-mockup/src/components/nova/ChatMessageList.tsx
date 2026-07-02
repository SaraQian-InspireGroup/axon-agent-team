import { ProcessStepCard } from './ProcessStepCard'
import { MessageBubble } from './MessageBubble'
import { groupMessages, shouldShowPendingIndicator, type ChatBlock } from '../../lib/messageActivity'
import type { Message } from '../../types/agent'

interface Props {
  messages: Message[]
  loading?: boolean
  turnSyncHint?: string | null
}

function PendingIndicator({ hint }: { hint?: string | null }) {
  return (
    <div className="nova-chat-pending-row" aria-live="polite">
      <span className="nova-chat-pending-dot" />
      {hint ? <span className="nova-chat-pending-hint">{hint}</span> : null}
    </div>
  )
}

function renderBlock(block: ChatBlock, key: string) {
  if (block.kind === 'bubble') {
    return <MessageBubble key={key} message={block.message} />
  }
  return (
    <div key={key} className="nova-chat-process-row">
      <ProcessStepCard item={block.item} />
    </div>
  )
}

export function ChatMessageList({ messages, loading = false, turnSyncHint = null }: Props) {
  const blocks = groupMessages(messages, { streaming: loading })
  const showPending = shouldShowPendingIndicator(loading, messages)
  const showSyncStatus = Boolean(turnSyncHint)

  return (
    <div className="nova-chat-timeline">
      {blocks.map((block, index) =>
        renderBlock(
          block,
          block.kind === 'bubble' ? block.message.id : `${block.kind}-${block.id}-${index}`,
        ),
      )}
      {(showPending || showSyncStatus) && (
        <PendingIndicator hint={showSyncStatus ? turnSyncHint : null} />
      )}
    </div>
  )
}
