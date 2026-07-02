import { useState } from 'react'
import { X } from 'lucide-react'
import TransferAllocationTab from '../tabs/TransferAllocationTab'
import NationalInventoryTab from '../tabs/NationalInventoryTab'

const CONTENT_TABS = [
  { id: 'transfer', label: '正向分货销售仓调拨', navId: 'sales-transfer', enabled: true },
  { id: 'inventory', label: '全国库存监控', navId: 'sales-transfer', enabled: true },
  { id: 'base-report', label: '基地仓库存监控报表', navId: 'sales-transfer', enabled: false },
  { id: 'sales-report', label: '销售仓库存监控报表', navId: 'sales-transfer', enabled: false },
  { id: 'ecommerce-report', label: '直营电商仓库存日报表', navId: 'sales-transfer', enabled: false },
  { id: 'production-summary', label: '排产计划汇总表(分工厂)', navId: 'sales-transfer', enabled: false },
] as const

type TabId = (typeof CONTENT_TABS)[number]['id']

interface PlanMainPanelProps {
  activeNavId: string
}

export default function PlanMainPanel({ activeNavId }: PlanMainPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('transfer')

  if (activeNavId !== 'sales-transfer') {
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

  const activeTabMeta = CONTENT_TABS.find((tab) => tab.id === activeTab)

  return (
    <>
      <div className="breadcrumb-bar">
        <span className="breadcrumb-text">首页</span>
        <span className="breadcrumb-text">/</span>
        <span className="breadcrumb-text breadcrumb-text-active">
          {activeTabMeta?.label ?? '正向分货销售仓调拨'}
        </span>
        <button type="button" className="breadcrumb-close" aria-label="关闭">
          <X size={14} />
        </button>
      </div>

      <div className="content-tabs" role="tablist">
        {CONTENT_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            disabled={!tab.enabled}
            className={`content-tab${activeTab === tab.id ? ' content-tab-active' : ''}`}
            onClick={() => tab.enabled && setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="panel-scroll">
        {activeTab === 'transfer' && <TransferAllocationTab />}
        {activeTab === 'inventory' && <NationalInventoryTab />}
      </div>
    </>
  )
}
