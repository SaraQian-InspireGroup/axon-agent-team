from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegionAllocationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    region: str
    assign_qty: float | str | None = None
    issued_not_shipped: float | None = None
    pre_prod_stock_rate: float | None = None
    post_prod_stock_rate: float | None = None
    order_complete_rate: float | None = None
    stock_days_after: float | None = None
    next_month_days: float | None = None


class TransferRowDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    base_warehouse: str
    product_name: str
    product_code: str
    monthly_inbound: float | str | None = None
    normal_transit: float = 0
    transfer_transit: float = 0
    pending_inspect: float = 0
    pending_unpublish: float = 0
    qualified: float = 0
    qualified_unpublish: float = 0
    available_qty: float = 0
    regions: list[RegionAllocationDTO] = Field(default_factory=list)


class TransferListResponse(BaseModel):
    items: list[TransferRowDTO]
    total: int
    updated_at: str
    filters_applied: dict[str, Any] = Field(default_factory=dict)
