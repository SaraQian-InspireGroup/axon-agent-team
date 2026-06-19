"""Persist MDM catalog snapshots to PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mdm_models import (
    MdmPackage,
    MdmPackageNameAlias,
    MdmPackageService,
    MdmService,
)
from app.mdm.excel_import import MdmCatalogSnapshot, PackageRecord, ServiceRecord


def _service_model(record: ServiceRecord) -> MdmService:
    return MdmService(
        sku=record.sku,
        category_id=record.category_id,
        region=record.region,
        bu=record.bu,
        department_team=record.department_team,
        service_group=record.service_group,
        service_group_display=record.service_group_display,
        product_name=record.product_name,
        service_name_on_proposal=record.service_name_on_proposal,
        description=record.description,
        scope_of_work=record.scope_of_work,
        service_type=record.service_type,
        billing_frequency=record.billing_frequency,
        recurring=record.recurring,
        status=record.status,
        pricing_type=record.pricing_type,
        price_currency=record.price_currency,
        price_amount=record.price_amount,
        price_min=record.price_min,
        price_max=record.price_max,
        price_spec=record.price_spec,
        fee_raw=record.fee_raw,
        footnotes=record.footnotes,
        sku_semantic_for_ai=record.sku_semantic_for_ai,
        external_record_id=record.external_record_id,
        source_sheet=record.source_sheet,
        source_row=record.source_row,
        extensions=record.extensions,
    )


def _package_model(record: PackageRecord) -> MdmPackage:
    return MdmPackage(
        package_id=record.package_id,
        category_id=record.category_id,
        region=record.region,
        bu=record.bu,
        package_name=record.package_name,
        package_detail=record.package_detail,
        package_semantic_for_ai=record.package_semantic_for_ai,
        status=record.status,
    )


async def clear_mdm_catalog(session: AsyncSession) -> None:
    await session.execute(delete(MdmPackageNameAlias))
    await session.execute(delete(MdmPackageService))
    await session.execute(delete(MdmPackage))
    await session.execute(delete(MdmService))


async def seed_mdm_catalog(session: AsyncSession, snapshot: MdmCatalogSnapshot) -> dict[str, int]:
    await clear_mdm_catalog(session)

    sku_index: dict[tuple[str, str], MdmService] = {}
    for service in snapshot.services:
        model = _service_model(service)
        session.add(model)
        sku_index[(service.category_id, service.sku)] = model

    await session.flush()

    for row in sku_index.values():
        await session.refresh(row)

    for package in snapshot.packages:
        session.add(_package_model(package))
        for sku in package.linked_skus:
            service = sku_index.get((package.category_id, sku))
            if service is None:
                continue
            session.add(
                MdmPackageService(
                    package_id=package.package_id,
                    category_id=package.category_id,
                    sku=sku,
                    service_id=service.id,
                )
            )

    for alias in snapshot.package_aliases:
        session.add(
            MdmPackageNameAlias(
                region=alias.region,
                legacy_name=alias.legacy_name,
                canonical_name=alias.canonical_name,
            )
        )

    await session.commit()
    return {
        "services": len(snapshot.services),
        "packages": len(snapshot.packages),
        "package_aliases": len(snapshot.package_aliases),
    }


async def count_mdm_rows(session: AsyncSession) -> dict[str, int]:
    return {
        "services": len((await session.scalars(select(MdmService.id))).all()),
        "packages": len((await session.scalars(select(MdmPackage.package_id))).all()),
        "package_aliases": len((await session.scalars(select(MdmPackageNameAlias.id))).all()),
    }
