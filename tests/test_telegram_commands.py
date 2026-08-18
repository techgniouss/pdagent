from pocket_desk_agent.telegram_commands import (
    TELEGRAM_MAX_BOT_COMMANDS,
    trim_registry_for_telegram,
)


def test_trim_registry_for_telegram_caps_to_api_limit() -> None:
    registry = [(f"cmd{i}", object(), f"description {i}") for i in range(105)]

    trimmed, dropped = trim_registry_for_telegram(registry)

    assert len(trimmed) == TELEGRAM_MAX_BOT_COMMANDS
    assert dropped == 5
    assert trimmed[0] == ("cmd0", "description 0")
    assert trimmed[-1] == ("cmd99", "description 99")


def test_trim_registry_for_telegram_keeps_all_when_under_limit() -> None:
    registry = [("start", object(), "Initialize the bot")]

    trimmed, dropped = trim_registry_for_telegram(registry)

    assert trimmed == [("start", "Initialize the bot")]
    assert dropped == 0
