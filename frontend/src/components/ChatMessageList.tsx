import { ProcessStepCard } from './ProcessStepCard'
import { MessageBubble } from './MessageBubble'
import { VizBubble } from './VizBubble'
import { ArtifactBubble } from './ArtifactBubble'
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
  if (block.kind === 'viz') {
    return (
      <div key={key} className="chat-viz-row">
        <VizBubble spec={block.spec} />
      </div>
    )
  }
  if (block.kind === 'artifact') {
    return (
      <div key={key} className="chat-artifact-row">
        <ArtifactBubble spec={block.spec} />
      </div>
    )
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
        renderBlock(
          block,
          block.kind === 'bubble' ? block.message.id : `${block.kind}-${block.id}-${index}`,
        ),
      )}
      {showPending && <PendingIndicator />}
    </div>
  )
}
