import { useState } from 'react'
import TopHeader from './TopHeader'
import SideNav from './SideNav'
import MainPanel from './MainPanel'

export default function AppShell() {
  const [sidenavCollapsed, setSidenavCollapsed] = useState(false)

  return (
    <div className="app-shell">
      <TopHeader />
      <div className="app-body">
        <SideNav
          collapsed={sidenavCollapsed}
          onToggle={() => setSidenavCollapsed((v) => !v)}
        />
        <main
          className={`main-content${sidenavCollapsed ? ' main-content-sidenav-collapsed' : ''}`}
        >
          <MainPanel />
        </main>
      </div>
    </div>
  )
}
