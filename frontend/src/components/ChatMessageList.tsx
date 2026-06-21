import { ProcessStepCard } from './ProcessStepCard'
import { MessageBubble } from './MessageBubble'
import { VizBubble } from './VizBubble'
import { ArtifactBubble } from './ArtifactBubble'
import { groupMessages, shouldShowPendingIndicator, type ChatBlock } from '../lib/messageActivity'
import type { ArtifactSpec } from '../types/artifact'
import type { Message } from '../types'

type Props = {
  messages: Message[]
  loading?: boolean
  turnSyncHint?: string | null
  liveProposalOpen?: boolean
  onExpandArtifact?: (spec: ArtifactSpec) => void
}

function PendingIndicator({ hint }: { hint?: string | null }) {
  return (
    <div
      className="chat-pending-row"
      aria-live="polite"
      aria-label={hint ?? 'Assistant is working'}
    >
      <span className="chat-pending-dot" />
      {hint ? <span className="chat-pending-hint">{hint}</span> : null}
    </div>
  )
}

function renderBlock(
  block: ChatBlock,
  key: string,
  liveProposalOpen?: boolean,
  onExpandArtifact?: (spec: ArtifactSpec) => void,
) {
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
        <ArtifactBubble
          spec={block.spec}
          expanded={Boolean(liveProposalOpen)}
          onExpand={onExpandArtifact}
        />
      </div>
    )
  }
  return (
    <div key={key} className="chat-process-row">
      <ProcessStepCard item={block.item} />
    </div>
  )
}

export function ChatMessageList({
  messages,
  loading = false,
  turnSyncHint = null,
  liveProposalOpen = false,
  onExpandArtifact,
}: Props) {
  const blocks = groupMessages(messages)
  const showPending = shouldShowPendingIndicator(loading, messages)
  const showSyncStatus = Boolean(turnSyncHint)

  return (
    <div className="chat-timeline">
      {blocks.map((block, index) =>
        renderBlock(
          block,
          block.kind === 'bubble' ? block.message.id : `${block.kind}-${block.id}-${index}`,
          liveProposalOpen,
          onExpandArtifact,
        ),
      )}
      {(showPending || showSyncStatus) && (
        <PendingIndicator hint={showSyncStatus ? turnSyncHint : null} />
      )}
    </div>
  )
}
