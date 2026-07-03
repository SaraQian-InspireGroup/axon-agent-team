import type {
  RegionAllocation,
  TransferRow,
  NationalInventoryRow,
  BranchReplenishmentOrder,
} from '../data/mockData'

const API = (import.meta.env.VITE_MOCKUP_API_BASE_URL || 'http://localhost:5001/api/v1').replace(
  /\/$/,
  '',
)

export interface PlanFilterOptions {
  business_units: string[]
  product_series: string[]
  base_warehouses: string[]
  sales_warehouses: string[]
  products: { code: string; name: string }[]
}

interface ApiRegion {
  region: string
  assign_qty?: number | string | null
  issued_not_shipped?: number | null
  pre_prod_stock_rate?: number | null
  post_prod_stock_rate?: number | null
  order_complete_rate?: number | null
  stock_days_after?: number | null
  next_month_days?: number | null
}

interface ApiTransferRow {
  id: string
  base_warehouse: string
  product_name: string
  product_code: string
  monthly_inbound?: number | string | null
  normal_transit: number
  transfer_transit: number
  pending_inspect: number
  pending_unpublish: number
  qualified: number
  qualified_unpublish: number
  available_qty: number
  regions: ApiRegion[]
}

interface TransferListResponse {
  items: ApiTransferRow[]
  total: number
  updated_at: string
}

interface ApiNationalInventoryRow {
  date: string
  series: string
  product_name: string
  product_code: string
  total_inventory: number
  base_warehouses: Record<string, number | null>
  sales_spot: Record<string, number | null>
  sales_unshipped: Record<string, number | null>
  sales_gaps: Record<string, number | null>
}

interface NationalInventoryListResponse {
  items: ApiNationalInventoryRow[]
  total: number
  updated_at: string
  base_warehouse_columns: string[]
  sales_city_columns: string[]
}

export interface FulfillmentFilterOptions {
  business_units: string[]
  logic_warehouses: string[]
  initial_ship_warehouses: string[]
  transit_warehouses: string[]
  statuses: string[]
  transfer_gen_statuses: string[]
  products: string[]
}

interface ApiBranchReplenishmentActions {
  split: boolean
  invalidate: boolean
  increase: boolean
  log: boolean
}

interface ApiBranchReplenishmentRow {
  id: string
  transfer_order_no: string
  product_code: string
  sku_code: string
  product_name: string
  unit: string
  business_unit: string
  ecommerce_barcode: string | null
  merchant_order_no: string | null
  status: string
  transfer_gen_status: string
  transfer_qty: number
  gross_weight_per_ton: number | null
  total_gross_weight_ton: number | null
  net_weight_per_ton: number | null
  total_net_weight_ton: number | null
  volume_m3: number | null
  total_volume_m3: number | null
  temp_zone: string | null
  initial_ship_warehouse: string | null
  outbound_logic_warehouse: string | null
  transit_warehouse: string | null
  inbound_logic_warehouse: string | null
  source_order_no: string | null
  actions: ApiBranchReplenishmentActions
}

interface BranchReplenishmentListResponse {
  items: ApiBranchReplenishmentRow[]
  total: number
  updated_at: string
  totals: {
    transfer_qty: number
    total_gross_weight_ton: number
    total_net_weight_ton: number
    total_volume_m3: number
  }
}

export interface CreateBranchReplenishmentPayload {
  product_code: string
  sku_code?: string
  initial_ship_warehouse: string
  outbound_logic_warehouse: string
  inbound_logic_warehouse: string
  transfer_qty: number
  planned_ship_at: string
  expected_arrival_at: string
  business_unit: string
  merchant_order_no?: string
  source_order_no?: string
  transit_warehouse?: string
  shipping_remark?: string
  temp_zone?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

function normalizeQty(value: number | string | null | undefined): number | '' {
  if (value === null || value === undefined || value === '') return ''
  const num = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(num) ? num : ''
}

function mapRegion(r: ApiRegion): RegionAllocation {
  return {
    region: r.region,
    assignQty: normalizeQty(r.assign_qty),
    issuedNotShipped: r.issued_not_shipped ?? 0,
    preProdStockRate: r.pre_prod_stock_rate ?? null,
    postProdStockRate: r.post_prod_stock_rate ?? null,
    orderCompleteRate: r.order_complete_rate ?? 0,
    stockDaysAfter: r.stock_days_after ?? 0,
    nextMonthDays: r.next_month_days ?? 0,
  }
}

function mapRow(row: ApiTransferRow): TransferRow {
  return {
    id: row.id,
    baseWarehouse: row.base_warehouse,
    productName: row.product_name,
    monthlyInbound: normalizeQty(row.monthly_inbound),
    normalTransit: row.normal_transit,
    transferTransit: row.transfer_transit,
    pendingInspect: row.pending_inspect,
    pendingUnpublish: row.pending_unpublish,
    qualified: row.qualified,
    qualifiedUnpublish: row.qualified_unpublish,
    availableQty: row.available_qty,
    regions: row.regions.map(mapRegion),
  }
}

function mapNationalRow(row: ApiNationalInventoryRow): NationalInventoryRow {
  return {
    date: row.date,
    series: row.series,
    productName: row.product_name,
    productCode: row.product_code,
    totalInventory: row.total_inventory,
    baseWarehouses: row.base_warehouses,
    salesSpot: row.sales_spot,
    salesUnshipped: row.sales_unshipped,
    salesGaps: row.sales_gaps,
  }
}

function mapBranchReplenishmentRow(row: ApiBranchReplenishmentRow): BranchReplenishmentOrder {
  return {
    id: row.id,
    transferOrderNo: row.transfer_order_no,
    productCode: row.product_code,
    skuCode: row.sku_code,
    productName: row.product_name,
    unit: row.unit,
    businessUnit: row.business_unit,
    ecommerceBarcode: row.ecommerce_barcode,
    merchantOrderNo: row.merchant_order_no,
    status: row.status,
    transferGenStatus: row.transfer_gen_status,
    transferQty: row.transfer_qty,
    grossWeightPerTon: row.gross_weight_per_ton ?? 0,
    totalGrossWeightTon: row.total_gross_weight_ton ?? 0,
    netWeightPerTon: row.net_weight_per_ton ?? 0,
    totalNetWeightTon: row.total_net_weight_ton ?? 0,
    volumeM3: row.volume_m3 ?? 0,
    totalVolumeM3: row.total_volume_m3 ?? 0,
    tempZone: row.temp_zone ?? '常温',
    initialShipWarehouse: row.initial_ship_warehouse ?? '',
    outboundLogicWarehouse: row.outbound_logic_warehouse ?? '',
    transitWarehouse: row.transit_warehouse ?? '-',
    inboundLogicWarehouse: row.inbound_logic_warehouse ?? '',
    sourceOrderNo: row.source_order_no ?? '',
    actions: row.actions,
  }
}

export const mockupApi = {
  fetchPlanFilters: () =>
    request<{ filter_options: PlanFilterOptions }>('/meta/filters/plan').then(
      (r) => r.filter_options,
    ),

  fetchTransferAllocation: (params: Record<string, string>) => {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value.trim()) qs.set(key, value.trim())
    }
    const query = qs.toString()
    return request<TransferListResponse>(
      `/plan/transfer-allocation${query ? `?${query}` : ''}`,
    ).then((r) => ({
      rows: r.items.map(mapRow),
      updatedAt: r.updated_at,
      total: r.total,
    }))
  },

  fetchNationalInventory: (params: Record<string, string>) => {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value.trim()) qs.set(key, value.trim())
    }
    const query = qs.toString()
    return request<NationalInventoryListResponse>(
      `/plan/national-inventory${query ? `?${query}` : ''}`,
    ).then((r) => ({
      rows: r.items.map(mapNationalRow),
      updatedAt: r.updated_at,
      total: r.total,
      baseWarehouseColumns: r.base_warehouse_columns,
      salesCityColumns: r.sales_city_columns,
    }))
  },

  fetchFulfillmentFilters: () =>
    request<{ filter_options: FulfillmentFilterOptions }>('/meta/filters/fulfillment').then(
      (r) => r.filter_options,
    ),

  fetchBranchReplenishment: (params: Record<string, string>) => {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value.trim()) qs.set(key, value.trim())
    }
    const query = qs.toString()
    return request<BranchReplenishmentListResponse>(
      `/fulfillment/branch-replenishment${query ? `?${query}` : ''}`,
    ).then((r) => ({
      rows: r.items.map(mapBranchReplenishmentRow),
      updatedAt: r.updated_at,
      total: r.total,
      totals: {
        transferQty: r.totals.transfer_qty,
        totalGrossWeightTon: r.totals.total_gross_weight_ton,
        totalNetWeightTon: r.totals.total_net_weight_ton,
        totalVolumeM3: r.totals.total_volume_m3,
      },
    }))
  },

  createBranchReplenishment: (payload: CreateBranchReplenishmentPayload) =>
    request<{ item: ApiBranchReplenishmentRow }>('/fulfillment/branch-replenishment', {
      method: 'POST',
      body: JSON.stringify(payload),
    }).then((r) => mapBranchReplenishmentRow(r.item)),

  generateTransferOrders: (ids: string[]) =>
    request<{ updated_count: number; items: ApiBranchReplenishmentRow[]; skipped: { id: string; reason: string }[] }>(
      '/fulfillment/branch-replenishment/generate-transfer',
      { method: 'POST', body: JSON.stringify({ ids }) },
    ).then((r) => ({
      updatedCount: r.updated_count,
      items: r.items.map(mapBranchReplenishmentRow),
      skipped: r.skipped,
    })),
}
