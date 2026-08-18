import re

from pocket_desk_agent.remote.web_server import _VIEWER_HTML


def _viewer_section(start_marker: str, end_marker: str) -> str:
    start = _VIEWER_HTML.index(start_marker)
    end = _VIEWER_HTML.index(end_marker, start)
    return _VIEWER_HTML[start:end]


def test_remote_viewer_exposes_explicit_drag_mode_control() -> None:
    assert 'id="dragBtn"' in _VIEWER_HTML
    assert ">drag off<" in _VIEWER_HTML


def test_remote_viewer_touchmove_does_not_start_left_drag_implicitly() -> None:
    touchmove_section = _viewer_section(
        "canvas.addEventListener('touchmove'",
        "canvas.addEventListener('touchend'",
    )

    assert "if (!dragMode)" in touchmove_section
    non_drag_branch = touchmove_section.split("if (!dragMode)", 1)[1].split(
        "send({type:'down'",
        1,
    )[0]
    assert "send({type:'down'" not in non_drag_branch


def test_remote_viewer_long_press_right_click_happens_on_release() -> None:
    touchend_section = _viewer_section(
        "canvas.addEventListener('touchend'",
        "canvas.addEventListener('touchcancel'",
    )

    assert "heldMs >= LONG_PRESS_MS" in touchend_section
    assert "button:'right'" in touchend_section


def test_remote_viewer_uses_accumulated_touch_scroll_steps() -> None:
    assert re.search(r"TOUCH_SCROLL_UNIT\s*=\s*120", _VIEWER_HTML)
    assert "scrollCarryY" in _VIEWER_HTML
