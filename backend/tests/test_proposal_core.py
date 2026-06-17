from app.proposal.loaders import get_category, load_categories, load_template_yaml
from app.proposal.pricing import compute_pricing
from app.proposal.state import apply_patch, empty_proposal_state


def test_load_categories():
    categories = load_categories()
    ids = {row["category_id"] for row in categories}
    assert "harneys-bvi" in ids
    assert "au-services" in ids


def test_category_default_template():
    cat = get_category("harneys-bvi")
    assert cat is not None
    assert cat["default_template_id"] == "harneys-bvi"


def test_harneys_template_has_solution_and_price():
    tpl = load_template_yaml("harneys-bvi")
    placeholders = tpl.get("placeholders") or {}
    assert "solution_and_price" in placeholders
    assert placeholders["solution_and_price"]["fee_layout"]["group_by"] == "service_group"


def test_au_template_fee_layout():
    tpl = load_template_yaml("au-advisory")
    sap = (tpl.get("placeholders") or {}).get("solution_and_price") or {}
    layout = sap.get("fee_layout") or {}
    assert layout.get("group_by") == "package"
    assert layout.get("table_style") == "frequency_columns"
    assert tpl.get("document_title", {}).get("prefix") == "INCORP ADVISORY PROPOSAL"


def test_compute_fixed_pricing():
    services = [
        {
            "sku": "TEST-FIXED",
            "pricing_type": "FIXED",
            "price_currency": "USD",
            "price_amount": 100.0,
            "price_spec": {},
            "recurring": "ONE_OFF",
            "billing_frequency": "ONE_TIME",
            "service_name_on_proposal": "Test service",
        }
    ]
    computed, explanations, recurring = compute_pricing(services, {})
    assert computed["TEST-FIXED"]["amount"] == 100.0
    assert explanations["TEST-FIXED"]
    assert recurring == []


def test_compute_tiered_requires_share_count():
    services = [
        {
            "sku": "BVI-GOV",
            "pricing_type": "TIERED",
            "price_currency": "USD",
            "price_amount": None,
            "price_spec": {"dimension": "share_count", "tier_label": "le_50000", "amount": 350},
            "recurring": "ONE_OFF",
            "billing_frequency": "ONE_TIME",
            "service_name_on_proposal": "Gov fee",
        }
    ]
    computed, _, _ = compute_pricing(services, {})
    assert computed["BVI-GOV"]["status"] == "missing_facts"

    computed, _, _ = compute_pricing(services, {"share_count": 1})
    assert computed["BVI-GOV"]["status"] == "computed"
    assert computed["BVI-GOV"]["amount"] == 350


def test_apply_patch_semantic_ops():
    state = empty_proposal_state()
    state = apply_patch(state, {"op": "set_category", "category_id": "harneys-bvi"})
    assert state["proposal_meta"]["category_id"] == "harneys-bvi"

    state = apply_patch(
        state,
        {"op": "set_client", "client": {"company_name": "Acme"}},
    )
    assert state["client"]["company_name"] == "Acme"

    state = apply_patch(
        state,
        {"op": "select_packages", "package_ids": ["PKG-BVI-INCORP-STD"]},
    )
    assert state["selection"]["selected_packages"] == ["PKG-BVI-INCORP-STD"]

    state = apply_patch(state, {"op": "add_skus", "skus": ["SKU-A", "SKU-B"]})
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-B"]

    state = apply_patch(state, {"op": "add_skus", "skus": ["SKU-B", "SKU-C"]})
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-B", "SKU-C"]

    state = apply_patch(state, {"op": "remove_skus", "skus": ["SKU-B"]})
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-C"]
