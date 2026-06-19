"""Sync bridge to MDM catalog tables — isolated async engine per call (never shares app pool)."""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.mdm_models import MdmPackage, MdmPackageService, MdmService

T = TypeVar("T")


def looks_like_display_name(value: str) -> bool:
    """Heuristic: proposal display titles vs compact SKU codes."""
    s = value.strip()
    if not s:
        return False
    if len(s) > 32 and " " in s:
        return True
    if " & " in s or " — " in s or " – " in s:
        return True
    return False


@dataclass(frozen=True)
class SelectionResolveResult:
    services: list[dict[str, Any]]
    unresolved: list[str]
    resolved_by_name: list[str]


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


def _norm_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


async def _resolve_services_for_selection(
    category_id: str, identifiers: list[str]
) -> SelectionResolveResult:
    if not identifiers:
        return SelectionResolveResult(services=[], unresolved=[], resolved_by_name=[])

    async with _ephemeral_session() as session:
        by_sku_rows = (
            await session.scalars(
                select(MdmService).where(
                    MdmService.category_id == category_id,
                    MdmService.sku.in_(identifiers),
                    MdmService.status == "ACTIVE",
                )
            )
        ).all()
        sku_map = {row.sku: row for row in by_sku_rows}

        missing = [ident for ident in identifiers if ident not in sku_map]
        name_map: dict[str, MdmService] = {}
        if missing:
            active_rows = (
                await session.scalars(
                    select(MdmService).where(
                        MdmService.category_id == category_id,
                        MdmService.status == "ACTIVE",
                    )
                )
            ).all()
            for row in active_rows:
                label = row.service_name_on_proposal or row.product_name or ""
                key = _norm_label(label)
                if key and key not in name_map:
                    name_map[key] = row

        ordered: list[dict[str, Any]] = []
        unresolved: list[str] = []
        resolved_by_name: list[str] = []
        seen_skus: set[str] = set()

        for ident in identifiers:
            row = sku_map.get(ident)
            via_name = False
            if row is None:
                row = name_map.get(_norm_label(ident))
                via_name = row is not None
            if row is None:
                unresolved.append(ident)
                continue
            if row.sku in seen_skus:
                continue
            seen_skus.add(row.sku)
            ordered.append(_service_to_dict(row))
            if via_name:
                resolved_by_name.append(ident)

        return SelectionResolveResult(
            services=ordered,
            unresolved=unresolved,
            resolved_by_name=resolved_by_name,
        )


async def _fetch_services_by_skus(category_id: str, skus: list[str]) -> list[dict[str, Any]]:
    return (await _resolve_services_for_selection(category_id, skus)).services


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


def resolve_services_for_selection(category_id: str, identifiers: list[str]) -> SelectionResolveResult:
    return _run_async(_resolve_services_for_selection(category_id, identifiers))


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
