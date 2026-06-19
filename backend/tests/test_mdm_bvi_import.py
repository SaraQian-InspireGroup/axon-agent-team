from decimal import Decimal
from pathlib import Path

import pytest

from app.mdm.excel_import import (
    BVI_CATEGORY_ID,
    au_department_team_from_sku,
    canonical_au_package_label,
    default_bvi_xlsx_path,
    normalize_package_sku_ref,
    parse_bvi_catalog,
    parse_bvi_fee,
    parse_bvi_services,
)
from app.mdm.snapshot_io import export_bvi_catalog_json, load_bvi_catalog_json


@pytest.fixture(scope="module")
def bvi_xlsx() -> Path:
    path = default_bvi_xlsx_path()
    if not path.exists():
        pytest.skip(f"Missing bundled BVI workbook: {path}")
    return path


def test_parse_bvi_services_uses_source_skus(bvi_xlsx: Path) -> None:
    services = parse_bvi_services(bvi_xlsx)
    assert len(services) == 168
    assert all(service.category_id == BVI_CATEGORY_ID for service in services)
    assert services[0].sku == "CSS001"
    assert services[0].service_group == "incorporation"
    assert services[0].external_record_id == "CSS001"


def test_parse_bvi_packages_links_normalized_skus(bvi_xlsx: Path) -> None:
    services, packages = parse_bvi_catalog(bvi_xlsx)
    known = {service.sku for service in services}
    incorp = next(pkg for pkg in packages if pkg.package_id == "PKG001")
    annual = next(pkg for pkg in packages if pkg.package_id == "PKG002")
    rta = next(pkg for pkg in packages if pkg.package_id == "PKG013")

    assert incorp.package_name == "Incorporation"
    assert incorp.linked_skus == [
        "CSS001",
        "CSS002",
        "CSS003",
        "CSS004",
        "CSS005",
        "CSS006",
        "CSS007",
        "CSS008",
    ]
    assert "CSS009" in annual.linked_skus
    assert annual.linked_skus.count("CSS011") == 1
    assert "COM034" in rta.linked_skus
    assert all(sku in known for pkg in packages for sku in pkg.linked_skus)


def test_parse_bvi_fee_patterns() -> None:
    ptype, _, amt, pmin, pmax, _ = parse_bvi_fee("120 - 663")
    assert ptype == "RANGE"
    assert pmin == Decimal("120")
    assert pmax == Decimal("663")
    assert amt is None

    ptype, pextra, amt, _, _, _ = parse_bvi_fee("$7,066 per annum")
    assert ptype == "FIXED"
    assert amt == Decimal("7066")
    assert pextra.get("billing_note") == "per annum"


def test_normalize_package_sku_ref_zero_pads_and_fixes_om_typo() -> None:
    known = {"COM014", "COM034", "CSS001"}
    assert normalize_package_sku_ref("COM14", known) == "COM014"
    assert normalize_package_sku_ref("OM34", known) == "COM034"


def test_canonical_au_package_label_uses_star_separator() -> None:
    assert (
        canonical_au_package_label("Tax Package 1 - Default Australia Compliance Services Product Suite")
        == "Tax Package 1*Default Australia Compliance Services Product Suite"
    )
    assert (
        canonical_au_package_label("SMSF Package 2*New Fund + Setup + Advice")
        == "SMSF Package 2*New Fund + Setup + Advice"
    )


def test_au_department_team_from_sku_uses_full_names() -> None:
    assert au_department_team_from_sku("TA05") == "Tax and Advisory"
    assert au_department_team_from_sku("TA NEW ITEM NUMBER 10") == "Tax and Advisory"
    assert au_department_team_from_sku("CSS23") == "Corporate Secretarial Services"
    assert au_department_team_from_sku("SMSF001") == "SMSF"
    assert au_department_team_from_sku("GI01") == "Global Incentive"


def test_bvi_snapshot_roundtrip(bvi_xlsx: Path, tmp_path: Path) -> None:
    out = tmp_path / "bvi_catalog.json"
    export_bvi_catalog_json(bvi_xlsx=bvi_xlsx, out_path=out)
    snapshot = load_bvi_catalog_json(out)
    assert len(snapshot.services) == 168
    assert len(snapshot.packages) == 15
    assert snapshot.services[0].price_amount == Decimal("440")
