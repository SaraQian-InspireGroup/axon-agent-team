import { useState } from 'react'
import type { CenterId } from '../../config/navigation'
import {
  DEFAULT_FULFILL_NAV_ID,
  DEFAULT_PLAN_NAV_ID,
  FULFILL_SIDE_NAV,
  PLAN_SIDE_NAV,
} from '../../config/navigation'
import TopHeader from './TopHeader'
import SideNav from './SideNav'
import PlanMainPanel from './PlanMainPanel'
import FulfillmentMainPanel from './FulfillmentMainPanel'
import AgentChatPanel from './AgentChatPanel'
import { useNovaChat } from '../../hooks/useNovaChat'

const DEFAULT_CHAT_WIDTH = 380
const MIN_CHAT_WIDTH = 320

function getMaxChatWidth() {
  return typeof window !== 'undefined' ? window.innerWidth * 0.4 : 640
}

export default function AppShell() {
  const [sidenavCollapsed, setSidenavCollapsed] = useState(false)
  const [activeCenter, setActiveCenter] = useState<CenterId>('plan')
  const [planNavId, setPlanNavId] = useState(DEFAULT_PLAN_NAV_ID)
  const [fulfillNavId, setFulfillNavId] = useState(DEFAULT_FULFILL_NAV_ID)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH)
  const novaChat = useNovaChat(chatOpen)

  const sideNavItems = activeCenter === 'plan' ? PLAN_SIDE_NAV : FULFILL_SIDE_NAV
  const activeNavId = activeCenter === 'plan' ? planNavId : fulfillNavId

  const handleCenterChange = (center: CenterId) => {
    setActiveCenter(center)
    if (center === 'fulfill') {
      setFulfillNavId(DEFAULT_FULFILL_NAV_ID)
    }
  }

  const handleNavSelect = (id: string) => {
    if (activeCenter === 'plan') {
      setPlanNavId(id)
    } else {
      setFulfillNavId(id)
    }
  }

  const handleChatWidthChange = (width: number) => {
    setChatWidth(Math.min(getMaxChatWidth(), Math.max(MIN_CHAT_WIDTH, width)))
  }

  return (
    <div className="app-shell">
      <TopHeader
        activeCenter={activeCenter}
        onCenterChange={handleCenterChange}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((value) => !value)}
      />
      <div className="app-body">
        <SideNav
          collapsed={sidenavCollapsed}
          onToggle={() => setSidenavCollapsed((value) => !value)}
          items={sideNavItems}
          activeId={activeNavId}
          onSelect={handleNavSelect}
        />
        <main
          className={`main-content${sidenavCollapsed ? ' main-content-sidenav-collapsed' : ''}${chatOpen ? ' main-content-chat-open' : ''}`}
        >
          {activeCenter === 'plan' ? (
            <PlanMainPanel activeNavId={planNavId} />
          ) : (
            <FulfillmentMainPanel activeNavId={fulfillNavId} />
          )}
        </main>
        {chatOpen ? (
          <AgentChatPanel
            width={chatWidth}
            onWidthChange={handleChatWidthChange}
            onClose={() => setChatOpen(false)}
            chat={novaChat}
          />
        ) : null}
      </div>
    </div>
  )
}
