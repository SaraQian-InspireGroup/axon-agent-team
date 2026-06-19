"""Seed the BVI MDM catalog snapshot for the Alembic migration."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection
from app.mdm.snapshot_io import MdmCatalogSnapshot

BVI_REGION = "BVI"
BVI_BU = "Harneys"

_SERVICE_INSERT = (
    sa.text(
        """
        INSERT INTO mdm_services (
            sku, region, bu, department_team, service_group, service_group_display,
            product_name, service_name_on_proposal, description, scope_of_work,
            service_type, billing_frequency, recurring, status, pricing_type,
            price_currency, price_amount, price_min, price_max, price_spec,
            fee_raw, footnotes, sku_semantic_for_ai, external_record_id,
            source_sheet, source_row, extensions
        )
        VALUES (
            :sku, :region, :bu, :department_team, :service_group, :service_group_display,
            :product_name, :service_name_on_proposal, :description, :scope_of_work,
            :service_type, :billing_frequency, :recurring, :status, :pricing_type,
            :price_currency, :price_amount, :price_min, :price_max, :price_spec,
            :fee_raw, :footnotes, :sku_semantic_for_ai, :external_record_id,
            :source_sheet, :source_row, :extensions
        )
        RETURNING id
        """
    )
    .bindparams(sa.bindparam("price_spec", type_=JSONB))
    .bindparams(sa.bindparam("extensions", type_=JSONB))
)

_PACKAGE_INSERT = sa.text(
    """
    INSERT INTO mdm_packages (
        package_id, region, bu, package_name, package_semantic_for_ai, status
    )
    VALUES (
        :package_id, :region, :bu, :package_name, :package_semantic_for_ai, :status
    )
    """
)

_LINK_INSERT = sa.text(
    """
    INSERT INTO mdm_package_services (package_id, sku, service_id)
    VALUES (:package_id, :sku, :service_id)
    ON CONFLICT (package_id, sku) DO NOTHING
    """
)


def _clear_bvi_catalog(connection: Connection) -> None:
    connection.execute(
        sa.text(
            """
            DELETE FROM mdm_package_services ps
            USING mdm_packages p
            WHERE ps.package_id = p.package_id
              AND p.region = :region
              AND p.bu = :bu
            """
        ),
        {"region": BVI_REGION, "bu": BVI_BU},
    )
    connection.execute(
        sa.text("DELETE FROM mdm_packages WHERE region = :region AND bu = :bu"),
        {"region": BVI_REGION, "bu": BVI_BU},
    )
    connection.execute(
        sa.text("DELETE FROM mdm_services WHERE region = :region AND bu = :bu"),
        {"region": BVI_REGION, "bu": BVI_BU},
    )


def seed_bvi_catalog_sync(connection: Connection, snapshot: MdmCatalogSnapshot) -> dict[str, int]:
    _clear_bvi_catalog(connection)
    sku_index = {}
    for service in snapshot.services:
        service_id = connection.execute(_SERVICE_INSERT, service.__dict__).scalar_one()
        sku_index[(service.region, service.bu, service.sku)] = service_id

    for package in snapshot.packages:
        connection.execute(
            _PACKAGE_INSERT,
            {
                "package_id": package.package_id,
                "region": package.region,
                "bu": package.bu,
                "package_name": package.package_name,
                "package_semantic_for_ai": package.package_semantic_for_ai,
                "status": package.status,
            },
        )
        for sku in package.linked_skus:
            service_id = sku_index.get((package.region, package.bu, sku))
            if service_id is None:
                continue
            connection.execute(
                _LINK_INSERT,
                {
                    "package_id": package.package_id,
                    "sku": sku,
                    "service_id": service_id,
                },
            )

    return {
        "services": len(snapshot.services),
        "packages": len(snapshot.packages),
    }
