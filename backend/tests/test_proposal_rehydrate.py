from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.platform.session_store import SessionStore
from app.proposal.context import init_run_proposal_state, reset_run_proposal_state
from app.proposal.rehydrate import rehydrate_proposal_state, should_rehydrate_proposal_state
from app.proposal.state import empty_proposal_state


def test_should_rehydrate_when_selection_present():
    state = empty_proposal_state()
    state["proposal_meta"]["category_id"] = "au-services"
    state["selection"]["selected_skus"] = ["SKU-1"]
    assert should_rehydrate_proposal_state(state) is True


def test_rehydrate_runs_pipeline():
    state = empty_proposal_state()
    state["proposal_meta"]["category_id"] = "au-services"
    state["selection"]["selected_skus"] = ["SKU-1"]
    with patch("app.proposal.rehydrate.run_pipeline") as run_pipeline:
        assert rehydrate_proposal_state(state) is True
        run_pipeline.assert_called_once_with(state)


@pytest.mark.asyncio
async def test_session_store_merges_proposal_state_from_db_when_redis_missing_it():
    chat_id = __import__("uuid").uuid4()
    db = AsyncMock()
    store = SessionStore(db)
    db_payload = {
        "session": {"session_id": str(chat_id)},
        "proposal_state": {"selection": {"selected_skus": ["A"]}},
    }
    redis_payload = {"session": {"session_id": str(chat_id)}, "working_set": {"rows": []}}

    with patch.object(store, "_load_payload_from_db", return_value=db_payload):
        with patch.object(store, "_get_from_redis", return_value=redis_payload):
            merged = await store._load_payload(chat_id)

    assert merged["proposal_state"]["selection"]["selected_skus"] == ["A"]
    assert merged["working_set"]["rows"] == []


def test_init_rehydrates_persisted_state():
    reset_run_proposal_state()
    state = empty_proposal_state()
    state["proposal_meta"]["category_id"] = "harneys-bvi"
    state["selection"]["selected_packages"] = ["PKG-BVI-INCORP-STD"]

    with patch("app.proposal.rehydrate.rehydrate_proposal_state", return_value=True) as rehydrate:
        ctx = init_run_proposal_state(initial_state=state)
        rehydrate.assert_called_once()
        assert ctx.dirty is True

    reset_run_proposal_state()
