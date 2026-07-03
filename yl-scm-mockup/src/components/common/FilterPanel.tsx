import { ChevronDown, RefreshCw, Search } from 'lucide-react'
import { useState } from 'react'

export interface FilterField {
  key: string
  label: string
  type?: 'text' | 'date' | 'select'
  placeholder?: string
  options?: string[]
  wide?: boolean
  compact?: boolean
  defaultValue?: string
}

interface FilterPanelProps {
  fields: FilterField[]
  searchLabel?: string
  resetLabel?: string
  onSearch?: (values: Record<string, string>) => void
  onClear?: () => void
}

export default function FilterPanel({
  fields,
  searchLabel = '查询',
  resetLabel = '清空',
  onSearch,
  onClear,
}: FilterPanelProps) {
  const [expanded, setExpanded] = useState(true)
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f.key, f.defaultValue ?? ''])),
  )

  const handleClear = () => {
    setValues(Object.fromEntries(fields.map((f) => [f.key, ''])))
    onClear?.()
  }

  return (
    <div className="filter-panel-glacier">
      <div className="filter-panel-header">
        <div className="filter-panel-title">
          <span className="filter-panel-title-bar" />
          筛选条件
        </div>
        <button
          type="button"
          className="filter-panel-expand"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? '收起' : '展开'}
          <ChevronDown
            size={14}
            style={{ transform: expanded ? 'rotate(180deg)' : undefined, transition: 'transform 0.15s' }}
          />
        </button>
      </div>

      {expanded && (
        <div className="filter-panel-body">
          <div className="filter-grid">
            {fields.map((field) => (
              <div
                key={field.key}
                className={`filter-field${field.wide ? ' filter-field-wide' : ''}${field.compact ? ' filter-field-compact' : ''}`}
              >
                <label className="filter-label" htmlFor={field.key}>
                  {field.label}
                </label>
                {field.type === 'select' ? (
                  <select
                    id={field.key}
                    className="filter-select"
                    value={values[field.key]}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  >
                    <option value="">请选择</option>
                    {field.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={field.key}
                    type={field.type ?? 'text'}
                    className="filter-input"
                    placeholder={field.placeholder}
                    value={values[field.key]}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  />
                )}
              </div>
            ))}

            <div className="filter-actions">
              <button type="button" className="btn-clear" onClick={handleClear}>
                <RefreshCw size={14} />
                {resetLabel}
              </button>
              <button type="button" className="btn-search" onClick={() => onSearch?.(values)}>
                <Search size={14} />
                {searchLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
