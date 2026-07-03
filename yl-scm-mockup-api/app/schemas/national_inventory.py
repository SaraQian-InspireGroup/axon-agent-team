from typing import Any

from pydantic import BaseModel, Field


class NationalInventoryRowDTO(BaseModel):
    date: str
    series: str
    product_name: str
    product_code: str
    total_inventory: float
    base_warehouses: dict[str, float | None] = Field(default_factory=dict)
    sales_spot: dict[str, float | None] = Field(default_factory=dict)
    sales_unshipped: dict[str, float | None] = Field(default_factory=dict)
    sales_gaps: dict[str, float | None] = Field(default_factory=dict)


class NationalInventoryListResponse(BaseModel):
    items: list[NationalInventoryRowDTO]
    total: int
    updated_at: str
    base_warehouse_columns: list[str] = Field(default_factory=list)
    sales_city_columns: list[str] = Field(default_factory=list)
    filters_applied: dict[str, Any] = Field(default_factory=dict)
