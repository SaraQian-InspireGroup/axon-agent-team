from unittest.mock import patch

from app.proposal.context import init_run_proposal_state, reset_run_proposal_state
from app.proposal.pipeline import run_pipeline
from app.proposal.state import apply_patch, empty_proposal_state
from app.tools.proposal import get_proposal_state, list_categories, patch_proposal_state


SAMPLE_SERVICES = [
    {
        "sku": "BVI-incorporation-001",
        "category_id": "harneys-bvi",
        "region": "BVI",
        "bu": "Harneys",
        "department_team": "Corporate Services",
        "service_group": "incorporation",
        "service_group_display": "Incorporation",
        "product_name": "Registered agent",
        "service_name_on_proposal": "Registered agent fee",
        "description": "Agent",
        "scope_of_work": None,
        "service_type": "BASE_MANDATORY",
        "billing_frequency": "ONE_TIME",
        "recurring": "ONE_OFF",
        "pricing_type": "FIXED",
        "price_currency": "USD",
        "price_amount": 500.0,
        "price_min": None,
        "price_max": None,
        "price_spec": {},
        "fee_raw": None,
        "footnotes": None,
    },
    {
        "sku": "BVI-incorporation-002",
        "category_id": "harneys-bvi",
        "region": "BVI",
        "bu": "Harneys",
        "department_team": "Corporate Services",
        "service_group": "incorporation",
        "service_group_display": "Incorporation",
        "product_name": "Government fee",
        "service_name_on_proposal": "Government fee",
        "description": "Gov",
        "scope_of_work": None,
        "service_type": "BASE_MANDATORY",
        "billing_frequency": "ONE_TIME",
        "recurring": "ONE_OFF",
        "pricing_type": "TIERED",
        "price_currency": "USD",
        "price_amount": None,
        "price_min": None,
        "price_max": None,
        "price_spec": {"dimension": "share_count", "tier_label": "le_50000", "amount": 350},
        "fee_raw": None,
        "footnotes": None,
    },
]


def test_pipeline_resolves_required_docs_and_pricing():
    state = empty_proposal_state()
    state = apply_patch(state, {"op": "set_category", "category_id": "harneys-bvi"})
    state = apply_patch(
        state,
        {
            "op": "select_packages",
            "package_ids": [],
            "selected_skus": ["BVI-incorporation-001", "BVI-incorporation-002"],
        },
    )
    state = apply_patch(state, {"op": "set_pricing_facts", "pricing_facts": {"share_count": 1}})
    state = apply_patch(state, {"op": "set_client", "client": {"company_name": "Demo Ltd"}})

    with patch("app.proposal.pipeline.expand_selected_skus", return_value=[s["sku"] for s in SAMPLE_SERVICES]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=SAMPLE_SERVICES):
            run_pipeline(state)

    assert state["pricing"]["computed"]["BVI-incorporation-001"]["amount"] == 500.0
    assert state["pricing"]["computed"]["BVI-incorporation-002"]["amount"] == 350.0
    assert state["peripheral"]["required_docs"]
    assert state["resolved_placeholders"]["knowledge.required_docs"]["filled"] is True
    assert state["completeness"]["ready_to_preview"] is True


def test_proposal_tools_with_context():
    reset_run_proposal_state()
    init_run_proposal_state()
    cats = list_categories()
    assert cats["categories"]

    with patch("app.proposal.pipeline.expand_selected_skus", return_value=["BVI-incorporation-001"]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=[SAMPLE_SERVICES[0]]):
            result = patch_proposal_state(
                {
                    "op": "set_category",
                    "category_id": "harneys-bvi",
                }
            )
            assert result["proposal_meta"]["category_id"] == "harneys-bvi"

            result = patch_proposal_state(
                {
                    "op": "set_client",
                    "client": {"company_name": "Demo Ltd"},
                }
            )
            assert result["client"]["company_name"] == "Demo Ltd"

            view = get_proposal_state()
            assert "completeness" in view

    reset_run_proposal_state()
