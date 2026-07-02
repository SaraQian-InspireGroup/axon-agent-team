import FilterPanel from '../common/FilterPanel'
import {
  BASE_WAREHOUSES,
  FILTER_OPTIONS,
  SALES_CITIES,
  nationalInventoryRows,
} from '../../data/mockData'

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
    return <span className="cell-danger-text">{value}</span>
  }
  return <span>{formatNum(value)}</span>
}

function ScrollNumCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-muted">-</span>
  }
  return <span>{formatNum(value)}</span>
}

export default function NationalInventoryTab() {
  const baseCount = BASE_WAREHOUSES.length
  const salesCount = SALES_CITIES.length

  return (
    <>
      <FilterPanel
        searchLabel="查询"
        fields={[
          {
            key: 'date',
            label: '日期',
            type: 'date',
            defaultValue: '2026-07-02',
          },
          {
            key: 'businessUnit',
            label: '事业部',
            type: 'select',
            options: FILTER_OPTIONS.businessUnits,
            defaultValue: FILTER_OPTIONS.businessUnits[0],
          },
          {
            key: 'productName',
            label: '产品名称',
            type: 'select',
            options: FILTER_OPTIONS.products,
            wide: true,
            placeholder: '请输入产品名称/编码',
          },
          {
            key: 'productSeries',
            label: '产品系列',
            type: 'select',
            options: FILTER_OPTIONS.productSeries,
            defaultValue: '中老年',
          },
        ]}
      />

      <div className="action-toolbar">
        <div className="action-toolbar-left">
          <button type="button" className="btn-primary">
            导出
          </button>
        </div>
      </div>

      <div className="table-container transfer-table-container">
        <table className="data-table inventory-table">
          <thead>
            <tr>
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
              <th colSpan={baseCount} className="header-fixed">
                基地仓
              </th>
              <th colSpan={salesCount} className="header-fixed">
                销售仓现货
              </th>
              <th colSpan={salesCount} className="header-unshipped-group">
                销售仓未发订单
              </th>
              <th colSpan={salesCount} className="header-gap-group">
                销售仓缺口（分配后）
              </th>
            </tr>
            <tr>
              {BASE_WAREHOUSES.map((wh) => (
                <th key={`base-${wh}`} className="col-scroll header-scroll-sub">
                  {wh}
                </th>
              ))}
              {SALES_CITIES.map((city) => (
                <th key={`spot-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
              {SALES_CITIES.map((city) => (
                <th key={`unshipped-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
              {SALES_CITIES.map((city) => (
                <th key={`gap-${city}`} className="col-scroll header-scroll-sub">
                  {city}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {nationalInventoryRows.map((row) => (
              <tr key={row.productName}>
                <td className={invFixCol(1)}>{row.date}</td>
                <td className={invFixCol(2)}>{row.series}</td>
                <td className={`${invFixCol(3)} col-product-name`}>{row.productName}</td>
                <td className={invFixCol(4, true)}>{formatNum(row.totalInventory)}</td>
                {BASE_WAREHOUSES.map((wh) => (
                  <td key={`${row.productName}-${wh}`} className="col-scroll">
                    <ScrollNumCell value={row.baseWarehouses[wh]} />
                  </td>
                ))}
                {SALES_CITIES.map((city) => (
                  <td key={`${row.productName}-spot-${city}`} className="col-scroll">
                    <ScrollNumCell value={row.salesSpot[city]} />
                  </td>
                ))}
                {SALES_CITIES.map((city) => (
                  <td key={`${row.productName}-unshipped-${city}`} className="col-scroll">
                    <ScrollNumCell value={row.salesUnshipped[city]} />
                  </td>
                ))}
                {SALES_CITIES.map((city) => {
                  const val = row.salesGaps[city]
                  const isNegative = val !== null && val !== undefined && val < 0
                  return (
                    <td
                      key={`${row.productName}-gap-${city}`}
                      className={`col-scroll${isNegative ? ' cell-danger-border' : ''}`}
                    >
                      <GapCell value={val} />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
