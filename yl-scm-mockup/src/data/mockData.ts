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
  '自贡',
  '呼市',
  '武汉',
  '合肥',
  '南京',
  '天津',
  '郑州',
  '沈阳',
  '广州',
  '新疆',
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
    regions: [
      makeRegion('自贡', 1, {
        assignQty: 120,
        issuedNotShipped: 45,
        preProdStockRate: 81.2,
        postProdStockRate: 100,
        orderCompleteRate: 0,
        stockDaysAfter: 29,
        nextMonthDays: 31,
      }),
      makeRegion('呼市', 2, {
        assignQty: 80,
        issuedNotShipped: 22,
        preProdStockRate: 164,
        postProdStockRate: 92.5,
        orderCompleteRate: 1,
        stockDaysAfter: 35,
        nextMonthDays: 52,
      }),
      makeRegion('武汉', 3, {
        preProdStockRate: 88,
        postProdStockRate: 95,
        stockDaysAfter: 14,
        nextMonthDays: 15,
      }),
      makeRegion('合肥', 4),
      makeRegion('南京', 5),
      makeRegion('天津', 6),
      makeRegion('郑州', 7),
      makeRegion('沈阳', 8),
      makeRegion('广州', 9),
      makeRegion('新疆', 10),
    ],
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
  totalInventory: number
  baseWarehouses: Record<string, number>
  salesSpot: Record<string, number>
  salesUnshipped: Record<string, number>
  salesGaps: Record<string, number | null>
}

export const INVENTORY_SCROLL_SECTIONS = [
  { id: 'base', label: '基地仓' },
  { id: 'spot', label: '销售仓现货' },
  { id: 'unshipped', label: '销售仓未发订单' },
  { id: 'gap', label: '销售仓缺口（分配后）' },
] as const

export const BASE_WAREHOUSES = [
  '武汉基地',
  '呼市基地',
  '天津基地',
  '杜尔伯特基地',
  '合肥基地',
  '辽宁基地',
  '金泽基地',
  '多伦多基地',
]

export const SALES_CITIES = [
  '兰州',
  '武汉',
  '天津',
  '郑州',
  '西安',
  '呼市',
  '沈阳',
  '广州',
  '合肥',
  '荆门',
  '南昌',
  '济南',
  '徐州',
  '柳州',
  '自贡',
  '新疆',
  '南京',
]

function buildSalesCityValues(
  seed: number,
  gaps?: Record<string, number | null>,
): {
  spot: Record<string, number>
  unshipped: Record<string, number>
  gaps: Record<string, number | null>
} {
  const spot: Record<string, number> = {}
  const unshipped: Record<string, number> = {}
  const gapMap: Record<string, number | null> = {}

  SALES_CITIES.forEach((city, i) => {
    const n = seed * 13 + i * 47
    spot[city] = 80 + (n % 900)
    unshipped[city] = (n % 120) + 5
    gapMap[city] = gaps?.[city] ?? (i % 5 === 0 ? null : (n % 180) - 60)
  })

  return { spot, unshipped, gaps: gapMap }
}

export const nationalInventoryRows: NationalInventoryRow[] = [
  {
    date: '2026-07-02',
    series: '中老年',
    productName: '伊利欣活心活膳底配方奶粉(听装)(同仁堂联名)1x6x800g',
    totalInventory: 12580,
    baseWarehouses: {
      武汉基地: 3200,
      呼市基地: 1800,
      天津基地: 2100,
      杜尔伯特基地: 980,
      合肥基地: 1500,
      辽宁基地: 1200,
      金泽基地: 900,
      多伦多基地: 900,
    },
    ...(() => {
      const s = buildSalesCityValues(1, {
        兰州: -42,
        武汉: -54,
        天津: 120,
        郑州: -12,
        西安: -18,
        呼市: 200,
        沈阳: -16,
        广州: 350,
        合肥: -45,
        荆门: 60,
        南昌: -71,
        济南: 95,
        徐州: null,
        柳州: null,
        自贡: 85,
        新疆: 180,
        南京: 42,
      })
      return { salesSpot: s.spot, salesUnshipped: s.unshipped, salesGaps: s.gaps }
    })(),
  },
  {
    date: '2026-07-02',
    series: '中老年',
    productName: '伊利欣活心语酸奶配方奶粉(听装)(同二官联名) 1x6x800g',
    totalInventory: 8920,
    baseWarehouses: {
      武汉基地: 2400,
      呼市基地: 1100,
      天津基地: 1300,
      杜尔伯特基地: 620,
      合肥基地: 980,
      辽宁基地: 850,
      金泽基地: 670,
      多伦多基地: 500,
    },
    ...(() => {
      const s = buildSalesCityValues(2, {
        兰州: 90,
        武汉: 150,
        天津: -35,
        郑州: 80,
        西安: 42,
        呼市: 110,
        沈阳: 65,
        广州: -48,
        合肥: 200,
        荆门: -8,
        南昌: 75,
        济南: -30,
        徐州: 45,
        柳州: -28,
        自贡: -22,
        新疆: -15,
        南京: 88,
      })
      return { salesSpot: s.spot, salesUnshipped: s.unshipped, salesGaps: s.gaps }
    })(),
  },
  {
    date: '2026-07-02',
    series: '奶片奶贝',
    productName: '伊利牛奶片160g草莓味(盒装)1x12',
    totalInventory: 45600,
    baseWarehouses: {
      武汉基地: 12800,
      呼市基地: 5600,
      天津基地: 4200,
      杜尔伯特基地: 3100,
      合肥基地: 6800,
      辽宁基地: 4500,
      金泽基地: 5200,
      多伦多基地: 3400,
    },
    ...(() => {
      const s = buildSalesCityValues(3)
      SALES_CITIES.forEach((city) => {
        s.gaps[city] = 120 + (s.spot[city] % 400)
      })
      return { salesSpot: s.spot, salesUnshipped: s.unshipped, salesGaps: s.gaps }
    })(),
  },
]

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
