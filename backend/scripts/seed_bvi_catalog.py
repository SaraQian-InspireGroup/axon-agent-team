#!/usr/bin/env python3
"""Load BVI MDM catalog snapshot into PostgreSQL (harneys-bvi only)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import get_async_session_factory, init_db_engine
from app.mdm.seed import count_mdm_rows, seed_bvi_catalog
from app.mdm.snapshot_io import DEFAULT_BVI_JSON, load_bvi_catalog_json


async def run(*, json_path: Path) -> None:
    if not json_path.exists():
        raise SystemExit(f"Missing BVI catalog snapshot: {json_path}")

    snapshot = load_bvi_catalog_json(json_path)
    init_db_engine()
    factory = get_async_session_factory()
    async with factory() as session:
        counts = await seed_bvi_catalog(session, snapshot)
        print("Seeded BVI MDM catalog:", counts)
        verify = await count_mdm_rows(session)
        print("Verified row counts:", verify)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed harneys-bvi mdm_* rows from JSON snapshot")
    parser.add_argument("--json", type=Path, default=DEFAULT_BVI_JSON)
    args = parser.parse_args()
    asyncio.run(run(json_path=args.json))


if __name__ == "__main__":
    main()
