"""OCR candidate scoring must not click the wrong control for short labels."""
import pytest

from pocket_desk_agent.automation_utils import _score_ocr_candidate


def _score(candidate: str, search: str):
    from pocket_desk_agent.automation_utils import _compact_ocr_text, _normalize_ocr_text

    return _score_ocr_candidate(candidate, _normalize_ocr_text(search), _compact_ocr_text(search))


@pytest.mark.parametrize(
    "candidate,search",
    [("Token", "OK"), ("Broken", "ok"), ("Running", "Run"), ("Yesterday", "Yes")],
)
def test_short_search_does_not_match_inside_other_words(candidate, search) -> None:
    assert _score(candidate, search) is None


@pytest.mark.parametrize("candidate,search", [("OK", "ok"), ("Run", "RUN"), ("Yes", "yes")])
def test_short_search_matches_exact_word(candidate, search) -> None:
    assert _score(candidate, search) == 1.0


def test_longer_search_still_matches_substrings_and_fuzzy() -> None:
    assert _score("Continue", "Continue") == 1.0
    assert _score("Continuing now", "Continu") is not None
    assert _score("Alow", "Allow") is not None
