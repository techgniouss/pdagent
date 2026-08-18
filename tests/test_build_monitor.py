from pocket_desk_agent.handlers import build
from pocket_desk_agent.handlers._shared import build_monitor_state, build_screenshot_tasks


def test_create_build_monitor_request_uses_unique_ids() -> None:
    build_monitor_state.clear()

    first = build.create_build_monitor_request(
        window_title="Build: first",
        repo_path=r"C:\repo-one",
        build_type="debug",
        chat_id=1,
        user_id=99,
    )
    second = build.create_build_monitor_request(
        window_title="Build: second",
        repo_path=r"C:\repo-two",
        build_type="release",
        chat_id=1,
        user_id=99,
    )

    assert first != second
    assert build_monitor_state[first]["repo_path"] == r"C:\repo-one"
    assert build_monitor_state[second]["repo_path"] == r"C:\repo-two"


def test_unregister_build_screenshot_task_only_clears_matching_task() -> None:
    current_task = object()
    replacement_task = object()

    build_screenshot_tasks.clear()
    build_screenshot_tasks[99] = replacement_task

    build.unregister_build_screenshot_task(99, current_task)
    assert build_screenshot_tasks[99] is replacement_task

    build.unregister_build_screenshot_task(99, replacement_task)
    assert 99 not in build_screenshot_tasks
