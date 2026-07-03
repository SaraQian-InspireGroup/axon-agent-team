import { useCallback, useEffect, useMemo, useState } from 'react'
import FilterPanel from '../common/FilterPanel'
import TableCheckbox from '../common/TableCheckbox'
import { useRowSelection } from '../../hooks/useRowSelection'
import { mockupApi } from '../../api/mockupClient'
import {
  FIXED_INVENTORY_HEADERS,
  REGION_METRIC_HEADERS,
  TRANSFER_REGIONS,
  getDaysCellClass,
  getInventoryDaysLevel,
} from '../../data/mockData'
import type { RegionAllocation, TransferRow } from '../../data/mockData'

const REGION_COL_COUNT = REGION_METRIC_HEADERS.length
const INVENTORY_COL_COUNT = FIXED_INVENTORY_HEADERS.level3.length + 2
const TOTAL_COL_SPAN = 4 + INVENTORY_COL_COUNT + TRANSFER_REGIONS.length * REGION_COL_COUNT

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

function fixColClass(index: number, last = false): string {
  const classes = [`fix-col-${index}`]
  if (last) classes.push('fix-col-last')
  return classes.join(' ')
}

function StockRateCell({ value }: { value: number | null }) {
  if (value === null) {
    return <td className="col-region cell-rate-empty">/</td>
  }
  const high = value >= 80
  return (
    <td className={`col-region ${high ? 'cell-rate-high' : 'cell-rate-normal'}`}>
      {Number.isInteger(value) ? value : value.toFixed(1)}%
    </td>
  )
}

function isEmptyRegion(region: RegionAllocation): boolean {
  return (
    (region.assignQty === '' || region.assignQty === 0) &&
    region.issuedNotShipped === 0 &&
    region.preProdStockRate === null &&
    region.postProdStockRate === null &&
    region.orderCompleteRate === 0 &&
    region.stockDaysAfter === 0 &&
    region.nextMonthDays === 0
  )
}

function RegionCells({ region }: { region: RegionAllocation | null }) {
  if (!region || isEmptyRegion(region)) {
    return (
      <>
        {REGION_METRIC_HEADERS.map((header) => (
          <td key={header} className="col-region">
            -
          </td>
        ))}
      </>
    )
  }
  return (
    <>
      <td className="col-region">
        <input
          type="number"
          className="cell-input"
          defaultValue={region.assignQty === '' ? '' : region.assignQty}
        />
      </td>
      <td className="col-region">{region.issuedNotShipped}</td>
      <StockRateCell value={region.preProdStockRate} />
      <StockRateCell value={region.postProdStockRate} />
      <td className="col-region">{region.orderCompleteRate}%</td>
      <td className={`col-region ${getDaysCellClass(getInventoryDaysLevel(region.stockDaysAfter))}`}>
        {region.stockDaysAfter}
      </td>
      <td className={`col-region ${getDaysCellClass(getInventoryDaysLevel(region.nextMonthDays))}`}>
        {region.nextMonthDays}
      </td>
    </>
  )
}

function InventoryCells({ row }: { row: TransferRow }) {
  return (
    <>
      <td className={fixColClass(4)}>{row.normalTransit}</td>
      <td className={fixColClass(5)}>{row.transferTransit}</td>
      <td className={fixColClass(6)}>{row.pendingInspect}</td>
      <td className={fixColClass(7)}>{row.pendingUnpublish}</td>
      <td className={fixColClass(8)}>{row.qualified}</td>
      <td className={fixColClass(9)}>{row.qualifiedUnpublish}</td>
      <td className={fixColClass(10, true)}>{row.availableQty}</td>
    </>
  )
}

export default function TransferAllocationTab() {
  const [rows, setRows] = useState<TransferRow[]>([])
  const [updatedAt, setUpdatedAt] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterOptions, setFilterOptions] = useState({
    businessUnits: ['成人营养品事业部'],
    productSeries: [] as string[],
    baseWarehouses: [] as string[],
    salesWarehouses: [] as string[],
    products: [] as string[],
  })

  const loadData = useCallback(async (filters: Record<string, string> = {}) => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (filters.businessUnit) params.business_unit = filters.businessUnit
      if (filters.productName) params.product_name = filters.productName
      if (filters.baseWarehouse) params.base_warehouse = filters.baseWarehouse
      if (filters.salesWarehouse) params.sales_warehouse = filters.salesWarehouse
      if (filters.productSeries) params.product_series = filters.productSeries
      const result = await mockupApi.fetchTransferAllocation(params)
      setRows(result.rows)
      setUpdatedAt(result.updatedAt)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    mockupApi
      .fetchPlanFilters()
      .then((opts) => {
        setFilterOptions({
          businessUnits: opts.business_units,
          productSeries: opts.product_series,
          baseWarehouses: opts.base_warehouses,
          salesWarehouses: opts.sales_warehouses,
          products: opts.products.map((p) => p.name),
        })
      })
      .catch(() => {})
    loadData()
  }, [loadData])

  const filterFields = useMemo(
    () => [
      {
        key: 'businessUnit',
        label: '事业部',
        type: 'select' as const,
        options: filterOptions.businessUnits,
        defaultValue: filterOptions.businessUnits[0] ?? '',
      },
      {
        key: 'productSeries',
        label: '产品系列',
        type: 'select' as const,
        options: filterOptions.productSeries,
      },
      {
        key: 'productName',
        label: '产品名称',
        type: 'select' as const,
        options: filterOptions.products,
        compact: true,
        placeholder: '请输入产品名称/编码',
      },
      {
        key: 'baseWarehouse',
        label: '基地仓',
        type: 'select' as const,
        options: filterOptions.baseWarehouses,
      },
      {
        key: 'salesWarehouse',
        label: '销售分仓',
        type: 'select' as const,
        options: filterOptions.salesWarehouses,
      },
    ],
    [filterOptions],
  )

  const rowIds = rows.map((row) => row.id)
  const { selected, allSelected, indeterminate, toggleRow, toggleAll } = useRowSelection(rowIds)

  return (
    <>
      <FilterPanel
        fields={filterFields}
        onSearch={loadData}
        onClear={() => loadData()}
      />

      <div className="action-toolbar">
        <div className="action-toolbar-left">
          <button type="button" className="btn-primary">
            分货导出
          </button>
          <button type="button" className="btn-primary">
            全量导出
          </button>
          <button type="button" className="btn-primary">
            分货导入
          </button>
          <button type="button" className="btn-outline">
            分货下发
          </button>
          <button type="button" className="btn-outline">
            一键提取
          </button>
        </div>
        <span className="toolbar-meta">
          {loading ? '加载中…' : error ? `错误: ${error}` : `更新时间: ${updatedAt}`}
        </span>
      </div>

      <div
        className={`table-container transfer-table-container transfer-table-container--allocation${loading ? ' transfer-table-container--loading' : ''}`}
      >
        {loading ? <TableLoadingOverlay /> : null}
        <table className="data-table transfer-table">
          <thead>
            <tr>
              <th rowSpan={3} className="fix-col-check">
                <TableCheckbox
                  checked={allSelected}
                  indeterminate={indeterminate}
                  onChange={toggleAll}
                  ariaLabel="全选"
                />
              </th>
              <th rowSpan={3} className={fixColClass(1)}>
                基地仓
              </th>
              <th rowSpan={3} className={`${fixColClass(2)} col-product-name`}>
                产品名称
              </th>
              <th rowSpan={3} className={fixColClass(3)}>
                本月预计入库
              </th>
              <th colSpan={INVENTORY_COL_COUNT} className="fix-col-inventory-group">
                基地仓库存
              </th>
              {TRANSFER_REGIONS.map((region) => (
                <th key={region} colSpan={REGION_COL_COUNT} className="col-region-group header-fixed">
                  区域分配预测 - {region}
                </th>
              ))}
            </tr>
            <tr>
              <th rowSpan={2} className={fixColClass(4)}>
                {FIXED_INVENTORY_HEADERS.level2[0]}
              </th>
              <th rowSpan={2} className={fixColClass(5)}>
                {FIXED_INVENTORY_HEADERS.level2[1]}
              </th>
              <th colSpan={4} className={fixColClass(6)}>
                {FIXED_INVENTORY_HEADERS.level2[2]}
              </th>
              <th className={fixColClass(10, true)}>
                {FIXED_INVENTORY_HEADERS.level2[3]}
              </th>
              {TRANSFER_REGIONS.flatMap((region) =>
                REGION_METRIC_HEADERS.map((header) => (
                  <th key={`${region}-${header}`} rowSpan={2} className="col-region header-scroll-sub">
                    {header}
                  </th>
                )),
              )}
            </tr>
            <tr>
              {FIXED_INVENTORY_HEADERS.level3.slice(0, 4).map((header, i) => (
                <th key={header} className={fixColClass(6 + i)}>
                  {header}
                </th>
              ))}
              <th className={fixColClass(10, true)}>
                {FIXED_INVENTORY_HEADERS.level3[4]}
              </th>
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr className="transfer-table-loading-placeholder" aria-hidden="true">
                <td colSpan={TOTAL_COL_SPAN} />
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={TOTAL_COL_SPAN}>
                  暂无数据
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const regionMap = Object.fromEntries(row.regions.map((r) => [r.region, r]))
                return (
                  <tr key={row.id}>
                    <td className="fix-col-check">
                      <TableCheckbox
                        checked={selected.has(row.id)}
                        onChange={(checked) => toggleRow(row.id, checked)}
                        ariaLabel={`选择 ${row.productName}`}
                      />
                    </td>
                    <td className={fixColClass(1)}>{row.baseWarehouse}</td>
                    <td className={`${fixColClass(2)} col-product-name`}>{row.productName}</td>
                    <td className={fixColClass(3)}>
                      <input
                        type="number"
                        className="cell-input cell-input-wide"
                        defaultValue={row.monthlyInbound === '' ? '' : row.monthlyInbound}
                      />
                    </td>
                    <InventoryCells row={row} />
                    {TRANSFER_REGIONS.map((region) => (
                      <RegionCells key={`${row.id}-${region}`} region={regionMap[region] ?? null} />
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
