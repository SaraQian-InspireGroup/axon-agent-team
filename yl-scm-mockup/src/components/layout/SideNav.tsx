import { ChevronDown, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import type { SideNavItemConfig } from '../../config/navigation'

interface SideNavProps {
  collapsed: boolean
  onToggle: () => void
  items: SideNavItemConfig[]
  activeId: string
  onSelect?: (id: string) => void
}

export default function SideNav({
  collapsed,
  onToggle,
  items,
  activeId,
  onSelect,
}: SideNavProps) {
  return (
    <aside className={`side-nav${collapsed ? ' side-nav-collapsed' : ''}`}>
      <div className="side-nav-scroll">
        {items.map((item) => {
          if (item.children) {
            const expanded = item.expanded ?? item.children.some((child) => child.id === activeId)
            return (
              <div
                key={item.id}
                className={`side-nav-group${expanded ? ' side-nav-group-expanded' : ''}`}
              >
                <div
                  className={`side-nav-group-label${expanded ? ' side-nav-group-label-expanded' : ''}`}
                >
                  {item.icon ? <item.icon size={16} className="side-nav-item-icon" /> : null}
                  <span>{item.label}</span>
                  <ChevronDown
                    size={14}
                    className={`side-nav-chevron${expanded ? ' side-nav-chevron-expanded' : ''}`}
                  />
                </div>
                {expanded
                  ? item.children.map((child) => (
                      <button
                        key={child.id}
                        type="button"
                        className={[
                          'side-nav-item',
                          'side-nav-sub-item',
                          child.interactive ? 'side-nav-item-interactive' : '',
                          child.id === activeId ? 'side-nav-item-active' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                        onClick={
                          child.interactive
                            ? () => onSelect?.(child.id)
                            : (event) => event.preventDefault()
                        }
                      >
                        <span>{child.label}</span>
                      </button>
                    ))
                  : null}
              </div>
            )
          }

          return (
            <button
              key={item.id}
              type="button"
              className={[
                'side-nav-item',
                item.interactive ? 'side-nav-item-interactive' : '',
                item.id === activeId ? 'side-nav-item-active' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={
                item.interactive
                  ? () => onSelect?.(item.id)
                  : (event) => event.preventDefault()
              }
            >
              {item.icon ? <item.icon size={16} className="side-nav-item-icon" /> : null}
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>

      <div className="side-nav-footer">
        <button
          type="button"
          className="side-nav-toggle-btn"
          onClick={onToggle}
          aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>
    </aside>
  )
}
