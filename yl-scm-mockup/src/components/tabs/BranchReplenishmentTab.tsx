import FilterPanel from '../common/FilterPanel'
import TableCheckbox from '../common/TableCheckbox'
import { useRowSelection } from '../../hooks/useRowSelection'
import {
  FILTER_OPTIONS,
  FULFILL_FILTER_OPTIONS,
  branchReplenishmentOrders,
} from '../../data/mockData'
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

function formatDecimal(value: number, digits = 3): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
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
      <td>{row.ecommerceBarcode}</td>
      <td>{row.merchantOrderNo}</td>
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
  const rowIds = branchReplenishmentOrders.map((row) => row.id)
  const { selected, allSelected, indeterminate, toggleRow, toggleAll } = useRowSelection(rowIds)

  const totals = branchReplenishmentOrders.reduce(
    (acc, row) => ({
      transferQty: acc.transferQty + row.transferQty,
      totalGrossWeightTon: acc.totalGrossWeightTon + row.totalGrossWeightTon,
      totalNetWeightTon: acc.totalNetWeightTon + row.totalNetWeightTon,
      totalVolumeM3: acc.totalVolumeM3 + row.totalVolumeM3,
    }),
    { transferQty: 0, totalGrossWeightTon: 0, totalNetWeightTon: 0, totalVolumeM3: 0 },
  )

  return (
    <>
      <FilterPanel
        searchLabel="查询"
        resetLabel="重置"
        fields={[
          {
            key: 'inboundLogicWarehouse',
            label: '调入逻辑仓',
            type: 'select',
            options: FULFILL_FILTER_OPTIONS.logicWarehouses,
          },
          {
            key: 'outboundLogicWarehouse',
            label: '调出逻辑仓',
            type: 'select',
            options: FULFILL_FILTER_OPTIONS.logicWarehouses,
          },
          {
            key: 'initialShipWarehouse',
            label: '初始发货仓',
            type: 'select',
            options: FULFILL_FILTER_OPTIONS.initialShipWarehouses,
          },
          {
            key: 'businessUnit',
            label: '事业部',
            type: 'select',
            options: FILTER_OPTIONS.businessUnits,
            defaultValue: FILTER_OPTIONS.businessUnits[0],
          },
          {
            key: 'status',
            label: '状态',
            type: 'select',
            options: FULFILL_FILTER_OPTIONS.statuses,
            defaultValue: '全部',
          },
          {
            key: 'transferGenStatus',
            label: '生成调拨单状态',
            type: 'select',
            options: FULFILL_FILTER_OPTIONS.transferGenStatuses,
            defaultValue: '全部',
          },
          {
            key: 'productName',
            label: '商品名称',
            type: 'select',
            options: FILTER_OPTIONS.products,
            wide: true,
            placeholder: '请输入商品名称/编码',
          },
          {
            key: 'sourceOrderNo',
            label: '来源单号',
            type: 'text',
            placeholder: '请输入来源单号',
          },
          {
            key: 'createdAt',
            label: '创建时间',
            type: 'text',
            wide: true,
            placeholder: '开始日期 - 结束日期',
          },
          {
            key: 'updatedAt',
            label: '修改时间',
            type: 'text',
            wide: true,
            placeholder: '开始日期 - 结束日期',
          },
          {
            key: 'upstreamCreatedAt',
            label: '上游创建时间',
            type: 'text',
            wide: true,
            placeholder: '开始日期 - 结束日期',
          },
        ]}
      />

      <div className="action-toolbar">
        <div className="action-toolbar-left">
          <button type="button" className="btn-primary">
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
      </div>

      <div className="table-container transfer-table-container">
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
            {branchReplenishmentOrders.map((row) => (
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
    </>
  )
}
