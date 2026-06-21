from app.proposal.draft import patch_draft
from app.proposal.fee_row import (
    build_mdm_source,
    effective_pricing,
    materialize_mdm_fee_row,
    parse_amount_display,
    remove_fee_rows_by_sku,
    resolve_fee_row,
    validate_fee_row_patches,
)
from app.proposal.draft import DraftPatchError, materialize_draft, _effective_fee_layout
from tests.proposal_fee_fixtures import make_mdm_fee_row


def _au_layout() -> dict:
    draft = materialize_draft(template_id="au-advisory")
    fee = next(section for section in draft["document"]["sections"] if section.get("kind") == "fee_section")
    return _effective_fee_layout(draft, fee)


def _bvi_layout() -> dict:
    draft = materialize_draft(template_id="harneys-bvi")
    fee = next(section for section in draft["document"]["sections"] if section.get("kind") == "fee_section")
    return _effective_fee_layout(draft, fee)


def test_resolve_au_frequency_display():
    source = build_mdm_source(
        {
            "sku": "TA01",
            "service_name": "Application",
            "scope_of_work": "SOW text",
            "price_amount": 600.0,
            "price_currency": "AUD",
            "billing_frequency": "ONE_TIME",
            "pricing_type": "FIXED",
        }
    )
    display = resolve_fee_row(source, layout=_au_layout())
    assert display["preview_primary"] == "Application"
    assert display["scope_of_work_display"] == "SOW text"
    assert display["frequency_columns_display"]["once_off"] == "AUD $600.00"
    assert display["total_display"] == "AUD $600.00"


def test_resolve_bvi_simple_display_uses_description():
    source = build_mdm_source(
        {
            "sku": "AM001",
            "service_name": "Approved Manager",
            "description": "Formation fee",
            "price_amount": 100.0,
            "price_currency": "USD",
            "billing_frequency": "ONE_TIME",
            "pricing_type": "FIXED",
        }
    )
    display = resolve_fee_row(source, layout=_bvi_layout())
    assert display["preview_primary"] == "Formation fee"
    assert display["amount_display"] == "USD $100.00"
    assert display["once_off_display"] == "USD $100.00"
    assert display["recurring_display"] == ""
    assert "scope_of_work_display" not in display


def test_resolve_recurring_once_off_recurring_canonical():
    source = build_mdm_source(
        {
            "sku": "SG01",
            "service_name": "Annual compliance",
            "scope_of_work": "Monthly filings",
            "price_amount": 800.0,
            "price_currency": "USD",
            "billing_frequency": "ANNUALLY",
            "pricing_type": "FIXED",
        }
    )
    layout = {
        "table_style": "one_off_recurring",
        "service_columns": {
            "service_name": True,
            "description": False,
            "scope_of_work": True,
        },
    }
    display = resolve_fee_row(source, layout=layout)
    assert display["preview_primary"] == "Annual compliance"
    assert display["scope_of_work_display"] == "Monthly filings"
    assert display["once_off_display"] == ""
    assert display["recurring_display"] == "USD $800.00 Annual"


def test_render_one_off_recurring_table():
    from app.proposal.fee_table import render_one_off_recurring_table

    groups = [
        {
            "group_id": "g1",
            "display_name": "Services",
            "rows": [
                {
                    "display": {
                        "preview_primary": "Setup",
                        "scope_of_work_display": "Initial work",
                        "once_off_display": "USD $500.00",
                        "recurring_display": "",
                    },
                },
                {
                    "display": {
                        "preview_primary": "Retainer",
                        "once_off_display": "",
                        "recurring_display": "USD $800.00 Annual",
                    },
                },
            ],
        }
    ]
    html = render_one_off_recurring_table(groups)
    assert "proposal-fee-table-one-off-recurring" in html
    assert "USD $500.00" in html
    assert "USD $800.00 Annual" in html
    assert "Initial work" in html


def test_patch_amount_display_updates_effective_pricing():
    row = make_mdm_fee_row({**{"sku": "TA01", "service_name": "App", "price_amount": 500.0, "price_currency": "AUD", "billing_frequency": "ONE_TIME", "pricing_type": "FIXED"}})
    draft = materialize_draft(template_id="au-advisory")
    fee = next(section for section in draft["document"]["sections"] if section.get("kind") == "fee_section")
    fee["tables"] = [{"id": "t1", "title": "T", "rows": [row]}]
    updated = patch_draft(
        draft,
        [{"op": "replace", "path": "/document/sections/1/tables/0/rows/0/display/frequency_columns_display/once_off", "value": "AUD $750.00"},
         {"op": "replace", "path": "/document/sections/1/tables/0/rows/0/display/total_display", "value": "AUD $750.00"}],
    )
    patched_row = updated["document"]["sections"][1]["tables"][0]["rows"][0]
    pricing = effective_pricing(patched_row)
    assert pricing["amount"] == 750.0


def test_validate_fee_row_patches_rejects_source_mutation():
    try:
        validate_fee_row_patches(
            [{"op": "replace", "path": "/document/sections/1/tables/0/rows/0/source/sku", "value": "X"}]
        )
        assert False, "expected DraftPatchError"
    except DraftPatchError as exc:
        assert "immutable" in exc.message


def test_remove_fee_rows_by_sku():
    draft = materialize_draft(template_id="au-advisory")
    fee = next(section for section in draft["document"]["sections"] if section.get("kind") == "fee_section")
    fee["tables"] = [
        {
            "id": "t1",
            "title": "T",
            "rows": [
                make_mdm_fee_row({"sku": "A", "service_name": "A", "price_amount": 1, "price_currency": "AUD", "billing_frequency": "ONE_TIME", "pricing_type": "FIXED"}),
                make_mdm_fee_row({"sku": "B", "service_name": "B", "price_amount": 2, "price_currency": "AUD", "billing_frequency": "ONE_TIME", "pricing_type": "FIXED"}),
            ],
        }
    ]
    updated = remove_fee_rows_by_sku(draft, ["A"])
    rows = updated["document"]["sections"][1]["tables"][0]["rows"]
    assert len(rows) == 1
    assert rows[0]["source"]["sku"] == "B"


def test_parse_amount_display():
    assert parse_amount_display("AUD $600.00") == 600.0
    assert parse_amount_display("400 per pension stream") == 400.0
