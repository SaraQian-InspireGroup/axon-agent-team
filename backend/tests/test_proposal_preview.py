from unittest.mock import patch

from app.proposal.preview import build_live_preview, proposal_state_fingerprint
from app.proposal.state import apply_patch, empty_proposal_state

SAMPLE_SERVICES = [
    {
        "sku": "BVI-incorporation-001",
        "service_name_on_proposal": "Registered agent fee",
        "billing_frequency": "ONE_TIME",
        "recurring": "ONE_OFF",
        "pricing_type": "FIXED",
        "price_currency": "USD",
        "price_amount": 500.0,
        "price_spec": {},
    }
]


def _ready_state():
    state = empty_proposal_state()
    state = apply_patch(state, {"op": "set_category", "category_id": "harneys-bvi"})
    state = apply_patch(
        state,
        {"op": "select_packages", "package_ids": [], "selected_skus": ["BVI-incorporation-001"]},
    )
    state = apply_patch(state, {"op": "set_client", "client": {"company_name": "Demo Ltd"}})
    return state


def test_fingerprint_changes_when_selection_changes():
    state = _ready_state()
    fp1 = proposal_state_fingerprint(state)
    state = apply_patch(state, {"op": "add_skus", "skus": ["SKU-NEW"]})
    fp2 = proposal_state_fingerprint(state)
    assert fp1 != fp2


def test_build_live_preview_empty_state():
    preview = build_live_preview(empty_proposal_state())
    assert preview["status"] == "empty"
    assert preview["markdown"] == ""


def test_build_live_preview_renders_markdown():
    state = _ready_state()
    with patch("app.proposal.pipeline.expand_selected_skus", return_value=["BVI-incorporation-001"]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=SAMPLE_SERVICES):
            with patch("app.proposal.pipeline.fetch_packages_by_ids", return_value=[]):
                preview = build_live_preview(state, draft=True)
    assert preview["status"] == "ok"
    assert "Demo Ltd" in preview["markdown"]
    assert preview["state_fingerprint"]
