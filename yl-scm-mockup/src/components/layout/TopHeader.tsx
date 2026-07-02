import {
  Bell,
  Grid3x3,
  HelpCircle,
  LayoutGrid,
  Settings,
} from 'lucide-react'

const HEADER_TABS = [
  { id: 'plan', label: '计划中心', active: true },
  { id: 'fulfill', label: '履约中心', active: false },
]

export default function TopHeader() {
  return (
    <header className="top-header">
      <div className="top-header-brand">
        <img src="/supply-chain.png" alt="供应链数字化" className="top-header-logo" />
        <div>
          <div className="top-header-title-main">供应链数字化</div>
          <div className="top-header-title-sub">OPERATION PLATFORM</div>
        </div>
      </div>

      <nav className="top-header-center" aria-label="主导航">
        {HEADER_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`top-header-nav-tab${tab.active ? ' top-header-nav-tab-active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="top-header-actions">
        <button type="button" className="top-header-icon-btn" aria-label="应用切换">
          <LayoutGrid size={18} />
        </button>
        <button type="button" className="top-header-icon-btn" aria-label="网格">
          <Grid3x3 size={18} />
        </button>
        <button type="button" className="top-header-icon-btn" aria-label="帮助">
          <HelpCircle size={18} />
        </button>
        <button type="button" className="top-header-icon-btn" aria-label="设置">
          <Settings size={18} />
        </button>
        <div className="top-header-notify-wrap">
          <button type="button" className="top-header-icon-btn" aria-label="通知">
            <Bell size={18} />
          </button>
          <span className="top-header-notify-badge">3</span>
        </div>
        <div className="top-header-user">
          <span className="top-header-avatar">陈</span>
          <span className="top-header-user-text">陈大文，欢迎登录！</span>
        </div>
      </div>
    </header>
  )
}
