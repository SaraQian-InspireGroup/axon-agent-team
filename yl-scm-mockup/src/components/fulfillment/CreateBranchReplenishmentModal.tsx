import { useEffect, useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import {
  mockupApi,
  type CreateBranchReplenishmentPayload,
  type FulfillmentFilterOptions,
} from '../../api/mockupClient'

interface ProductOption {
  code: string
  name: string
}

interface CreateBranchReplenishmentModalProps {
  open: boolean
  onClose: () => void
  filterOptions: FulfillmentFilterOptions
  products: ProductOption[]
  onSuccess: () => void
}

interface FormState {
  productCode: string
  skuCode: string
  initialShipWarehouse: string
  outboundLogicWarehouse: string
  inboundLogicWarehouse: string
  transferQty: string
  plannedShipAt: string
  expectedArrivalAt: string
  businessUnit: string
  merchantOrderNo: string
  sourceOrderNo: string
  transitWarehouse: string
  shippingRemark: string
  tempZone: string
}

const TEMP_ZONE_OPTIONS = ['常温', '冷藏', '冷冻']

function defaultForm(filterOptions: FulfillmentFilterOptions): FormState {
  const now = new Date()
  const ship = new Date(now.getTime() + 24 * 60 * 60 * 1000)
  const arrival = new Date(now.getTime() + 72 * 60 * 60 * 1000)
  const fmt = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  return {
    productCode: '',
    skuCode: '',
    initialShipWarehouse: filterOptions.initial_ship_warehouses[0] ?? '',
    outboundLogicWarehouse: filterOptions.initial_ship_warehouses[0] ?? '',
    inboundLogicWarehouse: filterOptions.logic_warehouses[0] ?? '',
    transferQty: '',
    plannedShipAt: fmt(ship),
    expectedArrivalAt: fmt(arrival),
    businessUnit: filterOptions.business_units[0] ?? '',
    merchantOrderNo: '',
    sourceOrderNo: '',
    transitWarehouse: '-',
    shippingRemark: '',
    tempZone: '常温',
  }
}

function toIsoDateTime(local: string): string {
  if (!local) return ''
  const normalized = local.length === 16 ? `${local}:00` : local
  return `${normalized}+08:00`
}

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return '创建失败'
  try {
    const parsed = JSON.parse(err.message) as { error?: string; details?: unknown }
    if (parsed.error) return parsed.error
  } catch {
    /* plain text */
  }
  return err.message || '创建失败'
}

export default function CreateBranchReplenishmentModal({
  open,
  onClose,
  filterOptions,
  products,
  onSuccess,
}: CreateBranchReplenishmentModalProps) {
  const [form, setForm] = useState<FormState>(() => defaultForm(filterOptions))
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setForm(defaultForm(filterOptions))
      setFormError(null)
    }
  }, [open, filterOptions])

  if (!open) return null

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value }
      if (key === 'initialShipWarehouse') {
        if (!prev.outboundLogicWarehouse || prev.outboundLogicWarehouse === prev.initialShipWarehouse) {
          next.outboundLogicWarehouse = String(value)
        }
      }
      if (key === 'productCode' && (!prev.skuCode || prev.skuCode === prev.productCode)) {
        next.skuCode = String(value)
      }
      return next
    })
  }

  const validate = (): string | null => {
    if (!form.productCode.trim()) return '请选择商品编码'
    if (!form.initialShipWarehouse.trim()) return '请选择初始发货仓'
    if (!form.outboundLogicWarehouse.trim()) return '请选择调出逻辑仓'
    if (!form.inboundLogicWarehouse.trim()) return '请选择调入逻辑仓'
    if (!form.businessUnit.trim()) return '请选择事业部'
    const qty = Number(form.transferQty)
    if (!Number.isFinite(qty) || qty <= 0) return '调拨数量须大于 0'
    if (!form.plannedShipAt) return '请填写拟定发货时间'
    if (!form.expectedArrivalAt) return '请填写期望到货时间'
    if (form.expectedArrivalAt < form.plannedShipAt) {
      return '期望到货时间不能早于拟定发货时间'
    }
    return null
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setFormError(validationError)
      return
    }

    const payload: CreateBranchReplenishmentPayload = {
      product_code: form.productCode.trim(),
      initial_ship_warehouse: form.initialShipWarehouse.trim(),
      outbound_logic_warehouse: form.outboundLogicWarehouse.trim(),
      inbound_logic_warehouse: form.inboundLogicWarehouse.trim(),
      transfer_qty: Number(form.transferQty),
      planned_ship_at: toIsoDateTime(form.plannedShipAt),
      expected_arrival_at: toIsoDateTime(form.expectedArrivalAt),
      business_unit: form.businessUnit.trim(),
      temp_zone: form.tempZone,
      transit_warehouse: form.transitWarehouse.trim() || '-',
    }
    if (form.skuCode.trim()) payload.sku_code = form.skuCode.trim()
    if (form.merchantOrderNo.trim()) payload.merchant_order_no = form.merchantOrderNo.trim()
    if (form.sourceOrderNo.trim()) payload.source_order_no = form.sourceOrderNo.trim()
    if (form.shippingRemark.trim()) payload.shipping_remark = form.shippingRemark.trim()

    setSubmitting(true)
    setFormError(null)
    try {
      const created = await mockupApi.createBranchReplenishment(payload)
      await mockupApi.generateTransferOrders([created.id])
      onSuccess()
      onClose()
    } catch (err) {
      setFormError(parseApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fulfill-modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="fulfill-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generate-transfer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="fulfill-modal-header">
          <h2 id="generate-transfer-title" className="fulfill-modal-title">
            生成调拨单
          </h2>
          <button type="button" className="fulfill-modal-close" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </header>

        <form className="fulfill-modal-body" onSubmit={handleSubmit}>
          <section className="fulfill-form-section">
            <h3 className="fulfill-form-section-title">必填项</h3>
            <p className="fulfill-form-section-hint">
              拟定补货单并生成调拨单；商品名称、重量体积等由系统根据 SKU 自动带出。
            </p>
            <div className="fulfill-form-grid">
              <div className="fulfill-form-field fulfill-form-field-wide">
                <label className="fulfill-form-label" htmlFor="productCode">
                  商品编码 / SKU <span className="fulfill-form-required">*</span>
                </label>
                <select
                  id="productCode"
                  className="fulfill-form-select"
                  value={form.productCode}
                  onChange={(e) => setField('productCode', e.target.value)}
                  required
                >
                  <option value="">请选择商品</option>
                  {products.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.code} — {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="skuCode">
                  SKU编码
                </label>
                <input
                  id="skuCode"
                  className="fulfill-form-input"
                  value={form.skuCode}
                  onChange={(e) => setField('skuCode', e.target.value)}
                  placeholder="默认同商品编码"
                />
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="businessUnit">
                  事业部 <span className="fulfill-form-required">*</span>
                </label>
                <select
                  id="businessUnit"
                  className="fulfill-form-select"
                  value={form.businessUnit}
                  onChange={(e) => setField('businessUnit', e.target.value)}
                  required
                >
                  {filterOptions.business_units.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="transferQty">
                  调拨数量 <span className="fulfill-form-required">*</span>
                </label>
                <input
                  id="transferQty"
                  type="number"
                  min={1}
                  step={1}
                  className="fulfill-form-input"
                  value={form.transferQty}
                  onChange={(e) => setField('transferQty', e.target.value)}
                  placeholder="补货数量"
                  required
                />
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="initialShipWarehouse">
                  初始发货仓 <span className="fulfill-form-required">*</span>
                </label>
                <select
                  id="initialShipWarehouse"
                  className="fulfill-form-select"
                  value={form.initialShipWarehouse}
                  onChange={(e) => setField('initialShipWarehouse', e.target.value)}
                  required
                >
                  <option value="">请选择</option>
                  {filterOptions.initial_ship_warehouses.map((w) => (
                    <option key={w} value={w}>
                      {w}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="outboundLogicWarehouse">
                  调出逻辑仓 <span className="fulfill-form-required">*</span>
                </label>
                <select
                  id="outboundLogicWarehouse"
                  className="fulfill-form-select"
                  value={form.outboundLogicWarehouse}
                  onChange={(e) => setField('outboundLogicWarehouse', e.target.value)}
                  required
                >
                  <option value="">请选择</option>
                  {filterOptions.initial_ship_warehouses.map((w) => (
                    <option key={`out-${w}`} value={w}>
                      {w}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="inboundLogicWarehouse">
                  调入逻辑仓 <span className="fulfill-form-required">*</span>
                </label>
                <select
                  id="inboundLogicWarehouse"
                  className="fulfill-form-select"
                  value={form.inboundLogicWarehouse}
                  onChange={(e) => setField('inboundLogicWarehouse', e.target.value)}
                  required
                >
                  <option value="">请选择</option>
                  {filterOptions.logic_warehouses.map((w) => (
                    <option key={w} value={w}>
                      {w}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="plannedShipAt">
                  拟定发货时间 <span className="fulfill-form-required">*</span>
                </label>
                <input
                  id="plannedShipAt"
                  type="datetime-local"
                  className="fulfill-form-input"
                  value={form.plannedShipAt}
                  onChange={(e) => setField('plannedShipAt', e.target.value)}
                  required
                />
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="expectedArrivalAt">
                  期望到货时间 <span className="fulfill-form-required">*</span>
                </label>
                <input
                  id="expectedArrivalAt"
                  type="datetime-local"
                  className="fulfill-form-input"
                  value={form.expectedArrivalAt}
                  onChange={(e) => setField('expectedArrivalAt', e.target.value)}
                  required
                />
              </div>
            </div>
          </section>

          <section className="fulfill-form-section">
            <h3 className="fulfill-form-section-title">选填项</h3>
            <div className="fulfill-form-grid">
              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="merchantOrderNo">
                  商家订单号
                </label>
                <input
                  id="merchantOrderNo"
                  className="fulfill-form-input"
                  value={form.merchantOrderNo}
                  onChange={(e) => setField('merchantOrderNo', e.target.value)}
                  placeholder="大客户直发时填写"
                />
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="sourceOrderNo">
                  来源单号
                </label>
                <input
                  id="sourceOrderNo"
                  className="fulfill-form-input"
                  value={form.sourceOrderNo}
                  onChange={(e) => setField('sourceOrderNo', e.target.value)}
                  placeholder="关联上游需求单"
                />
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="transitWarehouse">
                  中转仓
                </label>
                <select
                  id="transitWarehouse"
                  className="fulfill-form-select"
                  value={form.transitWarehouse}
                  onChange={(e) => setField('transitWarehouse', e.target.value)}
                >
                  {filterOptions.transit_warehouses.map((w) => (
                    <option key={w} value={w}>
                      {w}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field">
                <label className="fulfill-form-label" htmlFor="tempZone">
                  温区属性
                </label>
                <select
                  id="tempZone"
                  className="fulfill-form-select"
                  value={form.tempZone}
                  onChange={(e) => setField('tempZone', e.target.value)}
                >
                  {TEMP_ZONE_OPTIONS.map((z) => (
                    <option key={z} value={z}>
                      {z}
                    </option>
                  ))}
                </select>
              </div>

              <div className="fulfill-form-field fulfill-form-field-wide">
                <label className="fulfill-form-label" htmlFor="shippingRemark">
                  特殊运输备注
                </label>
                <textarea
                  id="shippingRemark"
                  className="fulfill-form-textarea"
                  rows={2}
                  value={form.shippingRemark}
                  onChange={(e) => setField('shippingRemark', e.target.value)}
                  placeholder="如：礼盒装注意防潮、指定承运商等"
                />
              </div>
            </div>
          </section>

          {formError ? <p className="fulfill-form-error">{formError}</p> : null}

          <footer className="fulfill-modal-footer">
            <button type="button" className="btn-outline" onClick={onClose} disabled={submitting}>
              取消
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? '生成中…' : '确认生成'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}
