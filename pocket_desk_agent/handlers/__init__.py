"""Handlers package — re-exports all public names.

This package was split from the original monolithic handlers.py.
Importing ``from pocket_desk_agent import handlers`` then using
``handlers.start_command`` (etc.) continues to work unchanged.
"""

# Shared utilities & state (needed by main.py and command_map.py)
from pocket_desk_agent.handlers._shared import (  # noqa: F401
    safe_command,
    record_action_if_active,
    auth_client,
    gemini_client,
    file_manager,
    recording_sessions,
    PYWINAUTO_AVAILABLE,
)

# ── Auth ────────────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.auth import (  # noqa: F401
    login_command,
    authcode_command,
    checkauth_command,
    logout_command,
)

# ── Core ────────────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.core import (  # noqa: F401
    start_command,
    help_command,
    new_command,
    status_command,
    enhance_command,
    handle_message,
    handle_photo,
    error_handler,
    sync_commands_command,
    get_bot_commands,
)

# ── File System ─────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.filesystem import (  # noqa: F401
    pwd_command,
    cd_command,
    ls_command,
    cat_command,
    find_command,
    info_command,
)

# ── System Control ──────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.system import (  # noqa: F401
    stopbot_command,
    shutdown_command,
    battery_command,
    screenshot_command,
    sleep_command,
    privacy_command,
    wakeup_command,
    hotkey_command,
    windows_command,
    focuswindow_command,
    clipboard_command,
    viewclipboard_command,
)

# ── UI Automation ───────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.automation import (  # noqa: F401
    clicktext_command,
    findtext_command,
    smartclick_command,
    findelements_command,
    clickelement_command,
    pasteenter_command,
    typeenter_command,
    scrollup_command,
    scrolldown_command,
)

# ── Custom Commands ─────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.custom_commands import (  # noqa: F401
    savecommand_command,
    done_command,
    cancelrecord_command,
    listcommands_command,
    deletecommand_command,
    execute_custom_command,
)

# ── Claude Desktop ──────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.claude import (  # noqa: F401
    clauderemote_command,
    stopclaude_command,
    openclaude_command,
    claudeask_command,
    claudenew_command,
    claudescreen_command,
    claudechat_command,
    claudelatest_command,
    claudemode_command,
    claudemodel_command,
    claudesearch_command,
    claudeselect_command,
    claudebranch_command,
    clauderepo_command,
    clauderepo_list,
    clauderepo_browse,
    find_claude_window,
    ensure_claude_open,
    capture_claude_screenshot,
)

# ── Antigravity / VS Code ──────────────────────────────────────────────────
from pocket_desk_agent.handlers.antigravity import (  # noqa: F401
    openantigravity_command,
    antigravitychat_command,
    antigravitymode_command,
    antigravitymodel_command,
    find_antigravity_window,
    antigravityclaudecodeopen_command,
    openclaudeinvscode_command,
    claudecli_command,
    claudeclisend_command,
    antigravityopenfolder_command,
    openbrowser_command,
)

# ── Build / APK ─────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.build import (  # noqa: F401
    build_command,
    check_build_selection,
    execute_build_command,
    monitor_build_window,
    capture_full_screen,
    capture_window_screenshot,
    find_and_send_apk,
    getapk_command,
    check_apk_retrieval_selection,
    show_folder_contents,
    send_apk_file,
    upload_to_tempfile,
    upload_to_dropbox,
    upload_large_file,
)

# ── Scheduling ──────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.scheduling import (  # noqa: F401
    parse_schedule_time,
    claudeschedule_command,
    schedule_command,
    repeatschedule_command,
    watchperm_command,
    watchscreen_command,
    stopscreenwatch_command,
    listschedules_command,
    cancelschedule_command,
    cleanup_scheduled_task_artifacts,
    describe_task,
    execute_scheduled_task,
    run_custom_actions,
)

# ── Callbacks ───────────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.callbacks import (  # noqa: F401
    button_callback,
    handle_dropbox_delete,
    handle_upload_choice,
    delete_from_dropbox,
)

# ── Remote Desktop ─────────────────────────────────────────────────────────
from pocket_desk_agent.handlers.remote import (  # noqa: F401
    remote_command,
    stopremote_command,
    start_remote_session,
    stop_remote_session,
    teardown_all_sessions,
)
