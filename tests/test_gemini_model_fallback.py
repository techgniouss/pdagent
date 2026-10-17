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
