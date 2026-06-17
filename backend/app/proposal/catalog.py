"""Sync bridge to MDM catalog tables — isolated async engine per call (never shares app pool)."""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Coroutine, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.mdm_models import MdmPackage, MdmPackageService, MdmService

T = TypeVar("T")


@asynccontextmanager
async def _ephemeral_session() -> AsyncIterator[AsyncSession]:
    """Short-lived engine/session so sync tools never touch the app's async pool."""
    settings = get_settings()
    engine = create_async_engine(
        settings.async_database_url,
        connect_args=settings.async_database_connect_args,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _fetch_services_by_skus(category_id: str, skus: list[str]) -> list[dict[str, Any]]:
    if not skus:
        return []
    async with _ephemeral_session() as session:
        rows = (
            await session.scalars(
                select(MdmService).where(
                    MdmService.category_id == category_id,
                    MdmService.sku.in_(skus),
                    MdmService.status == "ACTIVE",
                )
            )
        ).all()
        return [_service_to_dict(row) for row in rows]


async def _fetch_packages_by_ids(
    category_id: str, package_ids: list[str]
) -> list[dict[str, Any]]:
    if not package_ids:
        return []
    async with _ephemeral_session() as session:
        packages = (
            await session.scalars(
                select(MdmPackage).where(
                    MdmPackage.category_id == category_id,
                    MdmPackage.package_id.in_(package_ids),
                    MdmPackage.status == "ACTIVE",
                )
            )
        ).all()
        if not packages:
            return []
        links = (
            await session.scalars(
                select(MdmPackageService).where(
                    MdmPackageService.category_id == category_id,
                    MdmPackageService.package_id.in_(package_ids),
                )
            )
        ).all()
        skus_by_package: dict[str, list[str]] = {pkg.package_id: [] for pkg in packages}
        for link in links:
            skus_by_package.setdefault(link.package_id, []).append(link.sku)
        ordered: list[dict[str, Any]] = []
        pkg_by_id = {pkg.package_id: pkg for pkg in packages}
        for package_id in package_ids:
            pkg = pkg_by_id.get(package_id)
            if not pkg:
                continue
            ordered.append(
                {
                    "package_id": pkg.package_id,
                    "package_name": pkg.package_name,
                    "package_detail": pkg.package_detail,
                    "linked_skus": skus_by_package.get(package_id, []),
                }
            )
        return ordered


async def _fetch_package_skus(category_id: str, package_ids: list[str]) -> list[str]:
    if not package_ids:
        return []
    async with _ephemeral_session() as session:
        rows = (
            await session.scalars(
                select(MdmPackageService).where(
                    MdmPackageService.category_id == category_id,
                    MdmPackageService.package_id.in_(package_ids),
                )
            )
        ).all()
        return [row.sku for row in rows]


def fetch_services_by_skus(category_id: str, skus: list[str]) -> list[dict[str, Any]]:
    return _run_async(_fetch_services_by_skus(category_id, skus))


def fetch_package_skus(category_id: str, package_ids: list[str]) -> list[str]:
    return _run_async(_fetch_package_skus(category_id, package_ids))


def fetch_packages_by_ids(category_id: str, package_ids: list[str]) -> list[dict[str, Any]]:
    return _run_async(_fetch_packages_by_ids(category_id, package_ids))


def expand_selected_skus(category_id: str, selection: dict[str, Any]) -> list[str]:
    package_skus = fetch_package_skus(category_id, list(selection.get("selected_packages") or []))
    explicit = list(selection.get("selected_skus") or [])
    seen: set[str] = set()
    ordered: list[str] = []
    for sku in [*package_skus, *explicit]:
        if sku and sku not in seen:
            seen.add(sku)
            ordered.append(sku)
    return ordered


def _service_to_dict(row: MdmService) -> dict[str, Any]:
    return {
        "sku": row.sku,
        "category_id": row.category_id,
        "region": row.region,
        "bu": row.bu,
        "department_team": row.department_team,
        "service_group": row.service_group,
        "service_group_display": row.service_group_display,
        "product_name": row.product_name,
        "service_name_on_proposal": row.service_name_on_proposal,
        "description": row.description,
        "scope_of_work": row.scope_of_work,
        "service_type": row.service_type,
        "billing_frequency": row.billing_frequency,
        "recurring": row.recurring,
        "pricing_type": row.pricing_type,
        "price_currency": row.price_currency,
        "price_amount": float(row.price_amount) if row.price_amount is not None else None,
        "price_min": float(row.price_min) if row.price_min is not None else None,
        "price_max": float(row.price_max) if row.price_max is not None else None,
        "price_spec": dict(row.price_spec or {}),
        "fee_raw": row.fee_raw,
        "footnotes": row.footnotes,
    }
