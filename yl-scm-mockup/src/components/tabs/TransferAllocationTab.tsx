import FilterPanel from '../common/FilterPanel'
import {
  FILTER_OPTIONS,
  FIXED_INVENTORY_HEADERS,
  REGION_METRIC_HEADERS,
  TRANSFER_REGIONS,
  getDaysCellClass,
  getInventoryDaysLevel,
  transferRows,
} from '../../data/mockData'
import type { RegionAllocation, TransferRow } from '../../data/mockData'

const REGION_COL_COUNT = REGION_METRIC_HEADERS.length
const INVENTORY_COL_COUNT = FIXED_INVENTORY_HEADERS.level3.length + 2 // 2 transit + 4 pre + 1 available

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

function RegionCells({ region }: { region: RegionAllocation }) {
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
  return (
    <>
      <FilterPanel
        fields={[
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
            key: 'baseWarehouse',
            label: '基地仓',
            type: 'select',
            options: FILTER_OPTIONS.baseWarehouses,
            defaultValue: '武汉基地',
          },
          {
            key: 'salesWarehouse',
            label: '销售分仓',
            type: 'select',
            options: FILTER_OPTIONS.salesWarehouses,
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
        <span className="toolbar-meta">更新时间: 2026-07-02 08:17</span>
      </div>

      <div className="table-container transfer-table-container">
        <table className="data-table transfer-table">
          <thead>
            <tr>
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
            {transferRows.map((row) => {
              const regionMap = Object.fromEntries(row.regions.map((r) => [r.region, r]))
              return (
                <tr key={row.id}>
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
                  {TRANSFER_REGIONS.map((region) => {
                    const data = regionMap[region]
                    if (!data) {
                      return REGION_METRIC_HEADERS.map((header) => (
                        <td key={`${row.id}-${region}-${header}`} className="col-region">
                          -
                        </td>
                      ))
                    }
                    return (
                      <RegionCells key={`${row.id}-${region}`} region={data} />
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
