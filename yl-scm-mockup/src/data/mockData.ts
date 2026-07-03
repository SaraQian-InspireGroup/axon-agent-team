export type RateLevel = 'success' | 'warning' | 'danger'

export interface RegionAllocation {
  region: string
  assignQty: number | ''
  issuedNotShipped: number
  /** 分配前生产备货率，null 表示 "/" */
  preProdStockRate: number | null
  /** 分配后生产备货率，null 表示 "/" */
  postProdStockRate: number | null
  orderCompleteRate: number
  stockDaysAfter: number
  nextMonthDays: number
}

export interface TransferRow {
  id: string
  baseWarehouse: string
  productName: string
  monthlyInbound: number | ''
  normalTransit: number
  transferTransit: number
  pendingInspect: number
  pendingUnpublish: number
  qualified: number
  qualifiedUnpublish: number
  availableQty: number
  regions: RegionAllocation[]
}

export const TRANSFER_REGIONS = [
  '呼市',
  '武汉',
  '合肥',
  '天津',
  '郑州',
  '沈阳',
  '广州',
]

export const REGION_METRIC_HEADERS = [
  '分配量',
  '已下发未发货',
  '分配前生产备货率',
  '分配后生产备货率',
  '订单完成率',
  '分配后库存天数',
  '下月库存天数',
] as const

export const FIXED_INVENTORY_HEADERS = {
  level2: ['正常调拨在途', '中转调拨在途', '分配前合计', '分配后结余'] as const,
  level3: ['待检', '待检不可发', '合格', '合格不可发', '可发量'] as const,
}

export function getInventoryDaysLevel(days: number): RateLevel {
  if (days >= 20) return 'danger'
  if (days >= 12) return 'warning'
  return 'success'
}

export function getDaysCellClass(level: RateLevel): string {
  if (level === 'danger') return 'cell-days-danger'
  if (level === 'warning') return 'cell-days-warning'
  return 'cell-days-success'
}

function makeRegion(
  region: string,
  seed: number,
  overrides?: Partial<RegionAllocation>,
): RegionAllocation {
  const base = seed * 17
  return {
    region,
    assignQty: base % 900 || '',
    issuedNotShipped: (base % 200) + 10,
    preProdStockRate: seed % 4 === 0 ? null : 60 + (base % 45),
    postProdStockRate: seed % 5 === 0 ? null : 55 + (base % 50),
    orderCompleteRate: base % 100,
    stockDaysAfter: 8 + (base % 45),
    nextMonthDays: 5 + (base % 30),
    ...overrides,
  }
}

export const transferRows: TransferRow[] = [
  {
    id: '1',
    baseWarehouse: '武汉基地',
    productName: '伊利欣活心活膳底配方奶粉(听装)(同仁堂联名)1x6x800g',
    monthlyInbound: '',
    normalTransit: 0,
    transferTransit: 2355,
    pendingInspect: 769,
    pendingUnpublish: 0,
    qualified: 28218.7,
    qualifiedUnpublish: 0.7,
    availableQty: 2842.8,
    regions: TRANSFER_REGIONS.map((region) => {
      if (region === '呼市') {
        return makeRegion('呼市', 2, {
          assignQty: 80,
          issuedNotShipped: 22,
          preProdStockRate: 164,
          postProdStockRate: 92.5,
          orderCompleteRate: 1,
          stockDaysAfter: 35,
          nextMonthDays: 52,
        })
      }
      if (region === '武汉') {
        return makeRegion('武汉', 3, {
          preProdStockRate: 88,
          postProdStockRate: 95,
          stockDaysAfter: 14,
          nextMonthDays: 15,
        })
      }
      if (region === '广州') {
        return makeRegion('广州', 9, {
          assignQty: 120,
          issuedNotShipped: 45,
          preProdStockRate: 81.2,
          postProdStockRate: 100,
          orderCompleteRate: 0,
          stockDaysAfter: 29,
          nextMonthDays: 31,
        })
      }
      const seed = TRANSFER_REGIONS.indexOf(region) + 1
      return makeRegion(region, seed)
    }),
  },
  {
    id: '2',
    baseWarehouse: '武汉基地',
    productName: '伊利欣活心语酸奶配方奶粉(听装)(同二官联名) 1x6x800g',
    monthlyInbound: 500,
    normalTransit: 980,
    transferTransit: 650,
    pendingInspect: 380,
    pendingUnpublish: 90,
    qualified: 2800,
    qualifiedUnpublish: 150,
    availableQty: 4920,
    regions: TRANSFER_REGIONS.map((region, i) => makeRegion(region, i + 11)),
  },
  {
    id: '3',
    baseWarehouse: '武汉基地',
    productName: '伊利牛奶片160g草莓味(盒装)1x12',
    monthlyInbound: 2000,
    normalTransit: 3500,
    transferTransit: 1200,
    pendingInspect: 800,
    pendingUnpublish: 200,
    qualified: 8500,
    qualifiedUnpublish: 400,
    availableQty: 12800,
    regions: TRANSFER_REGIONS.map((region, i) =>
      makeRegion(region, i + 21, {
        preProdStockRate: 90 + (i % 10),
        postProdStockRate: 85 + (i % 12),
        stockDaysAfter: 10,
        nextMonthDays: 8,
      }),
    ),
  },
  {
    id: '4',
    baseWarehouse: '武汉基地',
    productName: '伊利中老年高钙低脂奶粉(袋装)1x16x400g',
    monthlyInbound: '',
    normalTransit: 2200,
    transferTransit: 900,
    pendingInspect: 600,
    pendingUnpublish: 180,
    qualified: 4100,
    qualifiedUnpublish: 250,
    availableQty: 6750,
    regions: TRANSFER_REGIONS.map((region, i) => makeRegion(region, i + 31)),
  },
]

// --- 全国库存监控 tab ---

export interface NationalInventoryRow {
  date: string
  series: string
  productName: string
  productCode: string
  totalInventory: number
  baseWarehouses: Record<string, number | null>
  salesSpot: Record<string, number | null>
  salesUnshipped: Record<string, number | null>
  salesGaps: Record<string, number | null>
}

export const INVENTORY_SCROLL_SECTIONS = [
  { id: 'base', label: '基地仓' },
  { id: 'spot', label: '销售仓现货' },
  { id: 'unshipped', label: '销售仓未发订单' },
  { id: 'gap', label: '销售仓缺口（分配后）' },
] as const

export const BASE_WAREHOUSES = [
  '呼市基地',
  '天津基地',
  '杜蒙基地',
  '武汉基地',
]

export const SALES_CITIES = [
  '合肥',
  '天津',
  '广州',
  '郑州',
  '成都',
  '武汉',
  '呼市',
  '济南',
  '柳州',
]

/** Tab2 已接后端 API */
export const nationalInventoryRows: NationalInventoryRow[] = []

/** @deprecated use nationalInventoryRows */
export interface InventoryGapRow {
  date: string
  series: string
  productName: string
  totalInventory: number
  gaps: Record<string, number | null>
}

export const inventoryGapRows: InventoryGapRow[] = nationalInventoryRows.map((row) => ({
  date: row.date,
  series: row.series,
  productName: row.productName,
  totalInventory: row.totalInventory,
  gaps: row.salesGaps,
}))

export const FILTER_OPTIONS = {
  businessUnits: ['成人营养品事业部'],
  productSeries: ['中老年', '奶片奶贝'],
  baseWarehouses: ['武汉基地', '呼市基地', '天津基地', '合肥基地'],
  salesWarehouses: ['武汉', '合肥', '南京', '天津', '郑州', '广州'],
  products: [
    '伊利欣活心活膳底配方奶粉(听装)(同仁堂联名)1x6x800g',
    '伊利欣活心语酸奶配方奶粉(听装)(同二官联名) 1x6x800g',
    '伊利牛奶片160g草莓味(盒装)1x12',
  ],
}

// --- 履约中心：分仓补录单 ---

export interface BranchReplenishmentOrder {
  id: string
  transferOrderNo: string
  productCode: string
  skuCode: string
  productName: string
  unit: string
  businessUnit: string
  ecommerceBarcode: string | null
  merchantOrderNo: string | null
  status: string
  transferGenStatus: string
  transferQty: number
  grossWeightPerTon: number
  totalGrossWeightTon: number
  netWeightPerTon: number
  totalNetWeightTon: number
  volumeM3: number
  totalVolumeM3: number
  tempZone: string
  initialShipWarehouse: string
  outboundLogicWarehouse: string
  transitWarehouse: string
  inboundLogicWarehouse: string
  sourceOrderNo: string
  actions: {
    split: boolean
    invalidate: boolean
    increase: boolean
    log: boolean
  }
}

export const FULFILL_FILTER_OPTIONS = {
  logicWarehouses: [
    '天津销售仓一盘货仓',
    '南昌分仓一盘货仓',
    '广州分仓一盘货仓',
    '武汉销售仓一盘货仓',
    '合肥销售仓一盘货仓',
  ],
  initialShipWarehouses: [
    '天津基地仓一盘货仓',
    '武汉基地仓一盘货仓',
    '呼市基地仓一盘货仓',
    '合肥基地仓一盘货仓',
  ],
  statuses: ['全部', '生效', '作废'],
  transferGenStatuses: ['全部', '未生成', '已生成'],
}

export const branchReplenishmentOrders: BranchReplenishmentOrder[] = [
  {
    id: '1',
    transferOrderNo: 'TS290721812345678901234567890123456789012345678901234567890',
    productCode: '10001234',
    skuCode: 'SKU-80001',
    productName: '伊利欣活中老年奶粉(听装)1x6x800g',
    unit: 'EA',
    businessUnit: '成人营养品事业部',
    ecommerceBarcode: '6901234567890',
    merchantOrderNo: 'MO202607020001',
    status: '生效',
    transferGenStatus: '未生成',
    transferQty: 1200,
    grossWeightPerTon: 0.0052,
    totalGrossWeightTon: 6.24,
    netWeightPerTon: 0.0048,
    totalNetWeightTon: 5.76,
    volumeM3: 0.012,
    totalVolumeM3: 14.4,
    tempZone: '常温',
    initialShipWarehouse: '天津基地仓一盘货仓',
    outboundLogicWarehouse: '天津基地仓一盘货仓',
    transitWarehouse: '-',
    inboundLogicWarehouse: '天津销售仓一盘货仓',
    sourceOrderNo: 'SR20260702001',
    actions: { split: true, invalidate: true, increase: true, log: true },
  },
  {
    id: '2',
    transferOrderNo: 'TS290721812345678901234567890123456789012345678901234567891',
    productCode: '10005678',
    skuCode: 'SKU-80002',
    productName: '伊利欣活心语酸奶配方奶粉(听装)1x6x800g',
    unit: 'EA',
    businessUnit: '成人营养品事业部',
    ecommerceBarcode: '6901234567891',
    merchantOrderNo: 'MO202607020002',
    status: '生效',
    transferGenStatus: '已生成',
    transferQty: 860,
    grossWeightPerTon: 0.0051,
    totalGrossWeightTon: 4.386,
    netWeightPerTon: 0.0047,
    totalNetWeightTon: 4.042,
    volumeM3: 0.011,
    totalVolumeM3: 9.46,
    tempZone: '常温',
    initialShipWarehouse: '武汉基地仓一盘货仓',
    outboundLogicWarehouse: '武汉基地仓一盘货仓',
    transitWarehouse: '郑州中转仓',
    inboundLogicWarehouse: '南昌分仓一盘货仓',
    sourceOrderNo: 'SR20260702002',
    actions: { split: true, invalidate: true, increase: true, log: true },
  },
  {
    id: '3',
    transferOrderNo: 'TS290721812345678901234567890123456789012345678901234567892',
    productCode: '10009876',
    skuCode: 'SKU-80003',
    productName: '伊利牛奶片160g草莓味(盒装)1x12',
    unit: 'EA',
    businessUnit: '成人营养品事业部',
    ecommerceBarcode: '6901234567892',
    merchantOrderNo: 'MO202607020003',
    status: '生效',
    transferGenStatus: '未生成',
    transferQty: 2400,
    grossWeightPerTon: 0.0016,
    totalGrossWeightTon: 3.84,
    netWeightPerTon: 0.0015,
    totalNetWeightTon: 3.6,
    volumeM3: 0.004,
    totalVolumeM3: 9.6,
    tempZone: '常温',
    initialShipWarehouse: '合肥基地仓一盘货仓',
    outboundLogicWarehouse: '合肥基地仓一盘货仓',
    transitWarehouse: '-',
    inboundLogicWarehouse: '广州分仓一盘货仓',
    sourceOrderNo: 'SR20260702003',
    actions: { split: false, invalidate: false, increase: true, log: true },
  },
  {
    id: '4',
    transferOrderNo: 'TS290721812345678901234567890123456789012345678901234567893',
    productCode: '10003321',
    skuCode: 'SKU-80004',
    productName: '伊利中老年高钙低脂奶粉(袋装)1x16x400g',
    unit: 'EA',
    businessUnit: '成人营养品事业部',
    ecommerceBarcode: '6901234567893',
    merchantOrderNo: 'MO202607020004',
    status: '作废',
    transferGenStatus: '未生成',
    transferQty: 500,
    grossWeightPerTon: 0.0065,
    totalGrossWeightTon: 3.25,
    netWeightPerTon: 0.006,
    totalNetWeightTon: 3,
    volumeM3: 0.009,
    totalVolumeM3: 4.5,
    tempZone: '常温',
    initialShipWarehouse: '呼市基地仓一盘货仓',
    outboundLogicWarehouse: '呼市基地仓一盘货仓',
    transitWarehouse: '-',
    inboundLogicWarehouse: '武汉销售仓一盘货仓',
    sourceOrderNo: 'SR20260702004',
    actions: { split: true, invalidate: false, increase: true, log: true },
  },
  {
    id: '5',
    transferOrderNo: 'TS290721812345678901234567890123456789012345678901234567894',
    productCode: '10004455',
    skuCode: 'SKU-80005',
    productName: '伊利欣活心活膳底配方奶粉(听装)(同仁堂联名)1x6x800g',
    unit: 'EA',
    businessUnit: '成人营养品事业部',
    ecommerceBarcode: '6901234567894',
    merchantOrderNo: 'MO202607020005',
    status: '生效',
    transferGenStatus: '未生成',
    transferQty: 680,
    grossWeightPerTon: 0.0053,
    totalGrossWeightTon: 3.604,
    netWeightPerTon: 0.0049,
    totalNetWeightTon: 3.332,
    volumeM3: 0.012,
    totalVolumeM3: 8.16,
    tempZone: '冷藏',
    initialShipWarehouse: '天津基地仓一盘货仓',
    outboundLogicWarehouse: '天津基地仓一盘货仓',
    transitWarehouse: '济南中转仓',
    inboundLogicWarehouse: '合肥销售仓一盘货仓',
    sourceOrderNo: 'SR20260702005',
    actions: { split: false, invalidate: false, increase: true, log: true },
  },
]
