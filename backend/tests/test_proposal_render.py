from unittest.mock import patch

from app.proposal.context import init_run_proposal_state, reset_run_proposal_state
from app.proposal.pipeline import run_pipeline
from app.proposal.render import render_proposal_markdown
from app.proposal.state import apply_json_patch, empty_proposal_state
from app.tools.proposal import generate_document, render_preview
from tests.proposal_patch_helpers import jp, replace


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
    }
]


def _ready_state() -> dict:
    state = apply_json_patch(
        empty_proposal_state(),
        jp(
            replace("/proposal_meta/category_id", "harneys-bvi"),
            replace("/selection/selected_skus", ["BVI-incorporation-001"]),
            replace("/client/company_name", "Demo Ltd"),
        ),
    )
    with patch("app.proposal.pipeline.expand_selected_skus", return_value=["BVI-incorporation-001"]):
        with patch("app.proposal.pipeline.fetch_services_by_skus", return_value=SAMPLE_SERVICES):
            run_pipeline(state)
    return state


def test_render_proposal_markdown_replaces_placeholders():
    state = _ready_state()
    markdown = render_proposal_markdown(state)
    assert "Demo Ltd" in markdown
    assert "Registered agent fee" in markdown
    assert "Certified passport" in markdown or "Required documents" in markdown
    assert "{{solution_and_price}}" not in markdown


def test_render_preview_returns_live_summary():
    reset_run_proposal_state()
    ctx_state = _ready_state()
    init_run_proposal_state(initial_state=ctx_state, rehydrate=False)

    with patch("app.tools.proposal.rehydrate_proposal_state", return_value=False):
        with patch("app.tools.proposal.build_live_preview") as build_preview:
            build_preview.return_value = {
                "status": "ok",
                "title": "Demo Ltd",
                "state_fingerprint": "abc123",
                "completeness": {
                    "missing_required": [],
                    "ready_to_preview": True,
                    "ready_to_generate": False,
                },
            }
            result = render_preview()
    assert result["status"] == "ok"
    assert "Live proposal panel" in result["message"]
    assert result["state_fingerprint"] == "abc123"

    reset_run_proposal_state()


def test_generate_document_blocked_when_incomplete():
    reset_run_proposal_state()
    init_run_proposal_state()
    result = generate_document()
    assert result["status"] == "blocked"
    reset_run_proposal_state()
