import { useCallback, useEffect, useMemo, useState } from 'react'
import FilterPanel from '../common/FilterPanel'
import TableCheckbox from '../common/TableCheckbox'
import { useRowSelection } from '../../hooks/useRowSelection'
import { mockupApi } from '../../api/mockupClient'
import type { NationalInventoryRow } from '../../data/mockData'
import { BASE_WAREHOUSES, SALES_CITIES } from '../../data/mockData'

function invFixCol(index: number, last = false): string {
  const classes = [`inv-fix-col-${index}`]
  if (last) classes.push('inv-fix-col-last')
  return classes.join(' ')
}

function formatNum(value: number): string {
  return value.toLocaleString()
}

function GapCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-muted">-</span>
  }
  if (value < 0) {
    return <span className="cell-danger-text">{value.toLocaleString()}</span>
  }
  return <span>{formatNum(value)}</span>
}

function ScrollNumCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-muted">-</span>
  }
  return <span>{formatNum(value)}</span>
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

function nationalInventoryRowId(row: NationalInventoryRow): string {
  return `${row.date}-${row.productCode}`
}

export default function NationalInventoryTab() {
  const [rows, setRows] = useState<NationalInventoryRow[]>([])
  const [baseColumns, setBaseColumns] = useState<string[]>(BASE_WAREHOUSES)
  const [salesColumns, setSalesColumns] = useState<string[]>(SALES_CITIES)
  const [updatedAt, setUpdatedAt] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterOptions, setFilterOptions] = useState({
    businessUnits: ['成人营养品事业部'],
    productSeries: [] as string[],
    products: [] as string[],
  })

  const loadData = useCallback(async (filters: Record<string, string> = {}) => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (filters.businessUnit) params.business_unit = filters.businessUnit
      if (filters.productName) params.product_name = filters.productName
      if (filters.productSeries) params.product_series = filters.productSeries
      if (filters.date) params.date = filters.date
      const result = await mockupApi.fetchNationalInventory(params)
      setRows(result.rows)
      setBaseColumns(result.baseWarehouseColumns)
      setSalesColumns(result.salesCityColumns)
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
          products: opts.products.map((p) => p.name),
        })
      })
      .catch(() => {})
    loadData()
  }, [loadData])

  const filterFields = useMemo(
    () => [
      {
        key: 'date',
        label: '日期',
        type: 'date' as const,
      },
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
    ],
    [filterOptions],
  )

  const rowIds = rows.map(nationalInventoryRowId)
  const { selected, allSelected, indeterminate, toggleRow, toggleAll } = useRowSelection(rowIds)

  const scrollColCount = baseColumns.length + salesColumns.length * 3
  const totalColSpan = 5 + scrollColCount

  return (
    <>
      <FilterPanel searchLabel="查询" fields={filterFields} onSearch={loadData} onClear={() => loadData()} />

      <div className="action-toolbar">
        <div className="action-toolbar-left">
          <button type="button" className="btn-primary">
            导出
          </button>
        </div>
        <span className="toolbar-meta">
          {loading ? '加载中…' : error ? `错误: ${error}` : `更新时间: ${updatedAt}`}
        </span>
      </div>

      <div
        className={`table-container transfer-table-container transfer-table-container--inventory${loading ? ' transfer-table-container--loading' : ''}`}
      >
        {loading ? <TableLoadingOverlay /> : null}
        <table className="data-table inventory-table">
          <thead>
            <tr>
              <th rowSpan={2} className="inv-fix-col-check">
                <TableCheckbox
                  checked={allSelected}
                  indeterminate={indeterminate}
                  onChange={toggleAll}
                  ariaLabel="全选"
                />
              </th>
              <th rowSpan={2} className={invFixCol(1)}>
                日期
              </th>
              <th rowSpan={2} className={invFixCol(2)}>
                产品系列
              </th>
              <th rowSpan={2} className={`${invFixCol(3)} col-product-name`}>
                产品名称
              </th>
              <th rowSpan={2} className={invFixCol(4, true)}>
                库存(合计)
              </th>
              <th colSpan={baseColumns.length} className="header-fixed">
                基地仓
              </th>
              <th colSpan={salesColumns.length} className="header-fixed">
                销售仓现货
              </th>
              <th colSpan={salesColumns.length} className="header-unshipped-group">
                销售仓未发订单
              </th>
              <th colSpan={salesColumns.length} className="header-gap-group">
                销售仓缺口（分配后）
              </th>
            </tr>
            <tr>
              {baseColumns.map((wh) => (
                <th key={`base-${wh}`} className="col-scroll header-scroll-sub">
                  {wh}
                </th>
              ))}
              {salesColumns.map((city) => (
                <th key={`spot-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
              {salesColumns.map((city) => (
                <th key={`unshipped-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
              {salesColumns.map((city) => (
                <th key={`gap-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr className="transfer-table-loading-placeholder" aria-hidden="true">
                <td colSpan={totalColSpan} />
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={totalColSpan}>暂无数据</td>
              </tr>
            ) : (
              rows.map((row) => {
                const rowId = nationalInventoryRowId(row)
                return (
                  <tr key={rowId}>
                    <td className="inv-fix-col-check">
                      <TableCheckbox
                        checked={selected.has(rowId)}
                        onChange={(checked) => toggleRow(rowId, checked)}
                        ariaLabel={`选择 ${row.productName}`}
                      />
                    </td>
                    <td className={invFixCol(1)}>{row.date}</td>
                    <td className={invFixCol(2)}>{row.series}</td>
                    <td className={`${invFixCol(3)} col-product-name`}>{row.productName}</td>
                    <td className={invFixCol(4, true)}>{formatNum(row.totalInventory)}</td>
                    {baseColumns.map((wh) => (
                      <td key={`${rowId}-${wh}`} className="col-scroll">
                        <ScrollNumCell value={row.baseWarehouses[wh]} />
                      </td>
                    ))}
                    {salesColumns.map((city) => (
                      <td key={`${rowId}-spot-${city}`} className="col-scroll">
                        <ScrollNumCell value={row.salesSpot[city]} />
                      </td>
                    ))}
                    {salesColumns.map((city) => (
                      <td key={`${rowId}-unshipped-${city}`} className="col-scroll">
                        <ScrollNumCell value={row.salesUnshipped[city]} />
                      </td>
                    ))}
                    {salesColumns.map((city) => {
                      const val = row.salesGaps[city]
                      const isNegative = val !== null && val !== undefined && val < 0
                      return (
                        <td
                          key={`${rowId}-gap-${city}`}
                          className={`col-scroll${isNegative ? ' cell-danger-border' : ''}`}
                        >
                          <GapCell value={val} />
                        </td>
                      )
                    })}
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
