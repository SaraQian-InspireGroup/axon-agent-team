#!/usr/bin/env python3
"""Load MDM catalog from source Excel into PostgreSQL (mdm_* tables)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import get_async_session_factory, init_db_engine
from app.mdm.excel_import import default_bvi_xlsx_path, load_mdm_snapshot
from app.mdm.seed import count_mdm_rows, seed_mdm_catalog


def default_bvi_xlsx() -> Path:
    return default_bvi_xlsx_path()


def default_au_xlsx() -> Path:
    return Path.home() / "Downloads/AU Hubspot Production 0407 updated.xlsx"


async def run(*, bvi_xlsx: Path, au_xlsx: Path) -> None:
    if not bvi_xlsx.exists():
        raise SystemExit(f"Missing BVI workbook: {bvi_xlsx}")
    if not au_xlsx.exists():
        raise SystemExit(f"Missing AU workbook: {au_xlsx}")

    snapshot = load_mdm_snapshot(bvi_xlsx=bvi_xlsx, au_xlsx=au_xlsx)
    init_db_engine()
    factory = get_async_session_factory()
    async with factory() as session:
        counts = await seed_mdm_catalog(session, snapshot)
        print("Seeded MDM catalog:", counts)
        verify = await count_mdm_rows(session)
        print("Verified row counts:", verify)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed mdm_* tables from Excel workbooks")
    parser.add_argument("--bvi-xlsx", type=Path, default=default_bvi_xlsx())
    parser.add_argument("--au-xlsx", type=Path, default=default_au_xlsx())
    args = parser.parse_args()
    asyncio.run(run(bvi_xlsx=args.bvi_xlsx, au_xlsx=args.au_xlsx))


if __name__ == "__main__":
    main()
