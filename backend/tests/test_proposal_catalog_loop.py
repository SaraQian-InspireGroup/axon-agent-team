from unittest.mock import AsyncMock, patch

import pytest

from app.db.session import check_db_connection, init_db_engine


@pytest.mark.asyncio
async def test_catalog_fetch_from_running_loop_does_not_break_app_pool():
    """Sync catalog calls from the uvicorn loop must not poison the shared async engine."""
    init_db_engine()
    await check_db_connection()

    async def _fake_fetch(category_id: str, skus: list[str]):
        return [{"sku": skus[0], "category_id": category_id}] if skus else []

    with patch(
        "app.proposal.catalog._fetch_services_by_skus",
        new=AsyncMock(side_effect=_fake_fetch),
    ):
        from app.proposal.catalog import fetch_services_by_skus

        rows = fetch_services_by_skus("au-services", ["SKU-1"])
        assert rows[0]["sku"] == "SKU-1"

    await check_db_connection()
