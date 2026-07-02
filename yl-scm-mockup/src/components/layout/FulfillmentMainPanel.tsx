import { X } from 'lucide-react'
import BranchReplenishmentTab from '../tabs/BranchReplenishmentTab'

const PAGE_META: Record<string, { label: string }> = {
  'branch-replenishment': { label: '分仓补录单' },
}

interface FulfillmentMainPanelProps {
  activeNavId: string
}

export default function FulfillmentMainPanel({ activeNavId }: FulfillmentMainPanelProps) {
  const page = PAGE_META[activeNavId]

  if (!page) {
    return (
      <>
        <div className="breadcrumb-bar">
          <span className="breadcrumb-text">首页</span>
        </div>
        <div className="panel-scroll panel-placeholder">
          <p className="panel-placeholder-text">该菜单页面暂未实现</p>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="breadcrumb-bar">
        <span className="breadcrumb-text">首页</span>
        <span className="breadcrumb-text">/</span>
        <span className="breadcrumb-text breadcrumb-text-active">{page.label}</span>
        <button type="button" className="breadcrumb-close" aria-label="关闭">
          <X size={14} />
        </button>
      </div>

      <div className="content-tabs" role="tablist">
        <button type="button" role="tab" aria-selected className="content-tab content-tab-active">
          {page.label}
        </button>
      </div>

      <div className="panel-scroll">
        {activeNavId === 'branch-replenishment' && <BranchReplenishmentTab />}
      </div>
    </>
  )
}
