# Graph Report - C:\Users\dell\Downloads\Srikanth\Github\pdagent  (2026-04-24)

## Corpus Check
- 84 files · ~97,226 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2825 nodes · 5842 edges · 44 communities detected
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 1403 edges (avg confidence: 0.67)
- Token cost: 234,766 input · 305,619 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Claude Text Ocr|Claude Text Ocr]]
- [[_COMMUNITY_Code Get Gemini|Code Get Gemini]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Dropbox Authentication Authcode|Dropbox Authentication Authcode]]
- [[_COMMUNITY_Utils Handlers Inputdispatcher|Utils Handlers Inputdispatcher]]
- [[_COMMUNITY_Compress App Scripts|Compress App Scripts]]
- [[_COMMUNITY_Text Ocr Get|Text Ocr Get]]
- [[_COMMUNITY_Cloudflared Enabled Load|Cloudflared Enabled Load]]
- [[_COMMUNITY_Task Tasks Scheduled|Task Tasks Scheduled]]
- [[_COMMUNITY_App Candidates Configure|App Candidates Configure]]
- [[_COMMUNITY_Session Cloudflared Start|Session Cloudflared Start]]
- [[_COMMUNITY_Load Server Start|Load Server Start]]
- [[_COMMUNITY_Win32 Workflow Antigravity|Win32 Workflow Antigravity]]
- [[_COMMUNITY_Validate Plugins Caveman|Validate Plugins Caveman]]
- [[_COMMUNITY_Caveman Skill Compress|Caveman Skill Compress]]
- [[_COMMUNITY_Validate Code Compress|Validate Code Compress]]
- [[_COMMUNITY_Check Local Version|Check Local Version]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Directory Get Current|Directory Get Current]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Exists Dict Get|Exists Dict Get]]
- [[_COMMUNITY_Get Instance Info|Get Instance Info]]
- [[_COMMUNITY_Bot Process Check|Bot Process Check]]
- [[_COMMUNITY_Dropbox Delete Upload|Dropbox Delete Upload]]
- [[_COMMUNITY_Arc Brow Hairline|Arc Brow Hairline]]
- [[_COMMUNITY_Init Management Scripts|Init Management Scripts]]
- [[_COMMUNITY_Eye Brow Hairline|Eye Brow Hairline]]
- [[_COMMUNITY_Eye Background Circle|Eye Background Circle]]
- [[_COMMUNITY_Centralized Bot Map|Centralized Bot Map]]
- [[_COMMUNITY_Constants Single Source|Constants Single Source]]
- [[_COMMUNITY_Plugins Caveman Skills|Plugins Caveman Skills]]
- [[_COMMUNITY_Generate Pkce Verifier|Generate Pkce Verifier]]
- [[_COMMUNITY_Clear New|Clear New]]
- [[_COMMUNITY_Create Dictionary|Create Dictionary]]
- [[_COMMUNITY_Read Every Value|Read Every Value]]
- [[_COMMUNITY_Validate Required|Validate Required]]
- [[_COMMUNITY_Create Instance Persisted|Create Instance Persisted]]
- [[_COMMUNITY_Escape Values Inserted|Escape Values Inserted]]
- [[_COMMUNITY_Combine Stdout Stderr|Combine Stdout Stderr]]
- [[_COMMUNITY_True When Schtasks|True When Schtasks]]
- [[_COMMUNITY_Run Subprocess Capture|Run Subprocess Capture]]
- [[_COMMUNITY_Scripts|Scripts]]
- [[_COMMUNITY_Scripts Install Ps1|Scripts Install Ps1]]

## God Nodes (most connected - your core abstractions)
1. `Config` - 222 edges
2. `GeminiCLIOAuth` - 113 edges
3. `AntigravityOAuth` - 109 edges
4. `pocket_desk_agent.handlers.scheduling` - 76 edges
5. `StartupManager` - 72 edges
6. `ScheduledTask` - 66 edges
7. `pocket_desk_agent.handlers.system` - 52 edges
8. `CommandAction` - 48 edges
9. `RateLimiter` - 39 edges
10. `pocket_desk_agent.handlers.remote` - 36 edges

## Surprising Connections (you probably didn't know these)
- `File system manager for repository access.` --uses--> `Config`  [INFERRED]
  C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\file_manager.py → C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\config.py
- `Manages file system access within approved directory.` --uses--> `Config`  [INFERRED]
  C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\file_manager.py → C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\config.py
- `Check if path is within any of the approved directories.          Uses Path.is` --uses--> `Config`  [INFERRED]
  C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\file_manager.py → C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\config.py
- `Get user's current directory.` --uses--> `Config`  [INFERRED]
  C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\file_manager.py → C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\config.py
- `Change user's current directory.` --uses--> `Config`  [INFERRED]
  C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\file_manager.py → C:\Users\dell\Downloads\Srikanth\Github\pdagent\pocket_desk_agent\config.py

## Hyperedges (group relationships)
- **Multilingual README Documentation Bundle** — file_readme_md, file_readme_de_md, file_readme_es_md, file_readme_fr_md, file_readme_ja_md, file_readme_ko_md, file_readme_pt_br_md, file_readme_ru_md, file_readme_tr_md, file_readme_uk_md, file_readme_zh_cn_md [EXTRACTED 1.00]
- **Maintainer and Contributor Guidance** — file_agents_md, file_claude_md, file_contributing_md, file_project_structure_md [INFERRED 0.91]
- **Authentication, Security, and Command Policy Docs** — file_security_md, file_docs_authentication_requirements_md, file_docs_commands_md, file_docs_antigravity_login_implementation_md [INFERRED 0.89]
- **hyperedge:mobile_auth_flow_chunk02** —  [INFERRED 0.88]
- **hyperedge:compress_skill_workflow_chunk02** —  [INFERRED 0.86]
- **hyperedge:telegram_command_registry_chunk02** —  [INFERRED 0.93]
- **hyperedge:config_env_surface_chunk02** —  [INFERRED 0.95]
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
- **face_group** —  [INFERRED 0.95]
- **Facial feature group** — node:left_eye, node:right_eye, node:mouth_arc, node:hairline_arc [EXTRACTED 0.94]
- **Facial features** — shape.left_eye, shape.right_eye, shape.mouth_arc, shape.brow_hairline_arc [INFERRED 0.96]
- **Foreground layered on background** — shape.background, shape.left_eye, shape.right_eye, shape.mouth_arc, shape.brow_hairline_arc [INFERRED 0.95]

## Communities

### Community 0 - "Claude Text Ocr"
Cohesion: 0.01
Nodes (414): antigravitychat_command(), antigravityclaudecodeopen_command(), antigravitymode_command(), antigravitymodel_command(), antigravityopenfolder_command(), claudecli_command(), claudeclisend_command(), _discover_candidate_folders() (+406 more)

### Community 1 - "Code Get Gemini"
Cohesion: 0.02
Nodes (240): AntigravityOAuth, generate(), OAuthCallbackHandler, PKCEGenerator, Antigravity OAuth authentication implementation., HTTP handler for OAuth callback.      Class-level state is used because HTTPSe, Suppress HTTP server logs, Handle GET request for OAuth callback (+232 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (307): class:pocket_desk_agent.gemini_actions.GeminiToolResult, class:pocket_desk_agent.gemini_actions.PendingGeminiAction, class:pocket_desk_agent.gemini_actions._MessageCollector, class:pocket_desk_agent.gemini_client.ResolvedModel, class:pocket_desk_agent.rate_limiter.RateLimiter, class:pocket_desk_agent.scheduler_registry.ScheduledTask, class:pocket_desk_agent.startup_manager.StartupStatus, class:pocket_desk_agent.updater.UpdateInfo (+299 more)

### Community 3 - "Dropbox Authentication Authcode"
Cohesion: 0.01
Nodes (209): AUTHENTICATION_REQUIREMENTS.md, config/antigravity-chatbot/tokens.json, config/pdagent-gemini/tokens.json, /accounts, /antigravitychat, /antigravityclaudecodeopen, /antigravitymode, /antigravitymodel (+201 more)

### Community 4 - "Utils Handlers Inputdispatcher"
Cohesion: 0.02
Nodes (208): PIL, PIL.Image, __future__, __future__.annotations, aiohttp, aiohttp.WSMsgType, aiohttp.web, asyncio (+200 more)

### Community 5 - "Compress App Scripts"
Cohesion: 0.01
Nodes (203): main, Path, compress_file, detect_file_type, exists, exit, is_file, len (+195 more)

### Community 6 - "Text Ocr Get"
Cohesion: 0.03
Nodes (118): Canny, CloseDesktop, Draw, GaussianBlur, GetUserObjectInformationW, ImportError, OpenInputDesktop, RuntimeError (+110 more)

### Community 7 - "Cloudflared Enabled Load"
Cohesion: 0.02
Nodes (115): Path, ValueError, append, dotenv_path_candidates, expanduser, expandvars, getenv, home (+107 more)

### Community 8 - "Task Tasks Scheduled"
Cohesion: 0.04
Nodes (74): _list_schedules_text(), Background task to check and execute scheduled tasks., scheduler_loop(), from_dict(), get_scheduler_registry(), Registry for storing and managing scheduled tasks., Return all pending tasks, including future runs., Update the status of a task. (+66 more)

### Community 9 - "App Candidates Configure"
Cohesion: 0.06
Nodes (85): AntigravityOAuth, ConfigParser, GeminiCLIOAuth, Path, StartupManager, app_path, app_path_candidates, append (+77 more)

### Community 10 - "Session Cloudflared Start"
Cohesion: 0.05
Nodes (65): _encode_jpeg(), frame_iter(), _pil_from_screen(), JPEG frame generator for the live remote-desktop stream.  Captures the screen at, Grab the primary monitor and return a PIL Image., Yield JPEG bytes forever until the session is torn down.      Emits ``b""`` as a, _try_import_mss(), InputDispatcher (+57 more)

### Community 11 - "Load Server Start"
Cohesion: 0.04
Nodes (80): HTTPServer, Thread, app_path, bool, chmod, clear, decode, digest (+72 more)

### Community 12 - "Win32 Workflow Antigravity"
Cohesion: 0.06
Nodes (48): Multi-mode Authentication, React Native APK Build Workflow, Claude and Antigravity Integration, Central Command Registry, Telegram Command Surface, Config.load Class Pattern, Runtime Dependency Stack, Large APK Upload via Dropbox (+40 more)

### Community 13 - "Validate Plugins Caveman"
Cohesion: 0.05
Nodes (60): Path, append, encode, exists, exit, get_encoding, glob, insert (+52 more)

### Community 14 - "Caveman Skill Compress"
Cohesion: 0.03
Nodes (60): CLAUDE.md, FILE.original.md, SKILL.md, config.yaml, directory_containing_this_SKILL.md, original.md, /caveman, /caveman lite|full|ultra (+52 more)

### Community 15 - "Validate Code Compress"
Cohesion: 0.06
Nodes (46): benchmark_pair(), count_tokens(), main(), print_table(), main(), print_usage(), Entry point dispatched by the `pdagent` console script., build_compress_prompt() (+38 more)

### Community 16 - "Check Local Version"
Cohesion: 0.06
Nodes (47): acquire_lock(), main(), post_init(), post_shutdown(), _process_is_running(), Main bot entry point., Sync commands with Telegram on startup and launch background tasks., Tear down any active remote-desktop sessions cleanly on bot exit. (+39 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (46): class:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth, class:pocket_desk_agent.gemini_client.GeminiClient, external_symbol:http.server.HTTPServer, external_symbol:pocket_desk_agent.antigravity_auth.AntigravityOAuth, external_symbol:pocket_desk_agent.antigravity_auth.TokenStorage, external_symbol:urllib.parse.urlencode, function:pocket_desk_agent.gemini_client._candidate_model_names, function:pocket_desk_agent.gemini_client._get_code_assist_endpoints (+38 more)

### Community 18 - "Directory Get Current"
Cohesion: 0.07
Nodes (29): FileManager, _format_size(), File system manager for repository access., Manages file system access within approved directory., Read contents of a file., Search for files matching pattern., Get information about a file or directory., Write content to a file (creates or overwrites). (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (37): class:pocket_desk_agent.file_manager.FileManager, class:pocket_desk_agent.startup_manager.StartupManager, external_symbol:pathlib.Path, external_symbol:pocket_desk_agent.app_paths.app_dir, method:pocket_desk_agent.file_manager.FileManager.__init__, method:pocket_desk_agent.file_manager.FileManager._format_size, method:pocket_desk_agent.file_manager.FileManager._is_safe_path, method:pocket_desk_agent.file_manager.FileManager.append_file (+29 more)

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (25): class:pocket_desk_agent.scheduler_registry.SchedulerRegistry, external_module:re, external_symbol:pocket_desk_agent.app_paths.existing_app_path, function:pocket_desk_agent.scheduling_utils.ensure_local_timezone, function:pocket_desk_agent.scheduling_utils.format_duration, function:pocket_desk_agent.scheduling_utils.format_eta, function:pocket_desk_agent.scheduling_utils.get_task_due_at, function:pocket_desk_agent.scheduling_utils.local_now (+17 more)

### Community 21 - "Exists Dict Get"
Cohesion: 0.13
Nodes (24): cls, dump, error, existing_app_path, exists, info, items, len (+16 more)

### Community 22 - "Get Instance Info"
Cohesion: 0.15
Nodes (23): AntigravityOAuth, GeminiCLIOAuth, append, bool, get, getattr, info, isinstance (+15 more)

### Community 23 - "Bot Process Check"
Cohesion: 0.27
Nodes (12): check_status(), _current_pid_file(), is_running(), Process management utility for Pocket Desk Agent. Handles stopping and status ch, Check if process is running on Windows., Return the canonical PID file, falling back to the legacy location., Terminate the bot process., Check and print bot status. (+4 more)

### Community 24 - "Dropbox Delete Upload"
Cohesion: 0.25
Nodes (7): delete_from_dropbox(), handle_dropbox_delete(), handle_upload_choice(), Inline button callback handlers., Handle Dropbox file deletion request., Delete file from Dropbox.      Returns:         dict with 'success' and 'error', Handle user's choice for large file upload.

### Community 25 - "Arc Brow Hairline"
Cohesion: 0.62
Nodes (7): Caveman, Rounded square background, Brow or hairline arc, Brow or hairline arc, Left eye, Mouth arc, Right eye

### Community 26 - "Init Management Scripts"
Cohesion: 0.33
Nodes (1): Management scripts for Pocket Desk Agent.

### Community 27 - "Eye Brow Hairline"
Cohesion: 0.67
Nodes (6): brow or hairline, head, left eye, mouth, right eye, Caveman icon

### Community 28 - "Eye Background Circle"
Cohesion: 0.4
Nodes (6): Background circle, Caveman, Hairline/forehead stroke, Left eye, Mouth arc, Right eye

### Community 29 - "Centralized Bot Map"
Cohesion: 1.0
Nodes (1): Centralized command registry for the bot.

### Community 30 - "Constants Single Source"
Cohesion: 1.0
Nodes (1): Shared constants for Pocket Desk Agent.  Single source of truth for API endpoi

### Community 31 - "Plugins Caveman Skills"
Cohesion: 1.0
Nodes (2): plugins/caveman/skills/compress/scripts/__init__.py, plugins.caveman.skills.compress.scripts

### Community 32 - "Generate Pkce Verifier"
Cohesion: 1.0
Nodes (1): Generate PKCE verifier and challenge

### Community 33 - "Clear New"
Cohesion: 1.0
Nodes (1): Clear state for a new login flow.

### Community 34 - "Create Dictionary"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 35 - "Read Every Value"
Cohesion: 1.0
Nodes (1): (Re-)read every config value from ``os.environ``.

### Community 36 - "Validate Required"
Cohesion: 1.0
Nodes (1): Validate required configuration.

### Community 37 - "Create Instance Persisted"
Cohesion: 1.0
Nodes (1): Create an instance from persisted data.

### Community 38 - "Escape Values Inserted"
Cohesion: 1.0
Nodes (1): Escape values inserted into Task Scheduler XML.

### Community 39 - "Combine Stdout Stderr"
Cohesion: 1.0
Nodes (1): Combine stdout and stderr for error reporting.

### Community 40 - "True When Schtasks"
Cohesion: 1.0
Nodes (1): Return True when schtasks reports that the task does not exist.

### Community 41 - "Run Subprocess Capture"
Cohesion: 1.0
Nodes (1): Run a subprocess command and capture output as text.

### Community 43 - "Scripts"
Cohesion: 1.0
Nodes (1): scripts

### Community 44 - "Scripts Install Ps1"
Cohesion: 1.0
Nodes (1): scripts.install.ps1

## Ambiguous Edges - Review These
- `PROJECT_STRUCTURE.md` → `README.md`  [AMBIGUOUS]
  PROJECT_STRUCTURE.md · relation: conceptually_related_to
- `docs/AUTHENTICATION_REQUIREMENTS.md` → `docs/COMMANDS.md`  [AMBIGUOUS]
  docs/AUTHENTICATION_REQUIREMENTS.md · relation: conceptually_related_to

## Knowledge Gaps
- **254 isolated node(s):** `Heuristic denylist for files that must never be shipped to a third-party API.`, `Strip outer ```markdown ... ``` fence when it wraps the entire output.`, `Check if a line looks like code.`, `Check if content is valid JSON.`, `Heuristic: check if content looks like YAML.` (+249 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Init Management Scripts`** (6 nodes): `Management scripts for Pocket Desk Agent.`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Centralized Bot Map`** (2 nodes): `Centralized command registry for the bot.`, `command_map.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Constants Single Source`** (2 nodes): `Shared constants for Pocket Desk Agent.  Single source of truth for API endpoi`, `constants.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Plugins Caveman Skills`** (2 nodes): `plugins/caveman/skills/compress/scripts/__init__.py`, `plugins.caveman.skills.compress.scripts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Generate Pkce Verifier`** (1 nodes): `Generate PKCE verifier and challenge`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Clear New`** (1 nodes): `Clear state for a new login flow.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Create Dictionary`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Read Every Value`** (1 nodes): `(Re-)read every config value from ``os.environ``.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Validate Required`** (1 nodes): `Validate required configuration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Create Instance Persisted`** (1 nodes): `Create an instance from persisted data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Escape Values Inserted`** (1 nodes): `Escape values inserted into Task Scheduler XML.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Combine Stdout Stderr`** (1 nodes): `Combine stdout and stderr for error reporting.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `True When Schtasks`** (1 nodes): `Return True when schtasks reports that the task does not exist.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Run Subprocess Capture`** (1 nodes): `Run a subprocess command and capture output as text.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scripts`** (1 nodes): `scripts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scripts Install Ps1`** (1 nodes): `scripts.install.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `PROJECT_STRUCTURE.md` and `README.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `docs/AUTHENTICATION_REQUIREMENTS.md` and `docs/COMMANDS.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Config` connect `Claude Text Ocr` to `Code Get Gemini`, `Task Tasks Scheduled`, `Session Cloudflared Start`, `Validate Code Compress`, `Check Local Version`, `Directory Get Current`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `pocket_desk_agent.handlers.scheduling` connect `Utils Handlers Inputdispatcher` to `Community 2`, `Community 20`, `Compress App Scripts`, `Text Ocr Get`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `scripts.manage_auth` connect `Utils Handlers Inputdispatcher` to `Community 2`, `Compress App Scripts`, `Cloudflared Enabled Load`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 220 inferred relationships involving `Config` (e.g. with `AntigravityAuth` and `Authentication command handlers (login, authcode, checkauth, logout).  /login`) actually correct?**
  _`Config` has 220 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `GeminiCLIOAuth` (e.g. with `AntigravityAuth` and `Authentication command handlers (login, authcode, checkauth, logout).  /login`) actually correct?**
  _`GeminiCLIOAuth` has 93 INFERRED edges - model-reasoned connections that need verification._