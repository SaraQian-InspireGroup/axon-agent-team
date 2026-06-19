#!/usr/bin/env python3
"""Export BVI MDM catalog snapshot JSON from the bundled Excel workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.mdm.excel_import import default_bvi_xlsx_path, parse_bvi_catalog
from app.mdm.snapshot_io import DEFAULT_BVI_JSON, export_bvi_catalog_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Export BVI catalog JSON for Alembic seed migration")
    parser.add_argument("--bvi-xlsx", type=Path, default=default_bvi_xlsx_path())
    parser.add_argument("--out", type=Path, default=DEFAULT_BVI_JSON)
    args = parser.parse_args()

    out_path = export_bvi_catalog_json(bvi_xlsx=args.bvi_xlsx, out_path=args.out)
    services, packages = parse_bvi_catalog(args.bvi_xlsx)
    linked = sum(len(pkg.linked_skus) for pkg in packages)
    print(f"Wrote {out_path}")
    print(f"Services: {len(services)}")
    print(f"Packages: {len(packages)}")
    print(f"Package links: {linked}")


if __name__ == "__main__":
    main()
