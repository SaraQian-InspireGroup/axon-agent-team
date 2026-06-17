from unittest.mock import patch

from app.proposal.pipeline import run_pipeline
from app.proposal.state import apply_patch, empty_proposal_state

LODGE = {
    "sku": "AU-LODG",
    "service_name_on_proposal": "Lodgement - Special Purpose Annual Financial Statements",
    "billing_frequency": "ANNUALLY",
    "recurring": "RECURRING",
    "pricing_type": "FIXED",
    "price_currency": "AUD",
    "price_amount": 4500.0,
    "price_spec": {},
}
XERO = {
    "sku": "AU-XERO",
    "service_name_on_proposal": "Setup of Xero",
    "billing_frequency": "ONE_TIME",
    "recurring": "ONE_OFF",
    "pricing_type": "FIXED",
    "price_currency": "AUD",
    "price_amount": 500.0,
    "price_spec": {},
}


def test_add_skus_keeps_existing_services_in_artifact_pipeline():
    """Simulates user adding Xero while Lodgement was already selected."""
    state = empty_proposal_state()
    state = apply_patch(state, {"op": "set_category", "category_id": "au-services"})
    state = apply_patch(state, {"op": "select_packages", "package_ids": [], "selected_skus": ["AU-LODG"]})

    # Wrong agent behavior (replace-only) drops Lodgement:
    wrong = apply_patch(state, {"op": "select_packages", "package_ids": [], "selected_skus": ["AU-XERO"]})
    assert wrong["selection"]["selected_skus"] == ["AU-XERO"]

    # Correct append keeps both:
    state = apply_patch(state, {"op": "add_skus", "skus": ["AU-XERO"]})
    assert state["selection"]["selected_skus"] == ["AU-LODG", "AU-XERO"]

    with patch("app.proposal.pipeline.expand_selected_skus", return_value=["AU-LODG", "AU-XERO"]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=[LODGE, XERO]):
            with patch("app.proposal.pipeline.fetch_packages_by_ids", return_value=[]):
                run_pipeline(state)

    rows = state["line_items"]["groups"][0]["rows"]
    assert len(rows) == 2
    assert {row["sku"] for row in rows} == {"AU-LODG", "AU-XERO"}
