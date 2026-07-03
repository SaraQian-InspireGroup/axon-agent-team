from datetime import date

from flask import Blueprint, jsonify, request

from app.services import national_inventory as national_service
from app.services import transfer_allocation as service

bp = Blueprint("plan_transfer", __name__, url_prefix="/api/v1/plan")


def _parse_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    return date.fromisoformat(value.strip())


@bp.get("/transfer-allocation")
def transfer_allocation():
    result = service.list_transfer_allocation(
        business_unit=request.args.get("business_unit"),
        product_name=request.args.get("product_name"),
        base_warehouse=request.args.get("base_warehouse"),
        sales_warehouse=request.args.get("sales_warehouse"),
        product_series=request.args.get("product_series"),
        adjust_date=_parse_date(request.args.get("adjust_date")),
    )
    return jsonify(result.model_dump(by_alias=False))


@bp.get("/national-inventory")
def national_inventory():
    result = national_service.list_national_inventory(
        business_unit=request.args.get("business_unit"),
        product_name=request.args.get("product_name"),
        product_series=request.args.get("product_series"),
        adjust_date=_parse_date(request.args.get("date")),
    )
    return jsonify(result.model_dump(by_alias=False))
