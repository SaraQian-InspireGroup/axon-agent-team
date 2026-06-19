from app.proposal.loaders import load_template_yaml, load_templates
from app.proposal.pricing import compute_pricing


def test_load_templates():
    templates = load_templates()
    ids = {row["template_id"] for row in templates}
    assert "harneys-bvi" in ids
    assert "au-advisory" in ids


def test_template_declares_catalog_filter():
    tpl = load_template_yaml("harneys-bvi")
    assert tpl["catalog_filter"] == {"region": "BVI", "bu": "Harneys"}


def test_harneys_template_has_solution_and_price():
    tpl = load_template_yaml("harneys-bvi")
    sections = {section["id"]: section for section in tpl.get("sections") or []}
    assert "solution_and_fees" in sections
    assert sections["solution_and_fees"]["kind"] == "fee_section"
    assert sections["solution_and_fees"]["fee_layout"]["group_by"] == "service_group"


def test_au_template_fee_layout():
    tpl = load_template_yaml("au-advisory")
    sections = {section["id"]: section for section in tpl.get("sections") or []}
    layout = sections["solution_and_fees"]["fee_layout"]
    assert layout.get("group_by") == "package"
    assert layout.get("table_style") == "frequency_columns"
    assert "body" not in tpl
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
