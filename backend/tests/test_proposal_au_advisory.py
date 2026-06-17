from unittest.mock import patch

from app.proposal.fee_table import render_frequency_table, row_frequency_columns
from app.proposal.loaders import resolve_document_title
from app.proposal.pipeline import materialize_line_items, run_pipeline
from app.proposal.render import render_proposal_markdown
from app.proposal.state import apply_patch, empty_proposal_state
from app.proposal.storage import build_filename


AU_PACKAGE = {
    "package_id": "PKG-AU-STRUCT",
    "package_name": "Initial Structuring & Corporate Compliance Services",
    "linked_skus": ["AU-INCORP", "AU-FYE", "AU-DIRECTOR"],
}

AU_SERVICES = [
    {
        "sku": "AU-INCORP",
        "category_id": "au-services",
        "product_name": "Company incorporation",
        "service_name_on_proposal": "Assistance with company incorporation, including ASIC registration",
        "scope_of_work": "ASIC registration, TFN/GST/PAYG applications.",
        "billing_frequency": "ONE_TIME",
        "recurring": "ONE_OFF",
        "pricing_type": "FIXED",
        "price_currency": "AUD",
        "price_amount": 2500.0,
        "price_spec": {},
    },
    {
        "sku": "AU-FYE",
        "category_id": "au-services",
        "product_name": "Fiscal year-end sync",
        "service_name_on_proposal": "Application to synchronise fiscal year-end",
        "scope_of_work": None,
        "billing_frequency": "ONE_TIME",
        "recurring": "ONE_OFF",
        "pricing_type": "FIXED",
        "price_currency": "AUD",
        "price_amount": 750.0,
        "price_spec": {},
    },
    {
        "sku": "AU-DIRECTOR",
        "category_id": "au-services",
        "product_name": "Resident director",
        "service_name_on_proposal": "Resident Director appointment",
        "scope_of_work": None,
        "billing_frequency": "ANNUALLY",
        "recurring": "RECURRING",
        "pricing_type": "FIXED",
        "price_currency": "AUD",
        "price_amount": 7500.0,
        "price_spec": {},
    },
    {
        "sku": "AU-TAX",
        "category_id": "au-services",
        "product_name": "Tax compliance",
        "service_name_on_proposal": "Tax Compliance Services",
        "scope_of_work": None,
        "billing_frequency": "QUARTERLY",
        "recurring": "RECURRING",
        "pricing_type": "FIXED",
        "price_currency": "AUD",
        "price_amount": 500.0,
        "price_spec": {},
    },
]


def _au_state(*, payment_options: bool = False) -> dict:
    state = empty_proposal_state()
    state = apply_patch(state, {"op": "set_category", "category_id": "au-services"})
    state = apply_patch(
        state,
        {
            "op": "select_packages",
            "package_ids": ["PKG-AU-STRUCT"],
            "selected_skus": ["AU-TAX"],
        },
    )
    state = apply_patch(
        state,
        {"op": "set_client", "client": {"company_name": "Acme Holdings Pty Ltd"}},
    )
    if payment_options:
        state = apply_patch(state, {"op": "enable_sections", "section_ids": ["payment_options"]})
    return state


def test_au_document_title_and_filename():
    state = _au_state()
    title = resolve_document_title(state, "au-advisory")
    assert title == "INCORP ADVISORY PROPOSAL - Acme Holdings Pty Ltd"
    assert build_filename(state, template_id="au-advisory") == f"{title}.md"


def test_au_package_grouping_and_frequency_columns():
    state = _au_state()
    computed = {
        "AU-INCORP": {"status": "computed", "amount": 2500.0, "currency": "AUD"},
        "AU-FYE": {"status": "computed", "amount": 750.0, "currency": "AUD"},
        "AU-DIRECTOR": {"status": "computed", "amount": 7500.0, "currency": "AUD"},
        "AU-TAX": {"status": "computed", "amount": 500.0, "currency": "AUD"},
    }
    with patch("app.proposal.pipeline.fetch_packages_by_ids", return_value=[AU_PACKAGE]):
        line_items = materialize_line_items(
            AU_SERVICES,
            computed,
            "au-advisory",
            state=state,
            category_id="au-services",
        )

    assert len(line_items["groups"]) == 1
    assert line_items["groups"][0]["display_name"] == AU_PACKAGE["package_name"]
    assert len(line_items["groups"][0]["rows"]) == 4

    cols = row_frequency_columns(line_items["groups"][0]["rows"][0])
    assert cols["once_off"] == 2500.0

    table = render_frequency_table(line_items["groups"], currency="AUD")
    assert "Once-Off" in table
    assert "Assistance with company incorporation" in table


def test_au_payment_options_derived_from_tables():
    state = _au_state(payment_options=True)
    with patch("app.proposal.pipeline.expand_selected_skus", return_value=[s["sku"] for s in AU_SERVICES]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=AU_SERVICES):
            with patch("app.proposal.pipeline.fetch_packages_by_ids", return_value=[AU_PACKAGE]):
                run_pipeline(state)

    resolved = state["payment_options"]["resolved"]
    assert len(resolved) == 1
    assert resolved[0]["label"] == "Payment Option A"
    assert len(resolved[0]["rows"]) == 1
    structuring = resolved[0]["rows"][0]
    assert structuring["once_off"] == 3250.0
    assert structuring["annual"] == 7500.0
    assert structuring["quarterly"] == 500.0
    assert structuring["total_annualized"] == 12750.0


def test_au_render_includes_fee_description_and_payment_section():
    state = _au_state(payment_options=True)
    with patch("app.proposal.pipeline.expand_selected_skus", return_value=[s["sku"] for s in AU_SERVICES]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=AU_SERVICES):
            with patch("app.proposal.pipeline.fetch_packages_by_ids", return_value=[AU_PACKAGE]):
                run_pipeline(state)

    markdown = render_proposal_markdown(state)
    assert markdown.startswith("# INCORP ADVISORY PROPOSAL - Acme Holdings Pty Ltd")
    assert "About Incorp Advisory" in markdown
    assert "2.5% disbursement charge" in markdown
    assert "Payment Option A" in markdown
    assert "## Fee summary" in markdown
