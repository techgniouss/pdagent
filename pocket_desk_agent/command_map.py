"""Centralized command registry for the bot."""

from pocket_desk_agent import handlers

# format: (command_name, handler_func, description)
COMMAND_REGISTRY = [
    # Core Bot Commands
    ("start", handlers.start_command, "Initialize the bot"),
    ("help", handlers.help_command, "Show help menu"),
    ("status", handlers.status_command, "Check session status"),
    ("login", handlers.login_command, "Get login link"),
    ("authcode", handlers.authcode_command, "Enter auth code"),
    ("checkauth", handlers.checkauth_command, "Check auth status"),
    ("logout", handlers.logout_command, "Sign out"),
    ("new", handlers.new_command, "Start new chat"),
    ("enhance", handlers.enhance_command, "Enhance prompt"),
    ("sync", handlers.sync_commands_command, "Sync command list with Telegram"),
    # File System Commands
    ("pwd", handlers.pwd_command, "Current directory"),
    ("cd", handlers.cd_command, "Change directory"),
    ("ls", handlers.ls_command, "List files"),
    ("cat", handlers.cat_command, "View file content"),
    ("find", handlers.find_command, "Search files"),
    ("info", handlers.info_command, "Get file info"),
    # Remote Desktop Commands
    (
        "remote",
        handlers.remote_command,
        "Start live remote desktop (returns HTTPS URL + QR)",
    ),
    (
        "stopremote",
        handlers.stopremote_command,
        "Stop the active remote desktop session",
    ),
    # System Control Commands
    ("stopbot", handlers.stopbot_command, "Stop the bot process"),
    ("shutdown", handlers.shutdown_command, "Shutdown the PC"),
    ("sleep", handlers.sleep_command, "Put PC to sleep"),
    ("privacy", handlers.privacy_command, "Blank or wake the display without locking"),
    ("wakeup", handlers.wakeup_command, "PC wakeup information"),
    ("battery", handlers.battery_command, "Check battery levels"),
    ("screenshot", handlers.screenshot_command, "Take a screenshot"),
    ("hotkey", handlers.hotkey_command, "Send keyboard hotkeys"),
    ("windows", handlers.windows_command, "List open application windows"),
    ("focuswindow", handlers.focuswindow_command, "Activate a listed window"),
    ("clipboard", handlers.clipboard_command, "Set PC clipboard"),
    ("viewclipboard", handlers.viewclipboard_command, "View PC clipboard"),
    # UI Automation Commands
    ("clicktext", handlers.clicktext_command, "Click text on screen"),
    ("findtext", handlers.findtext_command, "Locate text on screen"),
    ("smartclick", handlers.smartclick_command, "OCR-based smart click"),
    ("findelements", handlers.findelements_command, "Find all clickable UI symbols"),
    ("clickelement", handlers.clickelement_command, "Click a labeled UI element"),
    ("pasteenter", handlers.pasteenter_command, "Paste text and press enter"),
    ("typeenter", handlers.typeenter_command, "Type text and press enter"),
    ("scrollup", handlers.scrollup_command, "Scroll up outside text box"),
    ("scrolldown", handlers.scrolldown_command, "Scroll down outside text box"),
    # Custom Command Recording
    ("savecommand", handlers.savecommand_command, "Start recording custom command"),
    ("done", handlers.done_command, "Finish command recording"),
    ("cancelrecord", handlers.cancelrecord_command, "Cancel recording"),
    ("listcommands", handlers.listcommands_command, "List all custom commands"),
    ("deletecommand", handlers.deletecommand_command, "Remove custom command"),
    # Claude Desktop Commands
    ("claudeask", handlers.claudeask_command, "Detailed Claude prompt"),
    ("claudenew", handlers.claudenew_command, "New Claude chat session"),
    ("clauderepo", handlers.clauderepo_command, "Sync repository with Claude"),
    ("claudebranch", handlers.claudebranch_command, "Claude branch management"),
    ("claudelatest", handlers.claudelatest_command, "Latest Claude response"),
    ("claudesearch", handlers.claudesearch_command, "Search Claude history"),
    ("claudeselect", handlers.claudeselect_command, "Select Claude workspace"),
    ("claudemode", handlers.claudemode_command, "Switch Claude mode"),
    ("claudemodel", handlers.claudemodel_command, "Switch Claude model"),
    ("claudescreen", handlers.claudescreen_command, "Claude app screenshot"),
    ("claudechat", handlers.claudechat_command, "Automated Claude chat"),
    (
        "clauderemote",
        handlers.clauderemote_command,
        "Run claude remote-control in repo",
    ),
    ("stopclaude", handlers.stopclaude_command, "Stop claude remote-control session"),
    ("openclaude", handlers.openclaude_command, "Open Claude app"),
    # Antigravity Commands
    ("openantigravity", handlers.openantigravity_command, "Open Antigravity"),
    ("antigravitychat", handlers.antigravitychat_command, "Antigravity chat focus"),
    ("antigravitymode", handlers.antigravitymode_command, "Switch Antigravity mode"),
    ("antigravitymodel", handlers.antigravitymodel_command, "Switch Antigravity model"),
    (
        "antigravityclaudecodeopen",
        handlers.antigravityclaudecodeopen_command,
        "Open Claude Code panel in VS Code",
    ),
    (
        "openclaudeinvscode",
        handlers.openclaudeinvscode_command,
        "Run Claude Code: Open in VS Code",
    ),
    (
        "claudecli",
        handlers.claudecli_command,
        "Open Claude CLI in folder or from picker",
    ),
    (
        "claudeclisend",
        handlers.claudeclisend_command,
        "Send a prompt to active Claude CLI",
    ),
    (
        "antigravityopenfolder",
        handlers.antigravityopenfolder_command,
        "Open a VS Code folder directly or from picker",
    ),
    (
        "openbrowser",
        handlers.openbrowser_command,
        "Open a browser (Edge/Chrome/Firefox/Brave)",
    ),
    # Workflow Commands
    ("build", handlers.build_command, "Start build workflow"),
    ("getapk", handlers.getapk_command, "Download built APK"),
    # Scheduling Commands
    ("schedule", handlers.schedule_command, "Schedule custom command"),
    (
        "repeatschedule",
        handlers.repeatschedule_command,
        "Repeat a custom command for a duration",
    ),
    (
        "watchperm",
        handlers.watchperm_command,
        "Watch Claude or Antigravity for approval buttons",
    ),
    (
        "watchscreen",
        handlers.watchscreen_command,
        "Watch the screen for text and send a hotkey",
    ),
    (
        "stopscreenwatch",
        handlers.stopscreenwatch_command,
        "Stop one or all active screen watchers",
    ),
    ("claudeschedule", handlers.claudeschedule_command, "Schedule prompt to Claude"),
    (
        "scheduleshutdown",
        handlers.scheduleshutdown_command,
        "Schedule a one-shot system shutdown",
    ),
    (
        "listschedules",
        handlers.listschedules_command,
        "View all pending scheduled tasks",
    ),
    (
        "cancelschedule",
        handlers.cancelschedule_command,
        "Cancel a pending scheduled task",
    ),
]
