import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.db.repositories.messages import MessageRepository
from app.proposal.recover import (
    extract_patch_result_from_row,
    proposal_state_from_tool_result,
    recover_proposal_state_from_messages,
)
from app.proposal.state import empty_proposal_state
from app.proposal.store import load_proposal_state_from_payload


def test_load_proposal_state_ignores_empty_dict():
    assert load_proposal_state_from_payload({"proposal_state": {}}) is None


def test_load_proposal_state_ignores_intake_shell_without_scope():
    shell = empty_proposal_state()
    assert load_proposal_state_from_payload({"proposal_state": shell}) is None


def test_proposal_state_from_tool_result_accepts_patched_payload():
    payload = {
        "patched": True,
        "status": "ok",
        "proposal_meta": {"category_id": "au-services", "stage": "REVIEW"},
        "selection": {"selected_skus": ["CSS23"]},
        "client": {"company_name": "Acme"},
    }
    state = proposal_state_from_tool_result(payload)
    assert state is not None
    assert state["selection"]["selected_skus"] == ["CSS23"]
    assert state["client"]["company_name"] == "Acme"


def test_extract_patch_result_prefers_content():
    row = SimpleNamespace(
        message_type="tool_result",
        content=json.dumps(
            {
                "patched": True,
                "proposal_meta": {"category_id": "au-services"},
                "selection": {"selected_skus": ["A"]},
            }
        ),
        message_metadata={"tool_name": "patch_proposal_state"},
    )
    state = extract_patch_result_from_row(row)
    assert state is not None
    assert state["selection"]["selected_skus"] == ["A"]


def test_extract_patch_result_falls_back_to_metadata_result():
    row = SimpleNamespace(
        message_type="tool_result",
        content=None,
        message_metadata={
            "tool_name": "patch_proposal_state",
            "result": json.dumps(
                {
                    "patched": True,
                    "proposal_meta": {"category_id": "au-services"},
                    "selection": {"selected_skus": ["B"]},
                }
            ),
        },
    )
    state = extract_patch_result_from_row(row)
    assert state is not None
    assert state["selection"]["selected_skus"] == ["B"]


@pytest.mark.asyncio
async def test_recover_proposal_state_from_messages_returns_latest():
    chat_id = uuid.uuid4()
    repo = AsyncMock(spec=MessageRepository)
    older = SimpleNamespace(
        message_type="tool_result",
        content=json.dumps(
            {
                "patched": True,
                "proposal_meta": {"category_id": "au-services"},
                "selection": {"selected_skus": ["OLD"]},
            }
        ),
        message_metadata={"tool_name": "patch_proposal_state"},
    )
    newer = SimpleNamespace(
        message_type="tool_result",
        content=json.dumps(
            {
                "patched": True,
                "proposal_meta": {"category_id": "au-services"},
                "selection": {"selected_skus": ["NEW"]},
            }
        ),
        message_metadata={"tool_name": "patch_proposal_state"},
    )
    repo.list_by_chat.return_value = [older, newer]

    state = await recover_proposal_state_from_messages(repo, chat_id)
    assert state is not None
    assert state["selection"]["selected_skus"] == ["NEW"]
