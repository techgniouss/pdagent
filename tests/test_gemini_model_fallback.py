"""Model-lookup fallback behaviour for retired/missing Gemini models."""
import pytest

from pocket_desk_agent.gemini_client import _candidate_model_names, _is_model_not_found_error


@pytest.mark.parametrize(
    "error",
    [
        "HTTP 404: Requested entity was not found.",
        "HTTP 404: models/gemini-2.0-flash is not found for API version v1beta",
        "HTTP 410: model has reached end of life",
    ],
)
def test_missing_or_retired_model_triggers_fallback(error) -> None:
    assert _is_model_not_found_error({"error": error}) is True


@pytest.mark.parametrize("error", ["HTTP 429: quota", "HTTP 500: boom", "HTTP 403: denied"])
def test_other_errors_do_not_trigger_model_fallback(error) -> None:
    assert _is_model_not_found_error({"error": error}) is False


def test_candidates_never_include_retired_models() -> None:
    assert "gemini-2.0-flash" not in _candidate_model_names("gemini-2.5-flash")
    assert "gemini-2.5-flash" in _candidate_model_names("gemini-3-pro")


from pocket_desk_agent.gemini_client import _is_auth_error


@pytest.mark.parametrize(
    "error",
    [
        "HTTP 401: Request had invalid authentication credentials",
        "HTTP 400: invalid_grant: Token has been expired or revoked.",
        '{"status": "UNAUTHENTICATED"}',
    ],
)
def test_dead_oauth_session_is_an_auth_error(error) -> None:
    assert _is_auth_error(error, "antigravity") is True


@pytest.mark.parametrize(
    "error",
    [
        "HTTP 403: PERMISSION_DENIED project access",
        "HTTP 500: upstream returned 401 items",
        "HTTP 429: tokens 1401 used",
    ],
)
def test_other_failures_do_not_log_the_user_out(error) -> None:
    assert _is_auth_error(error, "antigravity") is False


def test_api_key_mode_never_counts_as_expired_session() -> None:
    assert _is_auth_error("HTTP 401: API key not valid", "apikey") is False


def test_transient_refresh_failure_keeps_credentials(monkeypatch) -> None:
    import types

    from pocket_desk_agent import gemini_client as gc

    client = gc.GeminiClient.__new__(gc.GeminiClient)
    logged_out: list[int] = []
    client._auto_logout_oauth = lambda uid, oauth, reason="": logged_out.append(uid)  # type: ignore[method-assign]

    still_has_refresh = types.SimpleNamespace(refresh_token="r-token")
    result = client._no_token_result(1, still_has_refresh)
    assert result.is_retryable_error and "try again" in result.text.lower()
    assert logged_out == []

    revoked = types.SimpleNamespace(refresh_token=None)
    result = client._no_token_result(1, revoked)
    assert logged_out == [1] and "/login" in result.text
