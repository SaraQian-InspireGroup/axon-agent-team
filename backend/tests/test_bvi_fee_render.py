from app.proposal.draft import add_package_to_draft, build_draft_preview, materialize_draft
from app.proposal.fee_table import build_fee_service_cell_html, service_column_flags


def test_bvi_service_columns_show_name_and_description_not_sow():
    columns = service_column_flags(
        {
            "service_columns": {
                "service_name": True,
                "description": True,
                "scope_of_work": False,
            }
        }
    )
    html = build_fee_service_cell_html(
        {
            "service_name": "Approved Manager",
            "description": "Registered Office/Registered Agent Fee",
            "scope_of_work": "Should not appear",
        },
        columns,
    )
    assert "Approved Manager" in html
    assert "Registered Office/Registered Agent Fee" in html
    assert "Should not appear" not in html


def test_au_service_columns_show_name_and_sow_not_description():
    columns = service_column_flags(
        {
            "service_columns": {
                "service_name": True,
                "description": False,
                "scope_of_work": True,
            }
        }
    )
    html = build_fee_service_cell_html(
        {
            "service_name": "Land Title Search",
            "description": "Registry description",
            "scope_of_work": "Search and report",
        },
        columns,
    )
    assert "Land Title Search" in html
    assert "Search and report" in html
    assert "Registry description" not in html


def test_bvi_fee_table_groups_by_department():
    draft = materialize_draft(template_id="harneys-bvi")
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "service_name": "Approved Manager",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
            {
                "sku": "AM022",
                "service_name": "Approved Manager",
                "description": "AML Officer: Provision of MLRO to BVI Approved Manager",
                "department_team": "Compliance Solutions",
                "pricing_type": "FIXED",
                "price_amount": 200.0,
                "price_currency": "USD",
                "billing_frequency": "ANNUALLY",
                "recurring": "RECURRING",
            },
            {
                "sku": "AM025",
                "service_name": "Approved Manager",
                "description": "AEOI Initial Setup\nBVI AEOI Portal Registration",
                "department_team": "AEOI Services",
                "pricing_type": "FIXED",
                "price_amount": 300.0,
                "price_currency": "USD",
                "billing_frequency": "ANNUALLY",
                "recurring": "RECURRING",
            },
        ],
    )
    preview = build_draft_preview(updated)
    markdown = preview["markdown"]
    assert "Approval Manager — Corporate Secretarial Services" in markdown
    assert "Approval Manager — Compliance Solutions" in markdown
    assert "Approval Manager — AEOI Services" in markdown
    assert "Formation fee" in markdown
    assert "AML Officer: Provision of MLRO to BVI Approved Manager" in markdown
    assert "AM001" not in markdown


def test_stale_draft_fee_layout_does_not_override_template():
    draft = materialize_draft(template_id="harneys-bvi")
    fee_section = next(
        section for section in draft["document"]["sections"] if section.get("kind") == "fee_section"
    )
    fee_section["fee_layout"] = {
        "table_style": "simple",
        "service_columns": {
            "service_name": True,
            "description": False,
            "scope_of_work": False,
        },
    }
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "service_name": "Approved Manager",
                "description": "Formation fee",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    preview = build_draft_preview(updated)
    markdown = preview["markdown"]
    assert "Formation fee" in markdown
    assert "<strong>Approved Manager</strong>" not in markdown


def test_bvi_template_column_widths_apply_to_grouped_tables():
    draft = materialize_draft(template_id="harneys-bvi")
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
            {
                "sku": "AM022",
                "description": "AML Officer: Provision of MLRO",
                "department_team": "Compliance Solutions",
                "pricing_type": "FIXED",
                "price_amount": 200.0,
                "price_currency": "USD",
                "billing_frequency": "ANNUALLY",
                "recurring": "RECURRING",
            },
        ],
    )
    markdown = build_draft_preview(updated)["markdown"]
    assert markdown.count('width="70%"') >= 2
    assert markdown.count('width="30%"') >= 2
