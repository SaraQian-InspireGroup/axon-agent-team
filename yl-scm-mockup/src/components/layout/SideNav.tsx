import {
  Boxes,
  ChevronDown,
  ClipboardList,
  Database,
  FileSpreadsheet,
  GitBranch,
  History,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Truck,
  User,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  active?: boolean
  interactive?: boolean
  children?: Omit<NavItem, 'icon'>[]
}

const NAV_ITEMS: NavItem[] = [
  { id: 'user', label: '个人中心', icon: User },
  { id: 'basic', label: '基础数据维护', icon: Database },
  { id: 'production-report', label: '排产计划报表', icon: FileSpreadsheet },
  {
    id: 'replenishment',
    label: '补货管理',
    icon: Package,
    interactive: true,
    children: [
      { id: 'horizontal', label: '横向调拨' },
      { id: 'base-transfer', label: '正向分货基地调拨' },
      {
        id: 'sales-transfer',
        label: '正向分货销售仓调拨',
        active: true,
        interactive: true,
      },
      { id: 'pending-config', label: '基地仓待检不可发布库存配置' },
      { id: 'deduction-history', label: '正向分货扣减历史汇总' },
    ],
  },
  { id: 'milk-history', label: '奶粉分量下发历史', icon: History },
  { id: 'inventory-report', label: '库存计划报表', icon: FileSpreadsheet },
  { id: 'inventory-mgmt', label: '库存管理', icon: Boxes },
  { id: 'logistics', label: '物流需求计划', icon: Truck },
  { id: 'production-plan', label: '生产计划', icon: ClipboardList },
  { id: 'workflow', label: '流程中心', icon: GitBranch },
]

interface SideNavProps {
  collapsed: boolean
  onToggle: () => void
}

export default function SideNav({ collapsed, onToggle }: SideNavProps) {
  return (
    <aside className={`side-nav${collapsed ? ' side-nav-collapsed' : ''}`}>
      <div className="side-nav-scroll">
        {NAV_ITEMS.map((item) => {
          if (item.children) {
            return (
              <div key={item.id} className="side-nav-group side-nav-group-expanded">
                <div className="side-nav-group-label side-nav-group-label-expanded">
                  <item.icon size={16} className="side-nav-item-icon" />
                  <span>{item.label}</span>
                  <ChevronDown size={14} className="side-nav-chevron side-nav-chevron-expanded" />
                </div>
                {item.children.map((child) => (
                  <button
                    key={child.id}
                    type="button"
                    className={[
                      'side-nav-item',
                      'side-nav-sub-item',
                      child.interactive ? 'side-nav-item-interactive' : '',
                      child.active ? 'side-nav-item-active' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onClick={child.interactive ? undefined : (e) => e.preventDefault()}
                  >
                    <span>{child.label}</span>
                  </button>
                ))}
              </div>
            )
          }

          return (
            <button
              key={item.id}
              type="button"
              className="side-nav-item"
              onClick={(e) => e.preventDefault()}
            >
              <item.icon size={16} className="side-nav-item-icon" />
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
