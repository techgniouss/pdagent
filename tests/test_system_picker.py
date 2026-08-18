from pocket_desk_agent.handlers import system


def test_build_app_picker_keyboard_includes_request_id() -> None:
    keyboard = system._build_app_picker_keyboard(
        "open",
        "req-123",
        {1: "chrome"},
    )

    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "appselect_req-123_open_1"
