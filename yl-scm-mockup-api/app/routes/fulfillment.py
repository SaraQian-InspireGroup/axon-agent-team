from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.services import branch_replenishment as service
from app.schemas.branch_replenishment import (
    CreateBranchReplenishmentRequest,
    GenerateTransferRequest,
)

bp = Blueprint("fulfillment", __name__, url_prefix="/api/v1/fulfillment")


@bp.get("/branch-replenishment")
def list_branch_replenishment():
    result = service.list_branch_replenishment(
        inbound_logic_warehouse=request.args.get("inbound_logic_warehouse"),
        outbound_logic_warehouse=request.args.get("outbound_logic_warehouse"),
        initial_ship_warehouse=request.args.get("initial_ship_warehouse"),
        business_unit=request.args.get("business_unit"),
        status=request.args.get("status"),
        transfer_gen_status=request.args.get("transfer_gen_status"),
        product_name=request.args.get("product_name"),
        source_order_no=request.args.get("source_order_no"),
        created_from=request.args.get("created_from"),
        created_to=request.args.get("created_to"),
        updated_from=request.args.get("updated_from"),
        updated_to=request.args.get("updated_to"),
        upstream_created_from=request.args.get("upstream_created_from"),
        upstream_created_to=request.args.get("upstream_created_to"),
    )
    return jsonify(result.model_dump(by_alias=False))


@bp.post("/branch-replenishment")
def create_branch_replenishment():
    try:
        body = CreateBranchReplenishmentRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    try:
        result = service.create_branch_replenishment(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result.model_dump(by_alias=False)), 201


@bp.post("/branch-replenishment/generate-transfer")
def generate_transfer():
    try:
        body = GenerateTransferRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    try:
        result = service.generate_transfer(ids=body.ids)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result.model_dump(by_alias=False))
