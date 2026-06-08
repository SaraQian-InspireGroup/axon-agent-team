from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.chat_run import _StreamTurnAccumulator


def _content(type_: str, **kwargs):
    return SimpleNamespace(type=type_, **kwargs)


def _update(*contents):
    return SimpleNamespace(contents=list(contents))


@pytest.mark.asyncio
async def test_accumulator_persist_tool_rows_keeps_arguments():
    acc = _StreamTurnAccumulator()
    acc.observe(
        _update(
            _content(
                "function_call",
                call_id="c1",
                name="mysql_execute_query",
                arguments={},
            )
        )
    )
    acc.observe(
        _update(
            _content(
                "function_call",
                call_id="c1",
                name="mysql_execute_query",
                arguments={"sql": "SELECT 1"},
            )
        )
    )
    acc.observe(
        _update(
            _content(
                "function_result",
                call_id="c1",
                result={"rows": [], "row_count": 0},
            )
        )
    )

    assert acc.has_tool_rows()

    class FakeRepo:
        def __init__(self) -> None:
            self.rows: list[dict] = []

        async def insert(self, **kwargs):
            self.rows.append(kwargs)

    repo = FakeRepo()
    saved = await acc.persist_tool_rows(repo, uuid4())
    assert saved == 2
    call_row = next(r for r in repo.rows if r["message_type"] == "tool_call")
    assert call_row["metadata"]["arguments"] == {"sql": "SELECT 1"}
