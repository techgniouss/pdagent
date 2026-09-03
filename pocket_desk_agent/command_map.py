"""Centralized command registry for the bot."""

from pocket_desk_agent import handlers

# format: (command_name, handler_func, description)
COMMAND_REGISTRY = [
    # Core Bot Commands
    ("start", handlers.start_command, "Initialize the bot"),
    ("help", handlers.help_command, "Show help menu"),
    ("status", handlers.status_command, "Check session status"),
    ("aiprovider", handlers.aiprovider_command, "View or set AI provider fallback order"),
    ("login", handlers.login_command, "Get login link"),
    ("authcode", handlers.authcode_command, "Enter auth code"),
    ("checkauth", handlers.checkauth_command, "Check auth status"),
    ("logout", handlers.logout_command, "Sign out"),
    ("setnvidiakey", handlers.setnvidiakey_command, "Set NVIDIA NIM API key (AI fallback)"),
    ("new", handlers.new_command, "Start new chat"),
    ("enhance", handlers.enhance_command, "Enhance prompt"),
    ("sync", handlers.sync_commands_command, "Sync command list with Telegram"),
    ("selftest", handlers.selftest_command, "Run non-GUI functional self-checks"),
    ("update", handlers.update_command, "Upgrade and restart the bot"),
    # File System Commands
    ("pwd", handlers.pwd_command, "Current directory"),
    ("cd", handlers.cd_command, "Change directory"),
    ("ls", handlers.ls_command, "List files"),
    ("cat", handlers.cat_command, "View file content"),
    ("getfile", handlers.getfile_command, "Download a file"),
    ("find", handlers.find_command, "Search files"),
    ("info", handlers.info_command, "Get file info"),
    ("approvedirs", handlers.approvedirs_command, "View or change approved sandbox directories"),
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
    (
        "remoteinfo",
        handlers.remoteinfo_command,
        "Show active remote desktop session status",
    ),
    # System Control Commands
    ("openapp", handlers.openapp_command, "Open a safe desktop app"),
    ("closeapp", handlers.closeapp_command, "Close a desktop app"),
    ("stopbot", handlers.stopbot_command, "Stop the bot process"),
    ("shutdown", handlers.shutdown_command, "Shutdown the PC"),
    ("sleep", handlers.sleep_command, "Put PC to sleep"),
    ("privacy", handlers.privacy_command, "Blank or wake the display without locking"),
    ("wakeup", handlers.wakeup_command, "PC wakeup information"),
    ("battery", handlers.battery_command, "Check battery levels"),
    ("autobattery", handlers.autobattery_command, "Auto-manage charging via smart plug"),
    ("smartplug", handlers.smartplug_command, "Control smart plug manually"),
    ("screenshot", handlers.screenshot_command, "Take a screenshot"),
    ("hotkey", handlers.hotkey_command, "Send keyboard hotkeys"),
    ("windows", handlers.windows_command, "List open application windows"),
    ("focuswindow", handlers.focuswindow_command, "Activate a listed window"),
    ("clipboard", handlers.clipboard_command, "Set PC clipboard"),
    (
        "pasteimage",
        handlers.pasteimage_command,
        "Reply to an image and paste it into active app",
    ),
    (
        "pasteimages",
        handlers.pasteimages_command,
        "Reply to an album image and paste all images",
    ),
    ("viewclipboard", handlers.viewclipboard_command, "View PC clipboard"),
    # UI Automation Commands
    ("clicktext", handlers.clicktext_command, "Click text on screen"),
    ("findtext", handlers.findtext_command, "Locate text on screen"),
    ("smartclick", handlers.smartclick_command, "OCR-based smart click"),
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
    ("claudescreen", handlers.claudescreen_command, "Claude app screenshot"),
    ("openclaude", handlers.openclaude_command, "Open Claude app"),
    # Antigravity / VS Code Commands
    ("openantigravity", handlers.openantigravity_command, "Open Antigravity"),
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
    ("stopbuildscreenshot", handlers.stopbuildscreenshot_command, "Stop build screenshot monitoring"),
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
        "watchnotify",
        handlers.watchnotify_command,
        "Watch screen or app text and notify in Telegram",
    ),
    (
        "watchstatus",
        handlers.watchstatus_command,
        "Show active watcher tasks only",
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
    # Workflow Recipe Commands
    ("recipecreate", handlers.recipecreate_command, "Create a reusable workflow recipe"),
    (
        "recipeaddcommand",
        handlers.recipeaddcommand_command,
        "Add a saved custom command step to a recipe",
    ),
    (
        "recipeaddclaude",
        handlers.recipeaddclaude_command,
        "Add a Claude prompt step to a recipe",
    ),
    ("recipeaddwait", handlers.recipeaddwait_command, "Add a wait-duration step to a recipe"),
    (
        "recipeaddwaittext",
        handlers.recipeaddwaittext_command,
        "Add a wait-until-text step to a recipe",
    ),
    ("recipeaddnotify", handlers.recipeaddnotify_command, "Add a Telegram notify step to a recipe"),
    ("recipelist", handlers.recipelist_command, "List workflow recipes"),
    ("recipeshow", handlers.recipeshow_command, "Show recipe steps"),
    ("recipedelete", handlers.recipedelete_command, "Delete a workflow recipe"),
    ("reciperun", handlers.reciperun_command, "Run a workflow recipe"),
]
