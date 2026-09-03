from pocket_desk_agent.ai_history import (
    gemini_history_to_openai,
    gemini_tools_to_openai,
    openai_message_to_gemini_parts,
)


def test_gemini_tools_to_openai_wraps_function_declarations() -> None:
    declarations = [
        {
            "name": "read_file",
            "description": "Read a file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        }
    ]

    tools = gemini_tools_to_openai(declarations)

    assert tools == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            },
        }
    ]


def test_gemini_tools_to_openai_defaults_missing_fields() -> None:
    tools = gemini_tools_to_openai([{"name": "ping"}])

    assert tools[0]["function"]["description"] == ""
    assert tools[0]["function"]["parameters"] == {"type": "object", "properties": {}}


def test_gemini_history_to_openai_converts_plain_turns() -> None:
    history = [
        {"role": "user", "parts": [{"text": "hello"}]},
        {"role": "model", "parts": [{"text": "hi there"}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="You are helpful.")

    assert messages == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_gemini_history_to_openai_pairs_single_tool_call() -> None:
    history = [
        {"role": "user", "parts": [{"text": "list files"}]},
        {"role": "model", "parts": [{"functionCall": {"name": "list_directory", "args": {"path": "."}}}]},
        {"role": "user", "parts": [{"functionResponse": {"name": "list_directory", "response": {"result": "a.txt", "success": True}}}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assert messages[1] == {"role": "user", "content": "list files"}
    assistant_msg = messages[2]
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["tool_calls"]) == 1
    call_id = assistant_msg["tool_calls"][0]["id"]
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "list_directory"
    import json
    assert json.loads(assistant_msg["tool_calls"][0]["function"]["arguments"]) == {"path": "."}

    tool_msg = messages[3]
    assert tool_msg == {
        "role": "tool",
        "tool_call_id": call_id,
        "content": tool_msg["content"],
    }
    assert json.loads(tool_msg["content"]) == {"result": "a.txt", "success": True}


def test_gemini_history_to_openai_pairs_multiple_tool_calls_in_order() -> None:
    history = [
        {"role": "user", "parts": [{"text": "do two things"}]},
        {
            "role": "model",
            "parts": [
                {"functionCall": {"name": "tool_a", "args": {}}},
                {"functionCall": {"name": "tool_b", "args": {}}},
            ],
        },
        {
            "role": "user",
            "parts": [
                {"functionResponse": {"name": "tool_a", "response": {"result": "A", "success": True}}},
                {"functionResponse": {"name": "tool_b", "response": {"result": "B", "success": True}}},
            ],
        },
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assistant_msg = messages[2]
    ids = [tc["id"] for tc in assistant_msg["tool_calls"]]
    assert len(set(ids)) == 2  # distinct ids

    tool_msgs = [m for m in messages if m["role"] == "tool"]
    assert len(tool_msgs) == 2
    assert tool_msgs[0]["tool_call_id"] == ids[0]
    assert tool_msgs[1]["tool_call_id"] == ids[1]


def test_openai_message_to_gemini_parts_text_only() -> None:
    parts = openai_message_to_gemini_parts({"role": "assistant", "content": "hello"})
    assert parts == [{"text": "hello"}]


def test_openai_message_to_gemini_parts_with_tool_calls() -> None:
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'},
            }
        ],
    }

    parts = openai_message_to_gemini_parts(message)

    assert parts == [{"functionCall": {"name": "read_file", "args": {"path": "a.txt"}}}]


def test_openai_message_to_gemini_parts_handles_malformed_arguments() -> None:
    message = {
        "content": None,
        "tool_calls": [{"function": {"name": "broken", "arguments": "not json"}}],
    }

    parts = openai_message_to_gemini_parts(message)

    assert parts == [{"functionCall": {"name": "broken", "args": {}}}]


def test_gemini_history_to_openai_drops_orphaned_tool_response() -> None:
    """A history slice starting mid tool-call-pair (e.g. after trimming)
    has a functionResponse with no preceding assistant tool_calls — it
    must be dropped, not emitted as an invalid lone 'tool' message."""
    history = [
        {"role": "user", "parts": [{"functionResponse": {"name": "list_directory", "response": {"result": "a.txt", "success": True}}}]},
        {"role": "model", "parts": [{"text": "Found a.txt"}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assert not any(m["role"] == "tool" for m in messages)
    assert messages == [
        {"role": "system", "content": "sys"},
        {"role": "assistant", "content": "Found a.txt"},
    ]


def test_gemini_history_to_openai_drops_dangling_tool_call() -> None:
    """A functionCall with no following functionResponse (e.g. left by an
    unhandled exception before history rollback) must not be emitted as
    an unanswerable assistant tool_calls message."""
    history = [
        {"role": "user", "parts": [{"text": "list files"}]},
        {"role": "model", "parts": [{"functionCall": {"name": "list_directory", "args": {}}}]},
        # no matching functionResponse entry follows — history ends here
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assert not any(m.get("tool_calls") for m in messages if m["role"] == "assistant")
    assert messages == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "list files"},
    ]


def test_gemini_history_to_openai_still_pairs_well_formed_history() -> None:
    """Regression guard: the fix must not break the normal, well-formed case."""
    history = [
        {"role": "user", "parts": [{"text": "list files"}]},
        {"role": "model", "parts": [{"functionCall": {"name": "list_directory", "args": {"path": "."}}}]},
        {"role": "user", "parts": [{"functionResponse": {"name": "list_directory", "response": {"result": "a.txt", "success": True}}}]},
        {"role": "model", "parts": [{"text": "Found a.txt"}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assert messages[2]["role"] == "assistant" and messages[2]["tool_calls"]
    assert messages[3]["role"] == "tool"
    assert messages[3]["tool_call_id"] == messages[2]["tool_calls"][0]["id"]
    assert messages[4] == {"role": "assistant", "content": "Found a.txt"}
