import { ProcessStepCard } from './ProcessStepCard'
import { MessageBubble } from './MessageBubble'
import { VizBubble } from './VizBubble'
import { ArtifactBubble } from './ArtifactBubble'
import { groupMessages, shouldShowPendingIndicator, type ChatBlock } from '../lib/messageActivity'
import { isProposalArtifact } from '../lib/artifactDownload'
import type { ArtifactSpec } from '../types/artifact'
import type { Message } from '../types'

type Props = {
  messages: Message[]
  loading?: boolean
  turnSyncHint?: string | null
  proposalPanelOpen?: boolean
  expandedArtifactId?: string | null
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

function isArtifactExpanded(
  spec: ArtifactSpec,
  proposalPanelOpen?: boolean,
  expandedArtifactId?: string | null,
): boolean {
  if (expandedArtifactId && spec.artifact_id === expandedArtifactId) return true
  if (proposalPanelOpen && isProposalArtifact(spec)) return true
  return false
}

function renderBlock(
  block: ChatBlock,
  key: string,
  proposalPanelOpen?: boolean,
  expandedArtifactId?: string | null,
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
          expanded={isArtifactExpanded(block.spec, proposalPanelOpen, expandedArtifactId)}
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
  proposalPanelOpen = false,
  expandedArtifactId = null,
  onExpandArtifact,
}: Props) {
  const blocks = groupMessages(messages, { streaming: loading })
  const showPending = shouldShowPendingIndicator(loading, messages)
  const showSyncStatus = Boolean(turnSyncHint)

  return (
    <div className="chat-timeline">
      {blocks.map((block, index) =>
        renderBlock(
          block,
          block.kind === 'bubble' ? block.message.id : `${block.kind}-${block.id}-${index}`,
          proposalPanelOpen,
          expandedArtifactId,
          onExpandArtifact,
        ),
      )}
      {(showPending || showSyncStatus) && (
        <PendingIndicator hint={showSyncStatus ? turnSyncHint : null} />
      )}
    </div>
  )
}
