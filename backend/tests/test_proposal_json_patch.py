from app.proposal.schema import (
    PatchValidationError,
    apply_json_patch,
    empty_proposal_state,
    validate_state,
)
from tests.proposal_patch_helpers import add, jp, remove, replace


def test_empty_state_validates():
    assert validate_state(empty_proposal_state()) == []


def test_replace_category_and_client():
    state = apply_json_patch(
        empty_proposal_state(),
        jp(
            replace("/proposal_meta/category_id", "harneys-bvi"),
            replace("/client/company_name", "Acme"),
        ),
    )
    assert state["proposal_meta"]["category_id"] == "harneys-bvi"
    assert state["client"]["company_name"] == "Acme"


def test_add_and_remove_skus():
    state = apply_json_patch(
        empty_proposal_state(),
        jp(add("/selection/selected_skus/-", "SKU-A"), add("/selection/selected_skus/-", "SKU-B")),
    )
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-B"]

    state = apply_json_patch(state, jp(add("/selection/selected_skus/-", "SKU-C")))
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-B", "SKU-C"]

    state = apply_json_patch(state, jp(remove("/selection/selected_skus/1")))
    assert state["selection"]["selected_skus"] == ["SKU-A", "SKU-C"]


def test_readonly_line_items_rejected():
    try:
        apply_json_patch(empty_proposal_state(), jp(replace("/line_items/groups", [])))
    except PatchValidationError as exc:
        assert exc.errors[0]["path"] == "/line_items/groups"
        assert "read-only" in exc.errors[0]["message"].lower()
    else:
        raise AssertionError("expected PatchValidationError")


def test_readonly_pricing_computed_rejected():
    try:
        apply_json_patch(
            empty_proposal_state(),
            jp(replace("/pricing/computed/FOO", {"amount": 1})),
        )
    except PatchValidationError as exc:
        assert exc.errors[0]["path"] == "/pricing/computed/FOO"
    else:
        raise AssertionError("expected PatchValidationError")
