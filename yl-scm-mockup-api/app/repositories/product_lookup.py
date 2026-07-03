"""从 YL 主数据读取商品属性."""

from __future__ import annotations

from app.config import settings
from app.db.yl import yl_connection

PRODUCT_SQL = """
SELECT product_code, product_name, weight, volume, business, pack_type
FROM yl_product
WHERE product_code = %(product_code)s
  AND business_code = %(business_code)s
  AND is_delete = 0
LIMIT 1
"""


def fetch_product(product_code: str) -> dict | None:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                PRODUCT_SQL,
                {
                    "product_code": product_code.strip(),
                    "business_code": settings.default_business_code,
                },
            )
            return cur.fetchone()
