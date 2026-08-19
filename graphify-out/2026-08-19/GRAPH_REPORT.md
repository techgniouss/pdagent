# Graph Report - pdagent  (2026-08-19)

## Corpus Check
- 88 files · ~341,951 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3201 nodes · 6396 edges · 185 communities (125 shown, 60 thin omitted)
- Extraction: 55% EXTRACTED · 45% INFERRED · 0% AMBIGUOUS · INFERRED: 2874 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `df1c5c32`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pocket_desk_agent.handlers.system
- RuntimeError
- scripts.manage_auth
- pocket_desk_agent.handlers.build
- pocket_desk_agent.command_map
- pocket_desk_agent.handlers.scheduling
- plugins.caveman.skills.compress.scripts.compress
- scheduling.py
- pocket_desk_agent.remote.session
- pocket_desk_agent.automation_utils
- docs/REMOTE.md
- _stop_via_pidfile
- pocket_desk_agent.configure
- AntigravityOAuth
- gemini_actions.py
- README.md
- system.py
- compress/SKILL.md
- core.py
- GeminiCLIOAuth
- StartupManager
- AntigravityAuth
- configure.py
- find_text_in_image
- Caveman
- pocket_desk_agent.gemini_actions
- Caveman icon
- handlers/__init__.py
- build.py
- docs/MOBILE_AUTHENTICATION.md
- pocket_desk_agent/cli.py
- compress/scripts/__init__.py
- StartupManager
- AntigravityOAuth
- Config
- GeminiCLIOAuth
- FileManager
- filesystem.py
- plugins.caveman.skills.compress.scripts.validate
- pocket_desk_agent.config
- callbacks.py
- antigravity.py
- scripts.install.ps1
- scripts
- remote.py
- pocket_desk_agent.gemini_client
- pocket_desk_agent.antigravity_auth
- gemini_client.py
- pocket_desk_agent.scheduling_utils
- pocket_desk_agent.updater
- pocket_desk_agent.main
- pocket_desk_agent.handlers.claude
- updater.py
- GeminiClient
- docs/dropbox-setup.md
- plugins.caveman.skills.compress.scripts.benchmark
- existing_app_path
- plugins.caveman.skills.compress.scripts.detect
- smart_plug.py
- RemoteSession
- load
- tunnel.py
- pocket_desk_agent.remote.web_server
- save_tokens
- pocket_desk_agent.handlers.remote
- app_control.py
- main
- load
- pocket_desk_agent.handlers.antigravity
- AntigravityAuth
- do_GET
- SchedulerRegistry
- generate
- find_text_in_image
- caveman/SKILL.md
- pocket_desk_agent.handlers.automation
- app_catalog.py
- find_ui_elements
- CommandRegistry
- QuboClient
- RecipeRegistry
- list_open_windows
- Mobile Authentication Guide
- pocket_desk_agent.app_paths
- get_windows_input_desktop_name
- pocket_desk_agent.cli
- pocket_desk_agent.window_utils
- Dropbox Setup Guide
- telegram.InlineKeyboardButton
- InputDispatcher
- Smart Plug & Auto Battery Management
- start_remote_session
- .refresh_token_if_needed
- manage_service.py
- _extract_ocr_words
- print
- Live Remote Desktop (`/remote`)
- pocket_desk_agent.handlers.filesystem
- DesktopAppEntry
- ._call_api_raw
- done_command
- RateLimiter
- annotate_screenshot_with_markers
- _run_background
- scripts.manage_service
- OAuthCallbackHandler
- TokenStorage
- winget_install_cloudflared
- capture.py
- _auth
- CommandAction
- _build_ui_masks
- _build_ocr_passes
- _ensure_tesseract
- append
- main
- Contributor Covenant Code of Conduct
- PULL_REQUEST_TEMPLATE.md
- monitor_build_window
- .connect_mqtt
- RateLimiter
- trim_registry_for_telegram
- resolve_app_query
- _load_config_files
- pocket_desk_agent
- ._disconnect_mqtt
- /antigravitychat
- /antigravityclaudecodeopen
- /antigravitymode
- /antigravityopenfolder
- /battery
- /build
- /cancelrecord
- /cd
- /claudechat
- /claudecli
- /claudeclisend
- /claudelatest
- /claudemode
- /claudemodel
- /clauderemote
- /clauderepo
- /claudeschedule
- /claudeselect
- /clicktext
- /clipboard
- /deletecommand
- /getapk
- /help
- /hotkey
- /info
- /listcommands
- /ls
- /openantigravity
- /openbrowser
- /openclaudeinvscode
- /pasteenter
- /privacy
- /pwd
- /remote
- /repeatschedule
- /savecommand
- /scrollup
- /shutdown
- /sleep
- /smartclick
- /start
- /stopclaude
- /stopremote
- /stopscreenwatch
- /sync
- /typeenter
- /viewclipboard
- /watchperm
- /watchscreen
- /windows
- _load_state
- pocket_desk_agent/__init__.py
- remote/__init__.py
- scripts/__init__.py
- setup.sh
- pocket-desk-agent

## God Nodes (most connected - your core abstractions)
1. `pocket_desk_agent.command_map` - 80 edges
2. `pocket_desk_agent.handlers.scheduling` - 76 edges
3. `pocket_desk_agent.handlers.system` - 52 edges
4. `Config` - 49 edges
5. `pocket_desk_agent.automation_utils` - 49 edges
6. `pocket_desk_agent.config` - 46 edges
7. `pocket_desk_agent.configure` - 44 edges
8. `GeminiCLIOAuth` - 41 edges
9. `pocket_desk_agent.cli` - 40 edges
10. `_execute_confirmed_action()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `manage_auth()` --uses--> `Config`  [INFERRED]
  scripts/manage_auth.py → pocket_desk_agent/config.py
- `manage_auth()` --uses--> `GeminiCLIOAuth`  [INFERRED]
  scripts/manage_auth.py → pocket_desk_agent/gemini_cli_auth.py
- `Windows Primary Platform` --conceptually_related_to--> `pyautogui (win32)`  [INFERRED]
  README.md → requirements.txt
- `Windows Primary Platform` --conceptually_related_to--> `pygetwindow (win32)`  [INFERRED]
  README.md → requirements.txt
- `Windows Primary Platform` --conceptually_related_to--> `pywinauto (win32)`  [INFERRED]
  README.md → requirements.txt

## Import Cycles
- 2-file cycle: `pocket_desk_agent/antigravity_auth.py -> pocket_desk_agent/auth.py -> pocket_desk_agent/antigravity_auth.py`
- 2-file cycle: `pocket_desk_agent/app_paths.py -> pocket_desk_agent/configure.py -> pocket_desk_agent/app_paths.py`
- 2-file cycle: `pocket_desk_agent/app_paths.py -> pocket_desk_agent/cli.py -> pocket_desk_agent/app_paths.py`
- 2-file cycle: `pocket_desk_agent/app_paths.py -> pocket_desk_agent/command_registry.py -> pocket_desk_agent/app_paths.py`
- 3-file cycle: `pocket_desk_agent/antigravity_auth.py -> pocket_desk_agent/auth.py -> pocket_desk_agent/gemini_cli_auth.py -> pocket_desk_agent/antigravity_auth.py`
- 3-file cycle: `pocket_desk_agent/app_paths.py -> pocket_desk_agent/cli.py -> pocket_desk_agent/configure.py -> pocket_desk_agent/app_paths.py`
- 4-file cycle: `pocket_desk_agent/app_paths.py -> pocket_desk_agent/cli.py -> pocket_desk_agent/config.py -> pocket_desk_agent/configure.py -> pocket_desk_agent/app_paths.py`

## Hyperedges (group relationships)
- **Multilingual README Documentation Bundle** — file_readme_md, file_readme_de_md, file_readme_es_md, file_readme_fr_md, file_readme_ja_md, file_readme_ko_md, file_readme_pt_br_md, file_readme_ru_md, file_readme_tr_md, file_readme_uk_md, file_readme_zh_cn_md [EXTRACTED 1.00]
- **Maintainer and Contributor Guidance** — file_agents_md, file_claude_md, file_contributing_md, file_project_structure_md [INFERRED 0.91]
- **Authentication, Security, and Command Policy Docs** — file_security_md, file_docs_authentication_requirements_md, file_docs_commands_md, file_docs_antigravity_login_implementation_md [INFERRED 0.89]
- **hyperedge:mobile_auth_flow_chunk02** — file:docs/MOBILE_AUTHENTICATION.md, module:pocket_desk_agent.antigravity_auth, module:pocket_desk_agent.auth, module:pocket_desk_agent.configure, module:pocket_desk_agent.config [INFERRED 0.88]
- **hyperedge:compress_skill_workflow_chunk02** — file:plugins/caveman/skills/compress/SKILL.md, module:plugins.caveman.skills.compress.scripts.cli, module:plugins.caveman.skills.compress.scripts.compress, module:plugins.caveman.skills.compress.scripts.detect, module:plugins.caveman.skills.compress.scripts.validate, module:plugins.caveman.skills.compress.scripts.benchmark [INFERRED 0.86]
- **hyperedge:telegram_command_registry_chunk02** — module:pocket_desk_agent.command_map, command:/abcd, command:/accounts, command:/antigravitychat, command:/antigravityclaudecodeopen, command:/antigravitymode, command:/antigravitymodel, command:/antigravityopenfolder, command:/authcode, command:/authcode <code_or_callback_url>, command:/battery, command:/build, command:/cancelrecord, command:/cancelschedule, command:/cat, command:/caveman, command:/caveman lite|full|ultra, command:/caveman:compress <filepath>, command:/cd, command:/checkauth, command:/claudeask, command:/claudebranch, command:/claudechat, command:/claudecli, command:/claudeclisend, command:/claudelatest, command:/claudemode, command:/claudemodel, command:/claudenew, command:/clauderemote, command:/clauderepo, command:/claudeschedule, command:/claudescreen, command:/claudesearch, command:/claudeselect, command:/clickelement, command:/clicktext, command:/clipboard, command:/config, command:/deletecommand, command:/developers, command:/done, command:/enhance, command:/find, command:/findelements, command:/findtext, command:/focuswindow, command:/getapk, command:/help, command:/hotkey, command:/info, command:/listcommands, command:/listschedules, command:/localhost, command:/login, command:/logout, command:/ls, command:/new, command:/openantigravity, command:/openbrowser, command:/openclaude, command:/openclaudeinvscode, command:/pasteenter, command:/privacy, command:/pwd, command:/remote, command:/repeatschedule, command:/savecommand, command:/schedule, command:/screenshot, command:/scrolldown, command:/scrollup, command:/shutdown, command:/sleep, command:/smartclick, command:/src, command:/src/components/..., command:/start, command:/status, command:/stopbot, command:/stopclaude, command:/stopremote, command:/stopscreenwatch, command:/sync, command:/typeenter, command:/viewclipboard, command:/wakeup, command:/watchperm, command:/watchscreen, command:/windows, command:/ws, command:/ws/input, command:/ws/video, command:/www, handler_ref:pocket_desk_agent.handlers.antigravitychat_command, handler_ref:pocket_desk_agent.handlers.antigravityclaudecodeopen_command, handler_ref:pocket_desk_agent.handlers.antigravitymode_command, handler_ref:pocket_desk_agent.handlers.antigravitymodel_command, handler_ref:pocket_desk_agent.handlers.antigravityopenfolder_command, handler_ref:pocket_desk_agent.handlers.authcode_command, handler_ref:pocket_desk_agent.handlers.battery_command, handler_ref:pocket_desk_agent.handlers.build_command, handler_ref:pocket_desk_agent.handlers.cancelrecord_command, handler_ref:pocket_desk_agent.handlers.cancelschedule_command, handler_ref:pocket_desk_agent.handlers.cat_command, handler_ref:pocket_desk_agent.handlers.cd_command, handler_ref:pocket_desk_agent.handlers.checkauth_command, handler_ref:pocket_desk_agent.handlers.claudeask_command, handler_ref:pocket_desk_agent.handlers.claudebranch_command, handler_ref:pocket_desk_agent.handlers.claudechat_command, handler_ref:pocket_desk_agent.handlers.claudecli_command, handler_ref:pocket_desk_agent.handlers.claudeclisend_command, handler_ref:pocket_desk_agent.handlers.claudelatest_command, handler_ref:pocket_desk_agent.handlers.claudemode_command, handler_ref:pocket_desk_agent.handlers.claudemodel_command, handler_ref:pocket_desk_agent.handlers.claudenew_command, handler_ref:pocket_desk_agent.handlers.clauderemote_command, handler_ref:pocket_desk_agent.handlers.clauderepo_command, handler_ref:pocket_desk_agent.handlers.claudeschedule_command, handler_ref:pocket_desk_agent.handlers.claudescreen_command, handler_ref:pocket_desk_agent.handlers.claudesearch_command, handler_ref:pocket_desk_agent.handlers.claudeselect_command, handler_ref:pocket_desk_agent.handlers.clickelement_command, handler_ref:pocket_desk_agent.handlers.clicktext_command, handler_ref:pocket_desk_agent.handlers.clipboard_command, handler_ref:pocket_desk_agent.handlers.deletecommand_command, handler_ref:pocket_desk_agent.handlers.done_command, handler_ref:pocket_desk_agent.handlers.enhance_command, handler_ref:pocket_desk_agent.handlers.find_command, handler_ref:pocket_desk_agent.handlers.findelements_command, handler_ref:pocket_desk_agent.handlers.findtext_command, handler_ref:pocket_desk_agent.handlers.focuswindow_command, handler_ref:pocket_desk_agent.handlers.getapk_command, handler_ref:pocket_desk_agent.handlers.help_command, handler_ref:pocket_desk_agent.handlers.hotkey_command, handler_ref:pocket_desk_agent.handlers.info_command, handler_ref:pocket_desk_agent.handlers.listcommands_command, handler_ref:pocket_desk_agent.handlers.listschedules_command, handler_ref:pocket_desk_agent.handlers.login_command, handler_ref:pocket_desk_agent.handlers.logout_command, handler_ref:pocket_desk_agent.handlers.ls_command, handler_ref:pocket_desk_agent.handlers.new_command, handler_ref:pocket_desk_agent.handlers.openantigravity_command, handler_ref:pocket_desk_agent.handlers.openbrowser_command, handler_ref:pocket_desk_agent.handlers.openclaude_command, handler_ref:pocket_desk_agent.handlers.openclaudeinvscode_command, handler_ref:pocket_desk_agent.handlers.pasteenter_command, handler_ref:pocket_desk_agent.handlers.privacy_command, handler_ref:pocket_desk_agent.handlers.pwd_command, handler_ref:pocket_desk_agent.handlers.remote_command, handler_ref:pocket_desk_agent.handlers.repeatschedule_command, handler_ref:pocket_desk_agent.handlers.savecommand_command, handler_ref:pocket_desk_agent.handlers.schedule_command, handler_ref:pocket_desk_agent.handlers.screenshot_command, handler_ref:pocket_desk_agent.handlers.scrolldown_command, handler_ref:pocket_desk_agent.handlers.scrollup_command, handler_ref:pocket_desk_agent.handlers.shutdown_command, handler_ref:pocket_desk_agent.handlers.sleep_command, handler_ref:pocket_desk_agent.handlers.smartclick_command, handler_ref:pocket_desk_agent.handlers.start_command, handler_ref:pocket_desk_agent.handlers.status_command, handler_ref:pocket_desk_agent.handlers.stopbot_command, handler_ref:pocket_desk_agent.handlers.stopclaude_command, handler_ref:pocket_desk_agent.handlers.stopremote_command, handler_ref:pocket_desk_agent.handlers.stopscreenwatch_command, handler_ref:pocket_desk_agent.handlers.sync_commands_command, handler_ref:pocket_desk_agent.handlers.typeenter_command, handler_ref:pocket_desk_agent.handlers.viewclipboard_command, handler_ref:pocket_desk_agent.handlers.wakeup_command, handler_ref:pocket_desk_agent.handlers.watchperm_command, handler_ref:pocket_desk_agent.handlers.watchscreen_command, handler_ref:pocket_desk_agent.handlers.windows_command [INFERRED 0.93]
- **hyperedge:config_env_surface_chunk02** — module:pocket_desk_agent.config, env:ACTIVE, env:ALLOWED_USERS, env:ANTIGRAVITY_ENABLED, env:ANTIGRAVITY_MODEL, env:ANTIGRAVITY_PROJECT_ID, env:APPROVED_DIRECTORIES, env:APPROVED_DIRECTORY, env:AUTHENTICATION_REQUIREMENTS, env:AUTHORIZED_USER_IDS, env:AUTO_UPDATE_CHECK, env:AUTO_UPDATE_ENABLED, env:AUTO_UPDATE_INTERVAL_MINUTES, env:CLAUDE, env:CLAUDE_DEFAULT_REPO_PATH, env:CLOUDFLARED_PATH, env:CRITICAL, env:DEFAULT_REPO_PATH, env:DROP, env:DROPBOX_ACCESS_TOKEN, env:EVERY, env:EXACTLY, env:FILE, env:GEMINI_AUTH_MODE, env:GEMINI_MODEL, env:GOOGLE_API_KEY, env:GOOGLE_OAUTH_ENABLED, env:GOOGLE_PROJECT_ID, env:HOME, env:HTML, env:HTTP, env:HTTPS, env:JPEG, env:LOG_LEVEL, env:MAX_TOKENS_PER_REQUEST, env:MJPEG, env:NEVER, env:NODE_ENV, env:ONLY, env:PATH, env:PKCE, env:REMOTE_AI_TOOLS_ENABLED, env:REMOTE_BIND_HOST, env:REMOTE_DEFAULT_FPS, env:REMOTE_ENABLED, env:REMOTE_IDLE_TIMEOUT_SECS, env:REMOTE_JPEG_QUALITY, env:REMOTE_MAX_WIDTH, env:RESPONSE, env:RULE, env:SKILL, env:SYSTEM_INSTRUCTION, env:SYSTEM_PROMPT, env:TABLE, env:TELEGRAM_BOT_TOKEN, env:TELEGRAM_BOT_USERNAME, env:UPLOAD_EXPIRY_TIME, env:YAML [INFERRED 0.95]
- **hyperedge:module_scope:pocket_desk_agent.file_manager** — module:pocket_desk_agent.file_manager, class:pocket_desk_agent.file_manager.FileManager, method:pocket_desk_agent.file_manager.FileManager.__init__, method:pocket_desk_agent.file_manager.FileManager._format_size, method:pocket_desk_agent.file_manager.FileManager._is_safe_path, method:pocket_desk_agent.file_manager.FileManager.append_file, method:pocket_desk_agent.file_manager.FileManager.create_directory, method:pocket_desk_agent.file_manager.FileManager.delete_file, method:pocket_desk_agent.file_manager.FileManager.execute_command, method:pocket_desk_agent.file_manager.FileManager.get_current_dir, method:pocket_desk_agent.file_manager.FileManager.get_file_info, method:pocket_desk_agent.file_manager.FileManager.get_tree_structure, method:pocket_desk_agent.file_manager.FileManager.list_directory, method:pocket_desk_agent.file_manager.FileManager.read_file, method:pocket_desk_agent.file_manager.FileManager.search_files, method:pocket_desk_agent.file_manager.FileManager.set_current_dir, method:pocket_desk_agent.file_manager.FileManager.write_file [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.gemini_actions** — module:pocket_desk_agent.gemini_actions, class:pocket_desk_agent.gemini_actions.GeminiToolResult, class:pocket_desk_agent.gemini_actions.PendingGeminiAction, class:pocket_desk_agent.gemini_actions._MessageCollector, function:pocket_desk_agent.gemini_actions._capture_screenshot, function:pocket_desk_agent.gemini_actions._check_tool_rate_limit, function:pocket_desk_agent.gemini_actions._coerce_scheduled_actions, function:pocket_desk_agent.gemini_actions._execute_confirmed_action, function:pocket_desk_agent.gemini_actions._find_text_on_screen, function:pocket_desk_agent.gemini_actions._focus_window, function:pocket_desk_agent.gemini_actions._get_battery_status_text, function:pocket_desk_agent.gemini_actions._list_custom_commands_text, function:pocket_desk_agent.gemini_actions._list_open_windows, function:pocket_desk_agent.gemini_actions._list_schedules_text, function:pocket_desk_agent.gemini_actions._parse_schedule_time, function:pocket_desk_agent.gemini_actions._queue_confirmation, function:pocket_desk_agent.gemini_actions._read_clipboard_text, function:pocket_desk_agent.gemini_actions._run_handler_action, function:pocket_desk_agent.gemini_actions._run_saved_command, function:pocket_desk_agent.gemini_actions._scan_ui_elements, function:pocket_desk_agent.gemini_actions._shorten, function:pocket_desk_agent.gemini_actions._summarize_file_action, function:pocket_desk_agent.gemini_actions._summarize_scheduled_sequence, function:pocket_desk_agent.gemini_actions.dispatch_gemini_tool, function:pocket_desk_agent.gemini_actions.get_gemini_action_tools, function:pocket_desk_agent.gemini_actions.handle_gemini_confirmation_callback, function:pocket_desk_agent.gemini_actions.is_gemini_confirmation_callback, method:pocket_desk_agent.gemini_actions.GeminiToolResult.to_response, method:pocket_desk_agent.gemini_actions._MessageCollector.__init__, method:pocket_desk_agent.gemini_actions._MessageCollector.reply_photo, method:pocket_desk_agent.gemini_actions._MessageCollector.reply_text [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.gemini_cli_auth** — module:pocket_desk_agent.gemini_cli_auth, class:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.__init__, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._apply_tokens, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._configured_project_id, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._extract_project_id, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._fetch_user_info, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._load_code_assist_profile, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._request_headers, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._save_tokens, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth._update_status, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.build_authorization_url, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.ensure_code_assist_ready, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.ensure_valid_token, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.exchange_code, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.is_authenticated, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.load_saved_tokens, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.logout, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.refresh_access_token, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.start_callback_server, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.start_login_flow, method:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth.stop_callback_server [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.gemini_client** — module:pocket_desk_agent.gemini_client, class:pocket_desk_agent.gemini_client.GeminiClient, class:pocket_desk_agent.gemini_client.ResolvedModel, function:pocket_desk_agent.gemini_client._build_wrapped_body, function:pocket_desk_agent.gemini_client._build_wrapped_body_with_tools, function:pocket_desk_agent.gemini_client._candidate_model_names, function:pocket_desk_agent.gemini_client._get_api_tools, function:pocket_desk_agent.gemini_client._get_code_assist_endpoints, function:pocket_desk_agent.gemini_client._get_code_assist_headers, function:pocket_desk_agent.gemini_client._is_model_not_found_error, function:pocket_desk_agent.gemini_client._parse_full_response, function:pocket_desk_agent.gemini_client._trim_history, function:pocket_desk_agent.gemini_client.resolve_model, method:pocket_desk_agent.gemini_client.GeminiClient.__init__, method:pocket_desk_agent.gemini_client.GeminiClient._call_api_key_raw, method:pocket_desk_agent.gemini_client.GeminiClient._call_api_raw, method:pocket_desk_agent.gemini_client.GeminiClient._call_code_assist_raw, method:pocket_desk_agent.gemini_client.GeminiClient._get_project, method:pocket_desk_agent.gemini_client.GeminiClient._get_request_model_candidates, method:pocket_desk_agent.gemini_client.GeminiClient._get_request_token, method:pocket_desk_agent.gemini_client.GeminiClient._get_token, method:pocket_desk_agent.gemini_client.GeminiClient._request_with_model_fallbacks, method:pocket_desk_agent.gemini_client.GeminiClient._resolve_auth_context, method:pocket_desk_agent.gemini_client.GeminiClient.clear_session, method:pocket_desk_agent.gemini_client.GeminiClient.get_or_create_session, method:pocket_desk_agent.gemini_client.GeminiClient.send_message, method:pocket_desk_agent.gemini_client.GeminiClient.send_message_with_image, method:pocket_desk_agent.gemini_client.ResolvedModel.__init__ [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers._shared** — module:pocket_desk_agent.handlers._shared, function:pocket_desk_agent.handlers._shared.record_action_if_active, function:pocket_desk_agent.handlers._shared.safe_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.antigravity** — module:pocket_desk_agent.handlers.antigravity, function:pocket_desk_agent.handlers.antigravity._discover_candidate_folders, function:pocket_desk_agent.handlers.antigravity._find_vscode_window, function:pocket_desk_agent.handlers.antigravity._load_win_deps, function:pocket_desk_agent.handlers.antigravity._run_vscode_palette_command, function:pocket_desk_agent.handlers.antigravity.antigravitychat_command, function:pocket_desk_agent.handlers.antigravity.antigravityclaudecodeopen_command, function:pocket_desk_agent.handlers.antigravity.antigravitymode_command, function:pocket_desk_agent.handlers.antigravity.antigravitymodel_command, function:pocket_desk_agent.handlers.antigravity.antigravityopenfolder_command, function:pocket_desk_agent.handlers.antigravity.claudecli_command, function:pocket_desk_agent.handlers.antigravity.claudeclisend_command, function:pocket_desk_agent.handlers.antigravity.find_antigravity_window, function:pocket_desk_agent.handlers.antigravity.launch_browser, function:pocket_desk_agent.handlers.antigravity.launch_claude_cli, function:pocket_desk_agent.handlers.antigravity.open_folder_in_vscode, function:pocket_desk_agent.handlers.antigravity.openantigravity_command, function:pocket_desk_agent.handlers.antigravity.openbrowser_command, function:pocket_desk_agent.handlers.antigravity.openclaudeinvscode_command, function:pocket_desk_agent.handlers.antigravity.resolve_workspace_folder, function:pocket_desk_agent.handlers.antigravity.send_prompt_to_claude_cli [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.auth** — module:pocket_desk_agent.handlers.auth, function:pocket_desk_agent.handlers.auth._decode_auth_state, function:pocket_desk_agent.handlers.auth._do_logout, function:pocket_desk_agent.handlers.auth.authcode_command, function:pocket_desk_agent.handlers.auth.checkauth_command, function:pocket_desk_agent.handlers.auth.login_button_callback, function:pocket_desk_agent.handlers.auth.login_command, function:pocket_desk_agent.handlers.auth.logout_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.automation** — module:pocket_desk_agent.handlers.automation, function:pocket_desk_agent.handlers.automation.clickelement_command, function:pocket_desk_agent.handlers.automation.clicktext_command, function:pocket_desk_agent.handlers.automation.findelements_command, function:pocket_desk_agent.handlers.automation.findtext_command, function:pocket_desk_agent.handlers.automation.pasteenter_command, function:pocket_desk_agent.handlers.automation.scrolldown_command, function:pocket_desk_agent.handlers.automation.scrollup_command, function:pocket_desk_agent.handlers.automation.smartclick_command, function:pocket_desk_agent.handlers.automation.typeenter_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.build** — module:pocket_desk_agent.handlers.build, function:pocket_desk_agent.handlers.build._discover_android_repositories, function:pocket_desk_agent.handlers.build._discover_build_repositories, function:pocket_desk_agent.handlers.build._filter_build_scripts, function:pocket_desk_agent.handlers.build._format_apk_folder_contents, function:pocket_desk_agent.handlers.build._load_repo_scripts, function:pocket_desk_agent.handlers.build.build_command, function:pocket_desk_agent.handlers.build.capture_full_screen, function:pocket_desk_agent.handlers.build.capture_window_screenshot, function:pocket_desk_agent.handlers.build.check_apk_retrieval_selection, function:pocket_desk_agent.handlers.build.check_build_selection, function:pocket_desk_agent.handlers.build.execute_build_command, function:pocket_desk_agent.handlers.build.find_and_send_apk, function:pocket_desk_agent.handlers.build.getapk_command, function:pocket_desk_agent.handlers.build.monitor_build_window, function:pocket_desk_agent.handlers.build.prepare_apk_retrieval_workflow, function:pocket_desk_agent.handlers.build.prepare_build_workflow, function:pocket_desk_agent.handlers.build.send_apk_file, function:pocket_desk_agent.handlers.build.show_folder_contents, function:pocket_desk_agent.handlers.build.upload_large_file, function:pocket_desk_agent.handlers.build.upload_to_dropbox, function:pocket_desk_agent.handlers.build.upload_to_tempfile [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.callbacks** — module:pocket_desk_agent.handlers.callbacks, function:pocket_desk_agent.handlers.callbacks.button_callback, function:pocket_desk_agent.handlers.callbacks.delete_from_dropbox, function:pocket_desk_agent.handlers.callbacks.handle_dropbox_delete, function:pocket_desk_agent.handlers.callbacks.handle_upload_choice [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.claude** — module:pocket_desk_agent.handlers.claude, function:pocket_desk_agent.handlers.claude._load_win_deps, function:pocket_desk_agent.handlers.claude.capture_claude_screenshot, function:pocket_desk_agent.handlers.claude.check_repo_selection, function:pocket_desk_agent.handlers.claude.claudeask_command, function:pocket_desk_agent.handlers.claude.claudebranch_command, function:pocket_desk_agent.handlers.claude.claudechat_command, function:pocket_desk_agent.handlers.claude.claudelatest_command, function:pocket_desk_agent.handlers.claude.claudemode_command, function:pocket_desk_agent.handlers.claude.claudemodel_command, function:pocket_desk_agent.handlers.claude.claudenew_command, function:pocket_desk_agent.handlers.claude.clauderemote_command, function:pocket_desk_agent.handlers.claude.clauderepo_browse, function:pocket_desk_agent.handlers.claude.clauderepo_command, function:pocket_desk_agent.handlers.claude.clauderepo_list, function:pocket_desk_agent.handlers.claude.clauderepo_select_path, function:pocket_desk_agent.handlers.claude.claudescreen_command, function:pocket_desk_agent.handlers.claude.claudesearch_command, function:pocket_desk_agent.handlers.claude.claudeselect_command, function:pocket_desk_agent.handlers.claude.clear_claude_pid, function:pocket_desk_agent.handlers.claude.ensure_claude_open, function:pocket_desk_agent.handlers.claude.find_claude_window, function:pocket_desk_agent.handlers.claude.get_claude_process, function:pocket_desk_agent.handlers.claude.is_claude_running, function:pocket_desk_agent.handlers.claude.load_claude_pid, function:pocket_desk_agent.handlers.claude.openclaude_command, function:pocket_desk_agent.handlers.claude.save_claude_pid, function:pocket_desk_agent.handlers.claude.stopclaude_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.core** — module:pocket_desk_agent.handlers.core, function:pocket_desk_agent.handlers.core._get_gemini_auth_context, function:pocket_desk_agent.handlers.core.enhance_command, function:pocket_desk_agent.handlers.core.error_handler, function:pocket_desk_agent.handlers.core.get_bot_commands, function:pocket_desk_agent.handlers.core.handle_message, function:pocket_desk_agent.handlers.core.handle_photo, function:pocket_desk_agent.handlers.core.help_command, function:pocket_desk_agent.handlers.core.new_command, function:pocket_desk_agent.handlers.core.start_command, function:pocket_desk_agent.handlers.core.status_command, function:pocket_desk_agent.handlers.core.sync_commands_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.handlers.custom_commands** — module:pocket_desk_agent.handlers.custom_commands, function:pocket_desk_agent.handlers.custom_commands.cancelrecord_command, function:pocket_desk_agent.handlers.custom_commands.deletecommand_command, function:pocket_desk_agent.handlers.custom_commands.done_command, function:pocket_desk_agent.handlers.custom_commands.execute_custom_command, function:pocket_desk_agent.handlers.custom_commands.listcommands_command, function:pocket_desk_agent.handlers.custom_commands.savecommand_command [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.main** — module:pocket_desk_agent.main, function:pocket_desk_agent.main._process_is_running, function:pocket_desk_agent.main._should_enable_reloader, function:pocket_desk_agent.main._tesseract_available, function:pocket_desk_agent.main.acquire_lock, function:pocket_desk_agent.main.main, function:pocket_desk_agent.main.post_init, function:pocket_desk_agent.main.post_shutdown, function:pocket_desk_agent.main.scheduler_loop, function:pocket_desk_agent.main.start_reloader [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.rate_limiter** — module:pocket_desk_agent.rate_limiter, class:pocket_desk_agent.rate_limiter.RateLimiter, method:pocket_desk_agent.rate_limiter.RateLimiter.__init__, method:pocket_desk_agent.rate_limiter.RateLimiter.check, method:pocket_desk_agent.rate_limiter.RateLimiter.remaining, method:pocket_desk_agent.rate_limiter.RateLimiter.set_limit [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.scheduler_registry** — module:pocket_desk_agent.scheduler_registry, class:pocket_desk_agent.scheduler_registry.ScheduledTask, class:pocket_desk_agent.scheduler_registry.SchedulerRegistry, function:pocket_desk_agent.scheduler_registry.get_scheduler_registry, method:pocket_desk_agent.scheduler_registry.ScheduledTask.from_dict, method:pocket_desk_agent.scheduler_registry.ScheduledTask.to_dict, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.__init__, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.add_task, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.cleanup_old_tasks, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.delete_task, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.finalize_task_run, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.get_all_pending, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.get_pending_tasks, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.load, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.pop_task, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.save, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.update_task_metadata, method:pocket_desk_agent.scheduler_registry.SchedulerRegistry.update_task_status [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.scheduling_utils** — module:pocket_desk_agent.scheduling_utils, function:pocket_desk_agent.scheduling_utils.ensure_local_timezone, function:pocket_desk_agent.scheduling_utils.format_duration, function:pocket_desk_agent.scheduling_utils.format_eta, function:pocket_desk_agent.scheduling_utils.get_task_due_at, function:pocket_desk_agent.scheduling_utils.local_now, function:pocket_desk_agent.scheduling_utils.parse_duration_spec, function:pocket_desk_agent.scheduling_utils.parse_iso_datetime, function:pocket_desk_agent.scheduling_utils.parse_repeat_expression, function:pocket_desk_agent.scheduling_utils.parse_schedule_time [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.startup_manager** — module:pocket_desk_agent.startup_manager, class:pocket_desk_agent.startup_manager.StartupManager, class:pocket_desk_agent.startup_manager.StartupStatus, method:pocket_desk_agent.startup_manager.StartupManager.__init__, method:pocket_desk_agent.startup_manager.StartupManager._build_task_xml, method:pocket_desk_agent.startup_manager.StartupManager._combined_output, method:pocket_desk_agent.startup_manager.StartupManager._default_runner, method:pocket_desk_agent.startup_manager.StartupManager._get_current_user, method:pocket_desk_agent.startup_manager.StartupManager._parse_task_xml, method:pocket_desk_agent.startup_manager.StartupManager._resolve_python_command, method:pocket_desk_agent.startup_manager.StartupManager._run_schtasks, method:pocket_desk_agent.startup_manager.StartupManager._schtasks_available, method:pocket_desk_agent.startup_manager.StartupManager._task_missing, method:pocket_desk_agent.startup_manager.StartupManager._validate_task_configuration, method:pocket_desk_agent.startup_manager.StartupManager._working_dir, method:pocket_desk_agent.startup_manager.StartupManager._xml_escape, method:pocket_desk_agent.startup_manager.StartupManager.configure_interactive, method:pocket_desk_agent.startup_manager.StartupManager.disable_startup, method:pocket_desk_agent.startup_manager.StartupManager.enable_startup, method:pocket_desk_agent.startup_manager.StartupManager.get_status, method:pocket_desk_agent.startup_manager.StartupManager.is_supported [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.updater** — module:pocket_desk_agent.updater, class:pocket_desk_agent.updater.UpdateInfo, function:pocket_desk_agent.updater._is_git_repo, function:pocket_desk_agent.updater._parse_version, function:pocket_desk_agent.updater._run_git, function:pocket_desk_agent.updater.apply_update, function:pocket_desk_agent.updater.check_for_updates, function:pocket_desk_agent.updater.check_pypi_version, function:pocket_desk_agent.updater.format_update_notification, function:pocket_desk_agent.updater.get_last_check, function:pocket_desk_agent.updater.get_local_commit_date, function:pocket_desk_agent.updater.get_local_sha, function:pocket_desk_agent.updater.get_local_short_sha, function:pocket_desk_agent.updater.get_version_string, function:pocket_desk_agent.updater.startup_update_check, function:pocket_desk_agent.updater.update_checker_loop [INFERRED]
- **hyperedge:module_scope:pocket_desk_agent.window_utils** — module:pocket_desk_agent.window_utils, class:pocket_desk_agent.window_utils.WindowInfo, function:pocket_desk_agent.window_utils._activate_window_with_pygetwindow, function:pocket_desk_agent.window_utils._is_switchable_window, function:pocket_desk_agent.window_utils._nudge_foreground_lock, function:pocket_desk_agent.window_utils._window_handle, function:pocket_desk_agent.window_utils.activate_window, function:pocket_desk_agent.window_utils.build_window_inventory, function:pocket_desk_agent.window_utils.format_window_inventory, function:pocket_desk_agent.window_utils.list_open_windows [INFERRED]
- **Remote Session Streaming Stack** — module:pocket_desk_agent.handlers.remote, module:pocket_desk_agent.remote.session, module:pocket_desk_agent.remote.web_server, module:pocket_desk_agent.remote.capture, module:pocket_desk_agent.remote.input_bridge, module:pocket_desk_agent.remote.tunnel [INFERRED 0.93]
- **Scheduled Task Execution Flow** — module:pocket_desk_agent.handlers.scheduling, symbol:pocket_desk_agent.handlers.scheduling.execute_scheduled_task, symbol:pocket_desk_agent.handlers.scheduling._execute_screen_watch, symbol:pocket_desk_agent.handlers.scheduling._execute_permission_watch, symbol:pocket_desk_agent.handlers.scheduling._execute_scheduled_claude_prompt [INFERRED 0.90]
- **Desktop Control Command Group** — module:pocket_desk_agent.handlers.system, symbol:pocket_desk_agent.handlers.system.hotkey_command, symbol:pocket_desk_agent.handlers.system.windows_command, symbol:pocket_desk_agent.handlers.system.focuswindow_command, symbol:pocket_desk_agent.handlers.system.privacy_command [INFERRED 0.87]
- **facial_features_group** — left_eye, right_eye, mouth, brow_hairline [INFERRED 0.96]
- **foreground_on_head** — head, left_eye, right_eye, mouth, brow_hairline [INFERRED 0.94]
- **face_group** — shape.left_eye, shape.right_eye, shape.mouth_arc, shape.brow_hair_arc [INFERRED 0.95]
- **Facial features** — shape.left_eye, shape.right_eye, shape.mouth_arc, shape.brow_hairline_arc [INFERRED 0.96]
- **Foreground layered on background** — shape.background, shape.left_eye, shape.right_eye, shape.mouth_arc, shape.brow_hairline_arc [INFERRED 0.95]

## Communities (185 total, 60 thin omitted)

### Community 0 - "pocket_desk_agent.handlers.system"
Cohesion: 0.11
Nodes (37): ctypes, platform, pocket_desk_agent.automation_utils.map_keys_to_pyautogui, pocket_desk_agent.automation_utils.press_key, pocket_desk_agent.automation_utils.send_hotkey, pocket_desk_agent.automation_utils.typewrite_text, pocket_desk_agent.automation_utils.write_text, pocket_desk_agent.handlers._shared.PYWINAUTO_AVAILABLE (+29 more)

### Community 1 - "RuntimeError"
Cohesion: 0.09
Nodes (30): _find_claude_window(), capture_claude_screenshot(), claudescreen_command(), _click_claude_input(), _configure_tesseract(), find_claude_window(), _load_win_deps(), openclaude_command() (+22 more)

### Community 2 - "scripts.manage_auth"
Cohesion: 0.27
Nodes (10): pathlib, pathlib.Path, pocket_desk_agent.antigravity_auth.AntigravityOAuth, pocket_desk_agent.config.Config, pocket_desk_agent.constants.AUTH_MODE_APIKEY, pocket_desk_agent.constants.AUTH_MODE_GEMINI_CLI, pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth, scripts.manage_auth (+2 more)

### Community 3 - "pocket_desk_agent.handlers.build"
Cohesion: 0.06
Nodes (62): asyncio, dropbox, dropbox.exceptions, functools, importlib.util, logging, os, platform (+54 more)

### Community 4 - "pocket_desk_agent.command_map"
Cohesion: 0.04
Nodes (45): /antigravitymodel, /cancelschedule, /cat, /claudeask, /claudebranch, /claudenew, /claudescreen, /claudesearch (+37 more)

### Community 5 - "pocket_desk_agent.handlers.scheduling"
Cohesion: 0.08
Nodes (52): datetime, os, pocket_desk_agent.automation_utils.find_text_in_image, pocket_desk_agent.command_registry.get_registry, pocket_desk_agent.handlers._shared.RECORDING_TIMEOUT_SECS, pocket_desk_agent.handlers._shared.recording_sessions, pocket_desk_agent.handlers.antigravity.find_antigravity_window, pocket_desk_agent.handlers.claude.ensure_claude_open (+44 more)

### Community 6 - "plugins.caveman.skills.compress.scripts.compress"
Cohesion: 0.06
Nodes (37): Anthropic, FileNotFoundError, RuntimeError, ValueError, any, compile, create, exists (+29 more)

### Community 7 - "scheduling.py"
Cohesion: 0.05
Nodes (85): _list_schedules_text(), Return the current user's pending schedules., _activate_window(), cancelschedule_command(), claudeschedule_command(), cleanup_scheduled_task_artifacts(), describe_task(), _execute_permission_watch() (+77 more)

### Community 8 - "pocket_desk_agent.remote.session"
Cohesion: 0.08
Nodes (43): PIL, PIL.Image, __future__, __future__.annotations, dataclasses, dataclasses.dataclass, dataclasses.field, logging (+35 more)

### Community 9 - "pocket_desk_agent.automation_utils"
Cohesion: 0.09
Nodes (27): RuntimeError, action, bool, getLogger, getattr, hotkey, join, match (+19 more)

### Community 10 - "docs/REMOTE.md"
Cohesion: 0.04
Nodes (48): /abcd, /developers, /ws, /ws/input, /ws/video, "", (User-Agent, sha256(remote IP)), *.cloudflare.com (+40 more)

### Community 11 - "_stop_via_pidfile"
Cohesion: 0.17
Nodes (16): bot_main, existing_app_path, exists, has_config, int, kill, read_text, run_configure_wizard (+8 more)

### Community 12 - "pocket_desk_agent.configure"
Cohesion: 0.06
Nodes (84): AntigravityOAuth, ConfigParser, GeminiCLIOAuth, Path, StartupManager, app_path, app_path_candidates, append (+76 more)

### Community 13 - "AntigravityOAuth"
Cohesion: 0.22
Nodes (22): bool, get, isinstance, json, on_status_update, post, server_close, str (+14 more)

### Community 14 - "gemini_actions.py"
Cohesion: 0.04
Nodes (79): map_keys_to_pyautogui(), press_key(), Map a hotkey string (e.g., 'ctrl+c') to a list of pyautogui key names. Args:…, Run a keyboard-only PyAutoGUI action with a lock-screen-friendly fallback.…, Type text via PyAutoGUI with a safe fail-safe retry for lock screens., Press a key via PyAutoGUI with a safe fail-safe retry for lock screens., Send a hotkey via PyAutoGUI with a safe fail-safe retry for lock screens., _run_keyboard_only_action() (+71 more)

### Community 15 - "README.md"
Cohesion: 0.06
Nodes (43): Multi-mode Authentication, React Native APK Build Workflow, Claude and Antigravity Integration, Central Command Registry, Telegram Command Surface, Config.load Class Pattern, Runtime Dependency Stack, Large APK Upload via Dropbox (+35 more)

### Community 16 - "system.py"
Cohesion: 0.05
Nodes (66): get_media_group_file_ids(), _prune_media_groups(), Shared state, clients, and utilities for all handler modules., Return ordered file_ids for a recently seen Telegram media group., Record one photo message that belongs to a Telegram media group., register_media_group_item(), battery_command(), _build_app_picker_keyboard() (+58 more)

### Community 17 - "compress/SKILL.md"
Cohesion: 0.05
Nodes (41): CLAUDE.md, FILE.original.md, SKILL.md, config.yaml, directory_containing_this_SKILL.md, original.md, /caveman:compress <filepath>, /config (+33 more)

### Community 18 - "core.py"
Cohesion: 0.06
Nodes (63): Application, Return True if the Tesseract binary is installed and reachable., _tesseract_available(), Centralized command registry for the bot., enhance_command(), error_handler(), get_bot_commands(), _get_gemini_auth_context() (+55 more)

### Community 19 - "GeminiCLIOAuth"
Cohesion: 0.08
Nodes (46): GeminiCLIOAuth, GeminiClient, http.server.HTTPServer, pocket_desk_agent.antigravity_auth.AntigravityOAuth, pocket_desk_agent.antigravity_auth.TokenStorage, urllib.parse.urlencode, _candidate_model_names, _get_code_assist_endpoints (+38 more)

### Community 20 - "StartupManager"
Cohesion: 0.14
Nodes (37): FileManager, StartupManager, pathlib.Path, pocket_desk_agent.app_paths.app_dir, __init__, _format_size, _is_safe_path, append_file (+29 more)

### Community 21 - "AntigravityAuth"
Cohesion: 0.15
Nodes (23): AntigravityOAuth, GeminiCLIOAuth, append, bool, get, getattr, info, isinstance (+15 more)

### Community 22 - "configure.py"
Cohesion: 0.06
Nodes (62): ConfigParser, _load_config_files(), Load config values from canonical and legacy app directories., _auto_oauth_login(), config_path(), config_path_candidates(), _configure_windows_startup(), credentials_path() (+54 more)

### Community 23 - "find_text_in_image"
Cohesion: 0.06
Nodes (60): Image, annotate_screenshot_with_markers(), _build_ocr_passes(), _build_phrase_candidates(), _candidate_overlap(), _compact_ocr_text(), _configure_tesseract(), _dedupe_scored_matches() (+52 more)

### Community 24 - "Caveman"
Cohesion: 0.62
Nodes (7): Caveman, Rounded square background, Brow or hairline arc, Brow or hairline arc, Left eye, Mouth arc, Right eye

### Community 25 - "pocket_desk_agent.gemini_actions"
Cohesion: 0.06
Nodes (55): GeminiToolResult, PendingGeminiAction, _MessageCollector, ScheduledTask, pocket_desk_agent.remote.session, types, dataclasses.asdict, pocket_desk_agent.automation_utils.map_keys_to_pyautogui (+47 more)

### Community 26 - "Caveman icon"
Cohesion: 0.67
Nodes (6): brow or hairline, head, left eye, mouth, right eye, Caveman icon

### Community 27 - "handlers/__init__.py"
Cohesion: 0.08
Nodes (51): Validate that a command name contains only alphanumeric characters and…, validate_command_name(), activate_adapter_window(), DesktopAdapter, find_adapter_window(), get_desktop_adapter(), list_desktop_adapters(), Desktop app adapter helpers for UI automation features. This module centralizes… (+43 more)

### Community 28 - "build.py"
Cohesion: 0.07
Nodes (46): _android_outputs_base(), build_command(), _build_large_file_upload_markup(), capture_window_screenshot(), check_apk_retrieval_selection(), check_build_selection(), clear_build_monitor_requests_for_user(), create_build_monitor_request() (+38 more)

### Community 29 - "docs/MOBILE_AUTHENTICATION.md"
Cohesion: 0.05
Nodes (43): AUTHENTICATION_REQUIREMENTS.md, config/antigravity-chatbot/tokens.json, config/pdagent-gemini/tokens.json, /accounts, /authcode, /authcode <code_or_callback_url>, /checkauth, /enhance (+35 more)

### Community 30 - "pocket_desk_agent/cli.py"
Cohesion: 0.08
Nodes (43): _auth(), _auto_configure(), _configure(), _ensure_tesseract(), main(), Command-line entry point for Pocket Desk Agent. Installed as the `pdagent`…, Auto-trigger the setup wizard and system dependency check on first run., Run the interactive configuration wizard. (+35 more)

### Community 32 - "StartupManager"
Cohesion: 0.09
Nodes (23): CompletedProcess, Path, Create or update the autorun task., Remove the autorun task., Interactively enable or disable autorun., Build the Task Scheduler XML definition., Escape values inserted into Task Scheduler XML., Represents the current autorun configuration state. (+15 more)

### Community 33 - "AntigravityOAuth"
Cohesion: 0.07
Nodes (21): AntigravityOAuth, get_oauth_client_id(), get_oauth_client_secret(), Handles OAuth flow for Antigravity/Google authentication, Update status callback, Encode state parameter with verifier and project ID, Build the OAuth authorization URL with PKCE, Start local HTTP server to receive OAuth callback (+13 more)

### Community 34 - "Config"
Cohesion: 0.07
Nodes (32): is_user_allowed(), Update, Authentication module with multi-provider support. Supports three…, Check if user is in allowed list., Config, _env_int(), _parse_user_ids(), Path (+24 more)

### Community 35 - "GeminiCLIOAuth"
Cohesion: 0.08
Nodes (17): PKCEGenerator, Generates PKCE code verifier and challenge, Generate PKCE verifier and challenge, GeminiCLIOAuth, get_gemini_cli_client_id(), get_gemini_cli_client_secret(), Any, Initialize project selection for the Code Assist backend. Returns True on… (+9 more)

### Community 36 - "FileManager"
Cohesion: 0.11
Nodes (18): FileManager, Path, List contents of directory., Manages file system access within approved directory., Read contents of a file., Search for files matching pattern., Get information about a file or directory., Write content to a file (creates or overwrites). (+10 more)

### Community 37 - "filesystem.py"
Cohesion: 0.11
Nodes (34): apply_approved_dirs(), approvedirs_command(), approvedirs_list_text(), cat_command(), cd_command(), check_getfile_selection(), find_command(), _format_blocked_file_message() (+26 more)

### Community 38 - "plugins.caveman.skills.compress.scripts.validate"
Cohesion: 0.11
Nodes (33): Path, abs, append, compile, exit, findall, group, join (+25 more)

### Community 39 - "pocket_desk_agent.config"
Cohesion: 0.06
Nodes (33): ALLOWED_USERS, ANTIGRAVITY_ENABLED, ANTIGRAVITY_MODEL, ANTIGRAVITY_PROJECT_ID, APPROVED_DIRECTORIES, APPROVED_DIRECTORY, AUTHORIZED_USER_IDS, AUTO_UPDATE_CHECK (+25 more)

### Community 40 - "callbacks.py"
Cohesion: 0.08
Nodes (33): handle_gemini_confirmation_callback(), is_gemini_confirmation_callback(), Return True when the callback belongs to the Gemini confirmation flow., Execute or cancel a pending Gemini action from an inline keyboard callback., launch_claude_cli(), Open Claude CLI in a folder and optionally send an initial prompt., _do_logout(), login_button_callback() (+25 more)

### Community 41 - "antigravity.py"
Cohesion: 0.10
Nodes (32): _find_antigravity_window(), antigravityopenfolder_command(), claudecli_command(), claudeclisend_command(), _discover_candidate_folders(), find_antigravity_window(), _find_vscode_window(), launch_browser() (+24 more)

### Community 44 - "remote.py"
Cohesion: 0.10
Nodes (31): handle_install_cloudflared_callback(), _idle_watchdog(), _is_missing_cloudflared_message(), _prompt_cloudflared_install(), DEFAULT_TYPE, Update, Telegram handlers for the live remote-desktop feature. Exposes: *…, Safe status dict for the Gemini ``get_remote_session_status`` tool. Never… (+23 more)

### Community 45 - "pocket_desk_agent.gemini_client"
Cohesion: 0.10
Nodes (32): ResolvedModel, base64, http.server, json, pathlib, pocket_desk_agent.antigravity_auth, pocket_desk_agent.config, requests (+24 more)

### Community 46 - "pocket_desk_agent.antigravity_auth"
Cohesion: 0.08
Nodes (27): Event, getLogger, getLogger, app_path, getLogger, pocket_desk_agent.antigravity_auth, pocket_desk_agent.auth, pocket_desk_agent.command_registry (+19 more)

### Community 47 - "gemini_client.py"
Cohesion: 0.11
Nodes (28): get_gemini_action_tools(), Return additional Gemini tool declarations for desktop actions., _as_bool(), _as_int(), _build_wrapped_body(), _build_wrapped_body_with_tools(), _candidate_model_names(), _first_string() (+20 more)

### Community 48 - "pocket_desk_agent.scheduling_utils"
Cohesion: 0.14
Nodes (28): SchedulerRegistry, re, pocket_desk_agent.app_paths.existing_app_path, pocket_desk_agent.handlers.scheduling.describe_task, _list_schedules_text, get_scheduler_registry, ensure_local_timezone, format_duration (+20 more)

### Community 49 - "pocket_desk_agent.updater"
Cohesion: 0.13
Nodes (28): StartupStatus, UpdateInfo, __future__, dataclasses, datetime, pocket_desk_agent, pocket_desk_agent.app_paths, shutil (+20 more)

### Community 50 - "pocket_desk_agent.main"
Cohesion: 0.09
Nodes (28): atexit, pocket_desk_agent.cli, pocket_desk_agent.command_map, pocket_desk_agent.handlers, psutil, threading, wakepy, pocket_desk_agent.cli._tesseract_available (+20 more)

### Community 51 - "pocket_desk_agent.handlers.claude"
Cohesion: 0.16
Nodes (28): _load_win_deps, capture_claude_screenshot, check_repo_selection, claudeask_command, claudebranch_command, claudechat_command, claudelatest_command, claudemode_command (+20 more)

### Community 52 - "updater.py"
Cohesion: 0.09
Nodes (27): apply_update(), check_for_updates(), format_update_notification(), get_last_check(), get_local_commit_date(), get_local_sha(), get_local_short_sha(), _is_git_repo() (+19 more)

### Community 53 - "GeminiClient"
Cohesion: 0.14
Nodes (17): AbstractEventLoop, OAuthProvider, GeminiClient, _is_auth_error(), _is_model_not_found_error(), _parse_full_response(), Send a message with an image to Gemini for vision analysis., Return True when the backend rejected the requested model lookup. (+9 more)

### Community 54 - "docs/dropbox-setup.md"
Cohesion: 0.07
Nodes (26): /www, .env, AuthError, bot.log, Dropbox, files.content.read, files.content.write, missing_scope (+18 more)

### Community 55 - "plugins.caveman.skills.compress.scripts.benchmark"
Cohesion: 0.10
Nodes (25): Path, append, encode, exists, exit, get_encoding, glob, insert (+17 more)

### Community 56 - "existing_app_path"
Cohesion: 0.13
Nodes (20): Antigravity OAuth authentication implementation., app_dir(), app_path(), app_path_candidates(), ensure_app_dir(), existing_app_path(), legacy_app_dirs(), Path (+12 more)

### Community 57 - "plugins.caveman.skills.compress.scripts.detect"
Cohesion: 0.10
Nodes (24): Path, any, compile, endswith, exit, is_file, len, loads (+16 more)

### Community 58 - "smart_plug.py"
Cohesion: 0.13
Nodes (24): autobattery_command(), _battery_manager_loop(), _get_or_create_plug(), _get_plug_credentials(), Any, DEFAULT_TYPE, Update, Smart plug and auto battery management command handlers. Commands: /autobattery… (+16 more)

### Community 59 - "RemoteSession"
Cohesion: 0.17
Nodes (21): RemoteSession, _authorize_ws(), build_app(), _client_ip(), _cookie_token(), _fingerprint(), _handle_healthz(), _handle_root() (+13 more)

### Community 60 - "load"
Cohesion: 0.14
Nodes (23): cls, dump, error, existing_app_path, exists, info, items, len (+15 more)

### Community 61 - "tunnel.py"
Cohesion: 0.15
Nodes (22): _discover_binary(), _line_has_ready_signal(), Cloudflared quick-tunnel supervisor. Spawns ``cloudflared tunnel --url…, Spawn the cloudflared subprocess for a local HTTP target., Return True when a cloudflared output line indicates edge readiness., Read and decode one cloudflared output line with timeout. Returns: - ``None``…, Read cloudflared output until URL is found, then wait briefly for readiness., Drain cloudflared stdout in the background after URL capture. (+14 more)

### Community 62 - "pocket_desk_agent.remote.web_server"
Cohesion: 0.16
Nodes (22): aiohttp, aiohttp.WSMsgType, aiohttp.web, hashlib, json, pocket_desk_agent.remote.capture.frame_iter, pocket_desk_agent.remote.input_bridge.InputDispatcher, pocket_desk_agent.remote.web_server (+14 more)

### Community 63 - "save_tokens"
Cohesion: 0.10
Nodes (21): app_path, chmod, dump, ensure_app_dir, exists, getenv, home, load (+13 more)

### Community 64 - "pocket_desk_agent.handlers.remote"
Cohesion: 0.19
Nodes (21): asyncio, io, pocket_desk_agent.handlers._shared.safe_command, pocket_desk_agent.handlers.remote, pocket_desk_agent.remote, pocket_desk_agent.remote.session.ACTIVE_SESSIONS, pocket_desk_agent.remote.session.RemoteSession, pocket_desk_agent.remote.session.get_for_user (+13 more)

### Community 65 - "app_control.py"
Cohesion: 0.15
Nodes (20): normalize_app_name(), Collapse punctuation and spacing into a stable lookup key., _candidate_names(), close_desktop_app(), _close_window_handle(), CloseAppResult, _find_matching_process_ids(), _find_matching_window_handles() (+12 more)

### Community 66 - "main"
Cohesion: 0.11
Nodes (18): main, Path, compress_file, detect_file_type, exists, exit, is_file, len (+10 more)

### Community 67 - "load"
Cohesion: 0.11
Nodes (20): Path, ValueError, append, expanduser, expandvars, getenv, home, int (+12 more)

### Community 68 - "pocket_desk_agent.handlers.antigravity"
Cohesion: 0.16
Nodes (20): PIL, pocket_desk_agent.automation_utils, pytesseract, pywinauto, pywinauto.keyboard, pocket_desk_agent.automation_utils.find_text_in_image, _find_vscode_window, _load_win_deps (+12 more)

### Community 69 - "AntigravityAuth"
Cohesion: 0.15
Nodes (11): OAuthInstance, AntigravityAuth, Return the active auth mode for a user., Check if user is authenticated., Get authenticated user info., Logout user and clear tokens for all OAuth modes., Handles authentication for multiple users. Despite the legacy name, this class…, Create a fresh OAuth instance for the requested provider. (+3 more)

### Community 70 - "do_GET"
Cohesion: 0.11
Nodes (19): HTTPServer, Thread, clear, end_headers, handle_request, is_set, parse_qs, send_header (+11 more)

### Community 71 - "SchedulerRegistry"
Cohesion: 0.15
Nodes (9): Return all pending tasks, including future runs., Update the status of a task., Replace the stored metadata for one task., Delete and return a task by ID., Remove completed or failed tasks older than ``days``., Manages persistent storage of scheduled tasks., Load scheduled tasks from disk., Save scheduled tasks to disk. (+1 more)

### Community 72 - "generate"
Cohesion: 0.14
Nodes (18): decode, digest, dumps, encode, join, len, loads, rstrip (+10 more)

### Community 73 - "find_text_in_image"
Cohesion: 0.19
Nodes (18): SequenceMatcher, lower, max, range, ratio, set, setdefault, split (+10 more)

### Community 74 - "caveman/SKILL.md"
Cohesion: 0.11
Nodes (17): /caveman, /caveman lite|full|ultra, <, <=, [thing] [action] [reason]. [next step]., useMemo, users, ACTIVE (+9 more)

### Community 75 - "pocket_desk_agent.handlers.automation"
Cohesion: 0.18
Nodes (18): io, pocket_desk_agent.automation_utils.annotate_screenshot_with_markers, pocket_desk_agent.automation_utils.find_ui_elements, pocket_desk_agent.automation_utils.press_key, pocket_desk_agent.command_registry.CommandAction, _coerce_scheduled_actions, _scan_ui_elements, record_action_if_active (+10 more)

### Community 76 - "app_catalog.py"
Cohesion: 0.16
Nodes (17): _build_start_menu_app_id(), _derive_process_hints(), _discover_start_menu_entries(), is_safe_launch_target(), _is_safe_resolved_launch_target(), Catalog and query helpers for launchable desktop applications., Resolve the target path from a ``.lnk`` shortcut file on Windows., Discover launchable app shortcuts from common Start Menu locations. (+9 more)

### Community 77 - "find_ui_elements"
Cohesion: 0.13
Nodes (16): ImportError, apply, array, boundingRect, contourArea, convert, createCLAHE, cvtColor (+8 more)

### Community 78 - "CommandRegistry"
Cohesion: 0.15
Nodes (9): CommandRegistry, Add or update a command in the registry. Args: name: Command name actions: List…, Delete a command from the registry. Args: name: Command name Returns: True if…, Get a list of all command names with their action counts. Returns: Dictionary…, Check if a command exists in the registry. Args: name: Command name Returns:…, Manages persistent storage of custom commands., Initialize the command registry., Load command registry from disk. Returns: True if loaded successfully, False… (+1 more)

### Community 79 - "QuboClient"
Cohesion: 0.16
Nodes (9): Any, QuboClient, Build the MQTT topic for this device., Called by paho-mqtt network thread when MQTT connection is established. Uses…, Called by paho-mqtt network thread when MQTT connection is lost. Uses…, Parse incoming Qubo state-change MQTT messages. Called from paho network…, Turn the smart plug on (on=True) or off (on=False). Waits up to…, Return current plug connection/state information. (+1 more)

### Community 80 - "RecipeRegistry"
Cohesion: 0.22
Nodes (4): Persistent recipe definition., Persistent storage manager for workflow recipes., RecipeDefinition, RecipeRegistry

### Community 81 - "list_open_windows"
Cohesion: 0.18
Nodes (15): _activate_window_with_pygetwindow(), build_window_inventory(), _is_switchable_window(), list_open_windows(), _nudge_foreground_lock(), Helpers for listing and activating desktop windows on Windows., Best-effort extraction of a platform window handle., Filter out shell/tool windows that should not be shown to the user. (+7 more)

### Community 82 - "Mobile Authentication Guide"
Cohesion: 0.13
Nodes (14): `/authcode <code_or_callback_url>`, `/checkauth`, Commands, Example Flow, How It Works, `/login`, `/logout`, Mobile Authentication Guide (+6 more)

### Community 83 - "pocket_desk_agent.app_paths"
Cohesion: 0.23
Nodes (13): exists, home, joinpath, mkdir, tuple, pocket_desk_agent.app_paths, __future__, app_dir (+5 more)

### Community 84 - "get_windows_input_desktop_name"
Cohesion: 0.14
Nodes (14): CloseDesktop, GetUserObjectInformationW, OpenInputDesktop, byref, c_uint, create_unicode_buffer, debug, exists (+6 more)

### Community 85 - "pocket_desk_agent.cli"
Cohesion: 0.15
Nodes (13): SystemExit, stop_bot, pocket_desk_agent.cli, argparse, pocket_desk_agent.main, pocket_desk_agent.startup_manager, pocket_desk_agent.updater, pytesseract (+5 more)

### Community 86 - "pocket_desk_agent.window_utils"
Cohesion: 0.24
Nodes (14): WindowInfo, ctypes, pygetwindow, _focus_window, _list_open_windows, _activate_window_with_pygetwindow, _is_switchable_window, _nudge_foreground_lock (+6 more)

### Community 87 - "Dropbox Setup Guide"
Cohesion: 0.14
Nodes (13): 1. Create a Dropbox App, 2. Grant Required Permissions, 3. Generate an Access Token, 4. Add the Token to Pocket Desk Agent, "Dropbox not configured", Dropbox Setup Guide, "Invalid Dropbox access token", `missing_scope` or `AuthError` (+5 more)

### Community 88 - "telegram.InlineKeyboardButton"
Cohesion: 0.25
Nodes (14): pocket_desk_agent.automation_utils.validate_command_name, telegram.InlineKeyboardButton, telegram.InlineKeyboardMarkup, _discover_candidate_folders, antigravityopenfolder_command, claudecli_command, openbrowser_command, login_command (+6 more)

### Community 89 - "InputDispatcher"
Cohesion: 0.22
Nodes (6): InputDispatcher, Any, Translate remote browser events into pyautogui input on the host. Events are…, Current host cursor position normalized to 0..1, or None if unavailable. The…, Per-session input dispatcher with rate limit and fail-safe tracking., Apply a single event. Returns an optional status string.

### Community 90 - "Smart Plug & Auto Battery Management"
Cohesion: 0.15
Nodes (12): 1. Get your Qubo credentials, 2. Add credentials to `~/.pdagent/config`, 3. (Optional) Override thresholds via environment, Auto-Resume on Bot Restart, `/autobattery` — Auto battery manager, Commands, Hardware Compatibility, How It Works (+4 more)

### Community 91 - "start_remote_session"
Cohesion: 0.15
Nodes (12): _build_qr_png(), _build_viewer_url(), _has_viewer_token(), _pick_free_port(), Return True if an existing session still has a live tunnel process., Ask the OS for a free localhost port. Small race is acceptable., Render a PNG QR code for ``url``. Returns None on any failure., Create and fully wire up a remote session for ``user_id``. Returns ``(success,… (+4 more)

### Community 92 - ".refresh_token_if_needed"
Cohesion: 0.23
Nodes (9): DeviceInfo, _pick(), Qubo smart plug MQTT client. This module embeds the full async Qubo client…, Authenticate with Qubo cloud and store tokens., Refresh access token when it is close to expiry., Discover the target device from the Qubo cloud device list., Return the first non-None value from dict *obj* matching any of *keys*., Unwrap common Qubo response envelope wrappers. (+1 more)

### Community 93 - "manage_service.py"
Cohesion: 0.27
Nodes (12): check_status(), _current_pid_file(), is_running(), Process management utility for Pocket Desk Agent. Handles stopping and status…, Check if process is running on Windows., Return the canonical PID file, falling back to the legacy location., Terminate the bot process., Check and print bot status. (+4 more)

### Community 94 - "_extract_ocr_words"
Cohesion: 0.26
Nodes (12): enumerate, float, get, image_to_data, int, len, replace, strip (+4 more)

### Community 95 - "print"
Cohesion: 0.20
Nodes (12): StartupManager, check_for_updates, configure_interactive, disable_startup, enable_startup, get_status, print, _startup_configure (+4 more)

### Community 96 - "Live Remote Desktop (`/remote`)"
Cohesion: 0.17
Nodes (11): Configuration reference, How to disable, Known limitations (v1), Live Remote Desktop (`/remote`), Mobile UX guide, Prerequisites, Quick start, Resource profile (+3 more)

### Community 97 - "pocket_desk_agent.handlers.filesystem"
Cohesion: 0.26
Nodes (12): pocket_desk_agent.handlers._shared.file_manager, pocket_desk_agent.handlers.filesystem, telegram, telegram.Update, telegram.ext, telegram.ext.ContextTypes, cat_command, cd_command (+4 more)

### Community 98 - "DesktopAppEntry"
Cohesion: 0.21
Nodes (12): build_builtin_app_catalog(), _dedupe_catalog(), DesktopAppEntry, discover_desktop_apps(), _first_existing_path(), get_app_entry_by_id(), Return the curated built-in safe app catalog., Normalized description of one launchable desktop app. (+4 more)

### Community 99 - "._call_api_raw"
Cohesion: 0.23
Nodes (9): _get_code_assist_endpoints(), _get_code_assist_headers(), Call Google's internal Code Assist backend for OAuth auth modes., Call the standard Gemini API using an API key (fallback mode)., Build headers for the shared internal Code Assist backend., Return the stable endpoint order for the Code Assist backend., Seconds to wait before retrying a 429 response. Respects Retry-After., _retry_wait() (+1 more)

### Community 100 - "done_command"
Cohesion: 0.23
Nodes (12): cancelrecord_command(), deletecommand_command(), done_command(), listcommands_command(), DEFAULT_TYPE, Update, Handle /savecommand command - start recording a custom command., Handle /cancelrecord command - cancel recording session. (+4 more)

### Community 101 - "RateLimiter"
Cohesion: 0.17
Nodes (7): RateLimiter, Per-user, per-command rate limiter. Prevents abuse by limiting how frequently…, Token-bucket style rate limiter keyed by (user_id, command)., Args: default_calls: Max invocations per window (default: 10). default_window:…, Override the rate limit for a specific command., Return True if the request is allowed, False if rate-limited. Automatically…, Return how many calls remain in the current window.

### Community 102 - "annotate_screenshot_with_markers"
Cohesion: 0.20
Nodes (10): Draw, copy, info, load_default, rectangle, str, text, textbbox (+2 more)

### Community 103 - "_run_background"
Cohesion: 0.20
Nodes (10): Popen, app_path, decode, dict, encode, ensure_app_dir, getattr, open (+2 more)

### Community 104 - "scripts.manage_service"
Cohesion: 0.51
Nodes (10): pocket_desk_agent.app_paths.app_path, pocket_desk_agent.app_paths.existing_app_path, scripts.manage_service, subprocess, _current_pid_file, check_status, is_running, restart_bot (+2 more)

### Community 105 - "OAuthCallbackHandler"
Cohesion: 0.22
Nodes (6): BaseHTTPRequestHandler, OAuthCallbackHandler, HTTP handler for OAuth callback. Class-level state is used because HTTPServer…, Clear state for a new login flow., Suppress HTTP server logs, Handle GET request for OAuth callback

### Community 106 - "TokenStorage"
Cohesion: 0.22
Nodes (4): Manages token storage and retrieval, Save tokens to file with restricted permissions., Load tokens from file, TokenStorage

### Community 107 - "winget_install_cloudflared"
Cohesion: 0.28
Nodes (8): _hydrate_cloudflared_path_from_installs(), Try to discover an existing cloudflared install and cache it in Config., find_installed_binary(), Helpers to auto-install the cloudflared binary on Windows via winget. Used by…, Probe known install locations for cloudflared.exe. Needed after a fresh…, Run ``winget install Cloudflare.cloudflared`` and return (ok, msg). Sets…, winget_available(), winget_install_cloudflared()

### Community 108 - "capture.py"
Cohesion: 0.25
Nodes (6): frame_iter(), _pil_from_screen(), JPEG frame generator for the live remote-desktop stream. Captures the screen at…, Grab the primary monitor and return a PIL Image. Prefer pyautogui first because…, Yield JPEG bytes forever until the session is torn down. Emits ``b""`` as a…, _try_import_mss()

### Community 109 - "_auth"
Cohesion: 0.25
Nodes (8): AntigravityOAuth, GeminiCLIOAuth, is_authenticated, load_saved_tokens, logout, manage_auth, start_login_flow, _auth

### Community 110 - "CommandAction"
Cohesion: 0.29
Nodes (5): CommandAction, Get a command from the registry. Args: name: Command name Returns: List of…, Represents a single action in a command sequence., Convert to dictionary for JSON serialization., Create from dictionary.

### Community 111 - "_build_ui_masks"
Cohesion: 0.29
Nodes (7): Canny, GaussianBlur, adaptiveThreshold, dilate, getStructuringElement, morphologyEx, _build_ui_masks

### Community 112 - "_build_ocr_passes"
Cohesion: 0.29
Nodes (7): autocontrast, filter, grayscale, invert, point, resize, _build_ocr_passes

### Community 113 - "_ensure_tesseract"
Cohesion: 0.29
Nodes (7): get_tesseract_version, input, lower, run, _ensure_tesseract, _setup, _tesseract_available

### Community 114 - "append"
Cohesion: 0.53
Nodes (6): any, append, sorted, _candidate_overlap, _dedupe_scored_matches, _dedupe_ui_candidates

### Community 115 - "main"
Cohesion: 0.33
Nodes (6): ArgumentParser, add_parser, add_subparsers, parse_args, print_help, main

### Community 116 - "Contributor Covenant Code of Conduct"
Cohesion: 0.33
Nodes (5): Attribution, Contributor Covenant Code of Conduct, Enforcement, Our Pledge, Our Standards

### Community 117 - "PULL_REQUEST_TEMPLATE.md"
Cohesion: 0.33
Nodes (5): Checklist, Related issues, Summary, Testing, Type of change

### Community 118 - "monitor_build_window"
Cohesion: 0.33
Nodes (6): capture_full_screen(), monitor_build_window(), Clear the task mapping only when the finishing task is still current., Send periodic full-screen screenshots to track build progress. Stores itself in…, Capture full screen screenshot., unregister_build_screenshot_task()

### Community 119 - ".connect_mqtt"
Cohesion: 0.40
Nodes (3): Login to Qubo cloud, discover device, connect MQTT., Establish the MQTT connection (or reconnect if already exists)., Background loop that keeps tokens fresh and MQTT connected.

### Community 120 - "RateLimiter"
Cohesion: 0.40
Nodes (5): RateLimiter, __init__, check, remaining, set_limit

### Community 121 - "trim_registry_for_telegram"
Cohesion: 0.40
Nodes (4): CommandRegistryEntry, Helpers for building Telegram bot command menus safely., Return command/description pairs capped to Telegram's command limit., trim_registry_for_telegram()

### Community 122 - "resolve_app_query"
Cohesion: 0.40
Nodes (4): AppQueryResult, Resolve a user query to one app or an ambiguous list., Result of resolving a user query against the app catalog., resolve_app_query()

### Community 123 - "_load_config_files"
Cohesion: 0.50
Nodes (4): dotenv_path_candidates, load_dotenv, load_into_environ, _load_config_files

### Community 124 - "pocket_desk_agent"
Cohesion: 0.50
Nodes (3): version, pocket_desk_agent, importlib.metadata

## Ambiguous Edges - Review These
- `PROJECT_STRUCTURE.md` → `README.md`  [AMBIGUOUS]
  PROJECT_STRUCTURE.md · relation: conceptually_related_to
- `docs/AUTHENTICATION_REQUIREMENTS.md` → `docs/COMMANDS.md`  [AMBIGUOUS]
  docs/AUTHENTICATION_REQUIREMENTS.md · relation: conceptually_related_to

## Knowledge Gaps
- **80 isolated node(s):** `pocket-desk-agent`, `setup.sh script`, `Summary`, `Type of change`, `Checklist` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `PROJECT_STRUCTURE.md` and `README.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `docs/AUTHENTICATION_REQUIREMENTS.md` and `docs/COMMANDS.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `pocket_desk_agent.config` connect `pocket_desk_agent.config` to `pocket_desk_agent.handlers.remote`, `main`, `load`, `scripts.manage_auth`, `plugins.caveman.skills.compress.scripts.compress`, `pocket_desk_agent.remote.session`, `pocket_desk_agent.configure`, `pocket_desk_agent.antigravity_auth`, `pocket_desk_agent.cli`, `_load_config_files`, `docs/MOBILE_AUTHENTICATION.md`?**
  _High betweenness centrality (0.241) - this node is a cross-community bridge._
- **Why does `pocket_desk_agent.remote.tunnel` connect `pocket_desk_agent.remote.session` to `pocket_desk_agent.handlers.remote`, `scripts.manage_auth`, `pocket_desk_agent.handlers.scheduling`, `pocket_desk_agent.config`?**
  _High betweenness centrality (0.228) - this node is a cross-community bridge._
- **Why does `RemoteSession` connect `RemoteSession` to `pocket_desk_agent.remote.session`, `capture.py`, `remote.py`, `InputDispatcher`, `start_remote_session`?**
  _High betweenness centrality (0.226) - this node is a cross-community bridge._
- **Are the 80 inferred relationships involving `pocket_desk_agent.command_map` (e.g. with `pocket_desk_agent/command_map.py` and `pocket_desk_agent`) actually correct?**
  _`pocket_desk_agent.command_map` has 80 INFERRED edges - model-reasoned connections that need verification._
- **Are the 58 inferred relationships involving `pocket_desk_agent.gemini_actions` (e.g. with `GeminiToolResult` and `PendingGeminiAction`) actually correct?**
  _`pocket_desk_agent.gemini_actions` has 58 INFERRED edges - model-reasoned connections that need verification._