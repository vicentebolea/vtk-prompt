"""The first prompt of a conversation must reach the LLM with its system prompt and context."""

import asyncio
import json
import types
from unittest.mock import MagicMock, patch

import pytest

from vtk_prompt.client import VTKPromptClient
from vtk_prompt.controllers import conversation, generation, sessions


def _reply(**kw):
    msg = types.SimpleNamespace(content="<explanation>e</explanation><code>x = 1</code>")
    msg.tool_calls = None
    choice = types.SimpleNamespace(finish_reason="stop", message=msg)
    usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1)
    return types.SimpleNamespace(choices=[choice], usage=usage)


def _app(client, conversation_so_far):
    state = types.SimpleNamespace(
        query_text="make a sphere",
        conversation=conversation_so_far,
        error_message="",
        is_loading=False,
        current_session_id="s1",
        max_tokens=100,
        temperature=0.5,
        top_k=5,
        retry_attempts=1,
        log_tool_calls=False,
        agentic_retrieval=False,
        provider="anthropic",
        dsl_translation=False,
        generated_code="",
        generated_explanation="",
        input_tokens=0,
        output_tokens=0,
        flush=lambda: None,
    )
    return types.SimpleNamespace(
        state=state,
        prompt_client=client,
        custom_prompt_data=None,
        _conversation_loading=False,
        debug=False,
        _init_prompt_client=lambda: None,
        _get_api_key=lambda: "k",
        _get_model=lambda: "claude-sonnet-5",
        _get_base_url=lambda: "http://api",
    )


@pytest.fixture(autouse=True)
def _ui_side_effects(monkeypatch):
    """Only the conversation sent to the LLM matters here, not rendering or bookkeeping."""
    monkeypatch.setattr(generation, "execute_with_renderer", lambda app, code: (True, None))
    monkeypatch.setattr(generation, "push_code_snapshot", lambda *a, **k: None)
    for name in ("sync_editor_code_into_conversation", "build_conversation_navigation"):
        monkeypatch.setattr(conversation, name, lambda *a, **k: None)
    monkeypatch.setattr(conversation, "record_turn_checkpoint", lambda *a, **k: None)
    for name in ("touch_current_session", "refresh_sessions_list"):
        monkeypatch.setattr(sessions, name, lambda *a, **k: None)


def _sent_messages(conversation_so_far):
    mcp = MagicMock()
    mcp.get_enriched_context.return_value = "CONTEXT-FROM-MCP"
    mcp.list_tools.return_value = []
    mcp.validate_code.return_value = ""
    sent: list = []

    def create(**kw):
        sent.extend(json.loads(json.dumps(kw["messages"])))
        return _reply()

    with (
        patch("vtk_prompt.client.openai.OpenAI") as openai,
        patch("vtk_prompt.vtk_mcp_client.check_mcp_available", return_value=True),
        patch("vtk_prompt.vtk_mcp_client.VTKMCPClient", return_value=mcp),
    ):
        openai.return_value.chat.completions.create.side_effect = create
        app = _app(VTKPromptClient(mcp_url="http://mcp"), conversation_so_far)
        asyncio.run(generation.generate_and_execute_code(app, "s1"))
    assert app.state.error_message == ""
    return sent, app


def test_first_prompt_carries_system_prompt_and_context():
    sent, _ = _sent_messages([])
    assert sent[0]["role"] == "system"
    assert any("CONTEXT-FROM-MCP" in str(m["content"]) for m in sent)


def test_follow_up_keeps_history_and_appends_the_new_turn():
    history = [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "<code>y = 2</code>"},
    ]
    sent, app = _sent_messages(list(history))
    assert sent[:3] == history
    assert [m["role"] for m in sent[3:]] == ["user"] and "sphere" in sent[3]["content"]
    assert app.state.conversation[:3] == history


def test_conversation_records_the_prompt_once():
    _, app = _sent_messages([])
    users = [m for m in app.state.conversation if m["role"] == "user"]
    assert len(users) == 1
