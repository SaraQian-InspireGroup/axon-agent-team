import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  Boxes,
  Calendar,
  ClipboardList,
  CloudUpload,
  Database,
  FileSpreadsheet,
  FileText,
  GitBranch,
  History,
  Home,
  LayoutDashboard,
  Package,
  Settings2,
  SlidersHorizontal,
  Truck,
  User,
} from 'lucide-react'

export type CenterId = 'plan' | 'fulfill'

export interface SideNavItemConfig {
  id: string
  label: string
  icon?: LucideIcon
  interactive?: boolean
  expanded?: boolean
  children?: Omit<SideNavItemConfig, 'icon'>[]
}

export const PLAN_SIDE_NAV: SideNavItemConfig[] = [
  { id: 'user', label: '个人中心', icon: User },
  { id: 'basic', label: '基础数据维护', icon: Database },
  { id: 'production-report', label: '排产计划报表', icon: FileSpreadsheet },
  {
    id: 'replenishment',
    label: '补货管理',
    icon: Package,
    expanded: true,
    children: [
      { id: 'horizontal', label: '横向调拨' },
      { id: 'base-transfer', label: '正向分货基地调拨' },
      {
        id: 'sales-transfer',
        label: '正向分货销售仓调拨',
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

export const FULFILL_SIDE_NAV: SideNavItemConfig[] = [
  { id: 'home', label: '首页', icon: Home },
  { id: 'mgmt-home', label: '管理首页', icon: LayoutDashboard },
  {
    id: 'order-center',
    label: '订单中心',
    icon: FileText,
    children: [],
  },
  {
    id: 'replen-transfer',
    label: '补调管理',
    icon: Settings2,
    expanded: true,
    children: [
      { id: 'summary-suggestion', label: '汇总补货建议' },
      { id: 'transfer-order', label: '调拨单' },
      { id: 'logic-transfer', label: '逻辑调拨单' },
      { id: 'ecommerce-inquiry', label: '电商直供询单' },
      { id: 'channel-prealloc', label: '渠道预占需求' },
      { id: 'summary-prealloc', label: '汇总预占需求' },
      { id: 'branch-source-order', label: '分仓补货来源订单' },
      {
        id: 'branch-replenishment',
        label: '分仓补录单',
        interactive: true,
      },
    ],
  },
  { id: 'fulfillment-mgmt', label: '履约管理', icon: Calendar },
  { id: 'inventory-center', label: '库存中心', icon: Package },
  { id: 'master-data', label: '主数据管理', icon: Database },
  { id: 'business-config', label: '业务配置', icon: SlidersHorizontal },
  { id: 'business-report', label: '业务报表', icon: BarChart3 },
  { id: 'system-sync', label: '系统同步', icon: CloudUpload },
]

export const DEFAULT_PLAN_NAV_ID = 'sales-transfer'
export const DEFAULT_FULFILL_NAV_ID = 'branch-replenishment'
