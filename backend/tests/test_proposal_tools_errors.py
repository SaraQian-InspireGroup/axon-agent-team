from unittest.mock import patch

from app.proposal.context import init_run_proposal_state, reset_run_proposal_state
from app.tools import proposal as proposal_tools


def test_patch_returns_error_dict_instead_of_raising():
    reset_run_proposal_state()
    init_run_proposal_state()
    with patch.object(proposal_tools, "run_pipeline", side_effect=RuntimeError("boom")):
        result = proposal_tools.patch_proposal_state(
            [{"op": "replace", "path": "/proposal_meta/category_id", "value": "au-services"}]
        )
        assert result["status"] == "error"
        assert result["error"] == "boom"
    reset_run_proposal_state()


def test_patch_readonly_returns_422():
    reset_run_proposal_state()
    init_run_proposal_state()
    result = proposal_tools.patch_proposal_state(
        [{"op": "replace", "path": "/line_items/groups", "value": []}]
    )
    assert result["status"] == "error"
    assert result["http_status"] == 422
    assert result["errors"]
    reset_run_proposal_state()
