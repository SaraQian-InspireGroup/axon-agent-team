from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BranchReplenishmentActionsDTO(BaseModel):
    split: bool = False
    invalidate: bool = False
    increase: bool = False
    log: bool = True


class BranchReplenishmentOrderDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    transfer_order_no: str
    product_code: str
    sku_code: str
    product_name: str
    unit: str = "EA"
    business_unit: str
    ecommerce_barcode: str | None = None
    merchant_order_no: str | None = None
    status: str
    transfer_gen_status: str
    transfer_qty: float
    gross_weight_per_ton: float | None = None
    total_gross_weight_ton: float | None = None
    net_weight_per_ton: float | None = None
    total_net_weight_ton: float | None = None
    volume_m3: float | None = None
    total_volume_m3: float | None = None
    temp_zone: str | None = "常温"
    initial_ship_warehouse: str | None = None
    outbound_logic_warehouse: str | None = None
    transit_warehouse: str | None = "-"
    inbound_logic_warehouse: str | None = None
    source_order_no: str | None = None
    planned_ship_at: str | None = None
    expected_arrival_at: str | None = None
    shipping_remark: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    upstream_created_at: str | None = None
    actions: BranchReplenishmentActionsDTO = Field(default_factory=BranchReplenishmentActionsDTO)


class BranchReplenishmentTotalsDTO(BaseModel):
    transfer_qty: float = 0
    total_gross_weight_ton: float = 0
    total_net_weight_ton: float = 0
    total_volume_m3: float = 0


class BranchReplenishmentListResponse(BaseModel):
    items: list[BranchReplenishmentOrderDTO]
    total: int
    updated_at: str
    totals: BranchReplenishmentTotalsDTO
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class CreateBranchReplenishmentRequest(BaseModel):
    product_code: str
    sku_code: str | None = None
    initial_ship_warehouse: str
    outbound_logic_warehouse: str
    inbound_logic_warehouse: str
    transfer_qty: float
    planned_ship_at: datetime
    expected_arrival_at: datetime
    business_unit: str
    merchant_order_no: str | None = None
    source_order_no: str | None = None
    transit_warehouse: str | None = "-"
    shipping_remark: str | None = None
    temp_zone: str | None = "常温"


class CreateBranchReplenishmentResponse(BaseModel):
    item: BranchReplenishmentOrderDTO


class GenerateTransferRequest(BaseModel):
    ids: list[str] = Field(min_length=1)


class GenerateTransferResponse(BaseModel):
    updated_count: int
    items: list[BranchReplenishmentOrderDTO]
    skipped: list[dict[str, str]] = Field(default_factory=list)
