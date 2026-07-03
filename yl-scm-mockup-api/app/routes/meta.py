from flask import Blueprint, jsonify

from app.config import load_region_config, settings
from app.repositories import transfer_allocation as repo

bp = Blueprint("meta", __name__, url_prefix="/api/v1/meta")


@bp.get("/filters/plan")
def plan_filters():
    business_code = settings.default_business_code
    cfg = load_region_config()

    warehouses = repo.fetch_meta_warehouses(business_code)
    base_labels = cfg.get("base_warehouse_labels") or {}
    sales_labels = cfg.get("sales_warehouse_labels") or {}

    base_warehouses = [
        base_labels.get(w["site_name"], w["site_name"].replace("基地仓", "基地"))
        for w in warehouses
        if w["site_type"] == 0 and w["site_name"] in base_labels
    ]
    sales_warehouses = [
        sales_labels.get(w["site_name"], w["site_name"].replace("销售仓", ""))
        for w in warehouses
        if w["site_type"] == 1 and w["site_name"] in sales_labels
    ]

    products = repo.fetch_meta_products(business_code)
    series = repo.fetch_meta_series(business_code)

    return jsonify(
        {
            "filter_options": {
                "business_units": [settings.default_business_unit],
                "product_series": series,
                "base_warehouses": base_warehouses,
                "sales_warehouses": sales_warehouses,
                "products": [
                    {"code": p["product_code"], "name": p["product_name"]}
                    for p in products
                ],
            }
        }
    )
