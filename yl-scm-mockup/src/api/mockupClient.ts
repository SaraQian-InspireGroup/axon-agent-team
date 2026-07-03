import type { RegionAllocation, TransferRow, NationalInventoryRow } from '../data/mockData'

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

function mapRegion(r: ApiRegion): RegionAllocation {
  return {
    region: r.region,
    assignQty: r.assign_qty ?? '',
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
    monthlyInbound: row.monthly_inbound ?? '',
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
}
