import { useCallback, useEffect, useMemo, useState } from 'react'
import FilterPanel from '../common/FilterPanel'
import TableCheckbox from '../common/TableCheckbox'
import CreateBranchReplenishmentModal from '../fulfillment/CreateBranchReplenishmentModal'
import { useRowSelection } from '../../hooks/useRowSelection'
import { mockupApi, type FulfillmentFilterOptions } from '../../api/mockupClient'
import type { BranchReplenishmentOrder } from '../../data/mockData'

const TABLE_HEADERS = [
  '调拨单号',
  '商品编码',
  'SKU编码',
  '商品名称',
  '单位',
  '事业部',
  '电商条码',
  '商家订单号',
  '状态',
  '生成调拨单状态',
  '调拨数量',
  '毛重/吨',
  '总毛重/吨',
  '净重/吨',
  '总净重/吨',
  '体积/m³',
  '总体积/m³',
  '温区属性',
  '初始发货仓',
  '调出逻辑仓',
  '中转仓',
  '调入逻辑仓',
] as const

const DEFAULT_FILTERS: FulfillmentFilterOptions = {
  business_units: ['成人营养品事业部'],
  logic_warehouses: [],
  initial_ship_warehouses: [],
  transit_warehouses: [],
  statuses: ['全部', '草稿', '生效', '作废'],
  transfer_gen_statuses: ['全部', '未生成', '已生成'],
  products: [],
}

function formatDecimal(value: number, digits = 3): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function TableLoadingOverlay() {
  return (
    <div className="transfer-table-loading" role="status" aria-live="polite" aria-label="正在加载数据">
      <svg
        className="process-step-spinner transfer-table-loading-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden
      >
        <path d="M12 2v4" />
        <path d="M12 18v4" opacity="0.3" />
        <path d="m4.93 4.93 2.83 2.83" opacity="0.7" />
        <path d="m16.24 16.24 2.83 2.83" opacity="0.3" />
      </svg>
      <span className="transfer-table-loading-text">正在查询数据…</span>
    </div>
  )
}

function ActionLinks({ actions }: { actions: BranchReplenishmentOrder['actions'] }) {
  const links: { key: string; label: string; show: boolean }[] = [
    { key: 'split', label: '拆行', show: actions.split },
    { key: 'invalidate', label: '作废', show: actions.invalidate },
    { key: 'increase', label: '加量', show: actions.increase },
    { key: 'log', label: '日志', show: actions.log },
  ]

  const visible = links.filter((link) => link.show)

  return (
    <div className="fulfill-action-links">
      {visible.map((link, index) => (
        <span key={link.key}>
          {index > 0 ? <span className="fulfill-action-sep">|</span> : null}
          <button type="button" className="fulfill-action-link">
            {link.label}
          </button>
        </span>
      ))}
    </div>
  )
}

function OrderCells({ row }: { row: BranchReplenishmentOrder }) {
  return (
    <>
      <td className="fulfill-col-order-no">{row.transferOrderNo}</td>
      <td>{row.productCode}</td>
      <td>{row.skuCode}</td>
      <td className="col-product-name fulfill-col-product">{row.productName}</td>
      <td>{row.unit}</td>
      <td>{row.businessUnit}</td>
      <td>{row.ecommerceBarcode ?? '-'}</td>
      <td>{row.merchantOrderNo ?? '-'}</td>
      <td>{row.status}</td>
      <td>{row.transferGenStatus}</td>
      <td>{row.transferQty.toLocaleString()}</td>
      <td>{formatDecimal(row.grossWeightPerTon, 4)}</td>
      <td>{formatDecimal(row.totalGrossWeightTon)}</td>
      <td>{formatDecimal(row.netWeightPerTon, 4)}</td>
      <td>{formatDecimal(row.totalNetWeightTon)}</td>
      <td>{formatDecimal(row.volumeM3, 4)}</td>
      <td>{formatDecimal(row.totalVolumeM3)}</td>
      <td>{row.tempZone}</td>
      <td className="fulfill-col-warehouse">{row.initialShipWarehouse}</td>
      <td className="fulfill-col-warehouse">{row.outboundLogicWarehouse}</td>
      <td>{row.transitWarehouse}</td>
      <td className="fulfill-col-warehouse">{row.inboundLogicWarehouse}</td>
    </>
  )
}

export default function BranchReplenishmentTab() {
  const [filterOptions, setFilterOptions] = useState<FulfillmentFilterOptions>(DEFAULT_FILTERS)
  const [rows, setRows] = useState<BranchReplenishmentOrder[]>([])
  const [totals, setTotals] = useState({
    transferQty: 0,
    totalGrossWeightTon: 0,
    totalNetWeightTon: 0,
    totalVolumeM3: 0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState('')
  const [lastFilters, setLastFilters] = useState<Record<string, string>>({})
  const [generateOpen, setGenerateOpen] = useState(false)
  const [products, setProducts] = useState<{ code: string; name: string }[]>([])

  const rowIds = rows.map((row) => row.id)
  const { selected, allSelected, indeterminate, toggleRow, toggleAll } = useRowSelection(rowIds)

  useEffect(() => {
    mockupApi.fetchFulfillmentFilters().then(setFilterOptions).catch(() => {})
    mockupApi.fetchPlanFilters().then((opts) => setProducts(opts.products)).catch(() => {})
  }, [])

  const loadData = useCallback(async (filters: Record<string, string> = {}) => {
    setLoading(true)
    setError(null)
    setLastFilters(filters)
    try {
      const apiParams: Record<string, string> = {
        business_unit: filters.businessUnit ?? filterOptions.business_units[0] ?? '',
        inbound_logic_warehouse: filters.inboundLogicWarehouse ?? '',
        outbound_logic_warehouse: filters.outboundLogicWarehouse ?? '',
        initial_ship_warehouse: filters.initialShipWarehouse ?? '',
        status: filters.status ?? '',
        transfer_gen_status: filters.transferGenStatus ?? '',
        product_name: filters.productName ?? '',
        source_order_no: filters.sourceOrderNo ?? '',
      }
      const result = await mockupApi.fetchBranchReplenishment(apiParams)
      setRows(result.rows)
      setTotals(result.totals)
      setUpdatedAt(result.updatedAt)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [filterOptions.business_units])

  useEffect(() => {
    if (filterOptions.business_units.length) {
      loadData({ businessUnit: filterOptions.business_units[0] })
    }
  }, [filterOptions.business_units, loadData])

  const filterFields = useMemo(
    () => [
      {
        key: 'inboundLogicWarehouse',
        label: '调入逻辑仓',
        type: 'select' as const,
        options: filterOptions.logic_warehouses,
      },
      {
        key: 'outboundLogicWarehouse',
        label: '调出逻辑仓',
        type: 'select' as const,
        options: filterOptions.logic_warehouses,
      },
      {
        key: 'initialShipWarehouse',
        label: '初始发货仓',
        type: 'select' as const,
        options: filterOptions.initial_ship_warehouses,
      },
      {
        key: 'businessUnit',
        label: '事业部',
        type: 'select' as const,
        options: filterOptions.business_units,
        defaultValue: filterOptions.business_units[0] ?? '',
      },
      {
        key: 'status',
        label: '状态',
        type: 'select' as const,
        options: filterOptions.statuses,
        defaultValue: '全部',
      },
      {
        key: 'transferGenStatus',
        label: '生成调拨单状态',
        type: 'select' as const,
        options: filterOptions.transfer_gen_statuses,
        defaultValue: '全部',
      },
      {
        key: 'productName',
        label: '商品名称',
        type: 'select' as const,
        options: filterOptions.products,
        wide: true,
        placeholder: '请输入商品名称/编码',
      },
      {
        key: 'sourceOrderNo',
        label: '来源单号',
        type: 'text' as const,
        placeholder: '请输入来源单号',
      },
    ],
    [filterOptions],
  )

  return (
    <>
      <FilterPanel
        searchLabel="查询"
        resetLabel="重置"
        fields={filterFields}
        onSearch={loadData}
        onClear={() => loadData({ businessUnit: filterOptions.business_units[0] ?? '' })}
      />

      <div className="action-toolbar">
        <div className="action-toolbar-left">
          <button
            type="button"
            className="btn-primary"
            disabled={loading}
            onClick={() => setGenerateOpen(true)}
          >
            生成调拨单
          </button>
          <button type="button" className="btn-outline">
            中转数据
          </button>
          <button type="button" className="btn-outline">
            导入取消量
          </button>
          <button type="button" className="btn-outline">
            批量导入加量
          </button>
          <button type="button" className="btn-outline">
            作废
          </button>
          <button type="button" className="btn-outline">
            导出
          </button>
        </div>
        <span className="toolbar-meta">
          {loading ? '加载中…' : error ? `错误: ${error}` : `更新时间: ${updatedAt}`}
        </span>
      </div>

      <div
        className={`table-container transfer-table-container${loading ? ' transfer-table-container--loading' : ''}`}
      >
        {loading ? <TableLoadingOverlay /> : null}
        <table className="data-table fulfillment-table">
          <thead>
            <tr>
              <th className="fulfill-col-check">
                <TableCheckbox
                  checked={allSelected}
                  indeterminate={indeterminate}
                  onChange={toggleAll}
                  ariaLabel="全选"
                />
              </th>
              {TABLE_HEADERS.map((header) => (
                <th key={header}>{header}</th>
              ))}
              <th className="fulfill-col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="fulfill-col-check">
                  <TableCheckbox
                    checked={selected.has(row.id)}
                    onChange={(checked) => toggleRow(row.id, checked)}
                    ariaLabel={`选择 ${row.productName}`}
                  />
                </td>
                <OrderCells row={row} />
                <td className="fulfill-col-actions">
                  <ActionLinks actions={row.actions} />
                </td>
              </tr>
            ))}
            <tr className="fulfill-summary-row">
              <td className="fulfill-col-check" />
              <td colSpan={10}>合计</td>
              <td>{totals.transferQty.toLocaleString()}</td>
              <td />
              <td>{formatDecimal(totals.totalGrossWeightTon)}</td>
              <td />
              <td>{formatDecimal(totals.totalNetWeightTon)}</td>
              <td />
              <td>{formatDecimal(totals.totalVolumeM3)}</td>
              <td colSpan={5} />
              <td className="fulfill-col-actions" />
            </tr>
          </tbody>
        </table>
      </div>

      <CreateBranchReplenishmentModal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        filterOptions={filterOptions}
        products={products}
        onSuccess={() => loadData(lastFilters)}
      />
    </>
  )
}
