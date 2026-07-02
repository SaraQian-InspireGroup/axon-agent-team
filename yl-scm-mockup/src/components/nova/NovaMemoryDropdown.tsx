import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { MemoryBullet, MemoryDocument } from '../../types/agent'

interface Props {
  open: boolean
  agentId: string | null
  refreshKey?: number
  onClose: () => void
}

type DraftState = {
  line: string
  isConstraint: boolean
}

function MemoryBulletList({
  bullets,
  saving,
  onRemove,
}: {
  bullets: MemoryBullet[]
  saving: boolean
  onRemove: (match: string) => void
}) {
  if (bullets.length === 0) {
    return <p className="nova-memory-empty">暂无记忆</p>
  }

  return (
    <ul className="nova-memory-list">
      {bullets.map((bullet) => (
        <li key={bullet.line} className="nova-memory-item">
          <span
            className={
              bullet.kind === 'constraint'
                ? 'nova-memory-badge nova-memory-badge-constraint'
                : 'nova-memory-badge'
            }
          >
            {bullet.kind === 'constraint' ? '约束' : '记忆'}
          </span>
          <span className="nova-memory-item-text">{bullet.text}</span>
          <button
            type="button"
            className="nova-memory-item-remove"
            disabled={saving}
            onClick={() => onRemove(bullet.text)}
            aria-label={`删除 ${bullet.text}`}
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  )
}

export default function NovaMemoryDropdown({ open, agentId, refreshKey = 0, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const [doc, setDoc] = useState<MemoryDocument | null>(null)
  const [draft, setDraft] = useState<DraftState>({ line: '', isConstraint: false })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    try {
      const next = await api.getAgentMemory(agentId)
      setDoc(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载记忆失败')
    } finally {
      setLoading(false)
    }
  }, [agentId])

  useEffect(() => {
    if (!open || !agentId) return
    void load()
  }, [open, agentId, load, refreshKey])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose])

  const handleAdd = async () => {
    if (!agentId) return
    const text = draft.line.trim()
    if (!text) return

    setSaving(true)
    setError(null)
    try {
      const updated = await api.appendMemory({
        scope: 'agent',
        agent_id: agentId,
        lines: [text],
        is_constraint: draft.isConstraint,
      })
      setDoc(updated)
      setDraft({ line: '', isConstraint: false })
    } catch (e) {
      setError(e instanceof Error ? e.message : '添加记忆失败')
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async (match: string) => {
    if (!agentId) return

    setSaving(true)
    setError(null)
    try {
      const updated = await api.removeMemory({
        scope: 'agent',
        agent_id: agentId,
        match,
      })
      setDoc(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除记忆失败')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div ref={panelRef} className="nova-memory-dropdown" role="dialog" aria-label="Nova 记忆">
      <div className="nova-memory-dropdown-header">
        <div className="nova-memory-dropdown-title-wrap">
          <img src="/alzheimer.png" alt="" className="nova-memory-dropdown-icon" width={18} height={18} />
          <span className="nova-memory-dropdown-title">Nova 记忆</span>
          <span className="nova-memory-dropdown-count">{doc?.bullets.length ?? 0}</span>
        </div>
        <button type="button" className="nova-memory-refresh-btn" disabled={loading || saving} onClick={() => void load()}>
          刷新
        </button>
      </div>

      <p className="nova-memory-hint">
        对话中说「记住 …」或「不要总是 …」也会写入；此处可手动维护 yl-worker1 专属记忆。
      </p>

      {error ? <p className="nova-memory-error">{error}</p> : null}

      <div className="nova-memory-dropdown-body">
        {loading ? (
          <p className="nova-memory-empty">加载中…</p>
        ) : (
          <>
            <MemoryBulletList bullets={doc?.bullets ?? []} saving={saving} onRemove={(match) => void handleRemove(match)} />
            <div className="nova-memory-add">
              <label className="nova-memory-add-label">
                <input
                  type="checkbox"
                  checked={draft.isConstraint}
                  onChange={(event) => setDraft((prev) => ({ ...prev, isConstraint: event.target.checked }))}
                />
                约束（[!]）
              </label>
              <div className="nova-memory-add-row">
                <input
                  type="text"
                  className="nova-memory-add-input"
                  placeholder={draft.isConstraint ? '例如：不要使用表格' : '例如：回复用中文'}
                  value={draft.line}
                  onChange={(event) => setDraft((prev) => ({ ...prev, line: event.target.value }))}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') void handleAdd()
                  }}
                  disabled={saving || !agentId}
                />
                <button
                  type="button"
                  className="nova-memory-add-btn"
                  disabled={saving || !draft.line.trim() || !agentId}
                  onClick={() => void handleAdd()}
                >
                  添加
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
