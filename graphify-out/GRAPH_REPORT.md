# Graph Report - pdagent  (2026-04-25)

## Corpus Check
- 55 files · ~101,472 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2993 nodes · 6295 edges · 98 communities detected
- Extraction: 71% EXTRACTED · 29% INFERRED · 0% AMBIGUOUS · INFERRED: 1853 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]

## God Nodes (most connected - your core abstractions)
1. `Config` - 302 edges
2. `GeminiCLIOAuth` - 112 edges
3. `AntigravityOAuth` - 108 edges
4. `ScheduledTask` - 106 edges
5. `pocket_desk_agent.handlers.scheduling` - 76 edges
6. `StartupManager` - 72 edges
7. `perform_system_shutdown` - 67 edges
8. `get_for_user` - 55 edges
9. `pocket_desk_agent.handlers.system` - 52 edges
10. `CommandAction` - 48 edges

## Surprising Connections (you probably didn't know these)
- `Config` --uses--> `Return True when the target PID is alive.`  [INFERRED]
  pocket_desk_agent\config.py → pocket_desk_agent\main.py
- `Config` --uses--> `Background task to check and execute scheduled tasks.`  [INFERRED]
  pocket_desk_agent\config.py → pocket_desk_agent\main.py
- `Config` --uses--> `Antigravity and VS Code integration command handlers.`  [INFERRED]
  pocket_desk_agent\config.py → pocket_desk_agent\handlers\antigravity.py
- `Config` --uses--> `Load Windows UI automation modules on first use (cached after that).`  [INFERRED]
  pocket_desk_agent\config.py → pocket_desk_agent\handlers\antigravity.py
- `Config` --uses--> `Return the first visible VS Code window, if any.`  [INFERRED]
  pocket_desk_agent\config.py → pocket_desk_agent\handlers\antigravity.py

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

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (365): antigravitychat_command(), antigravityclaudecodeopen_command(), antigravitymode_command(), antigravitymodel_command(), antigravityopenfolder_command(), claudecli_command(), claudeclisend_command(), _discover_candidate_folders() (+357 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (299): Handle /claudeclisend - type a followup prompt into the open Claude CLI window., Handle /claudeclisend - type a followup prompt into the open Claude CLI window., Handle /antigravityopenfolder - list folders and open selected one in VS Code., Handle /antigravityopenfolder - list folders and open selected one in VS Code., Handle /openbrowser - show browser options and open selected one maximized., Handle /openbrowser - show browser options and open selected one maximized., Return the saved-token file mtime, or 0 when unavailable., build_command() (+291 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (242): AntigravityOAuth, generate(), OAuthCallbackHandler, PKCEGenerator, Antigravity OAuth authentication implementation., HTTP handler for OAuth callback.      Class-level state is used because HTTPSe, Suppress HTTP server logs, Handle GET request for OAuth callback (+234 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (308): class:pocket_desk_agent.gemini_actions.GeminiToolResult, class:pocket_desk_agent.gemini_actions.PendingGeminiAction, class:pocket_desk_agent.gemini_actions._MessageCollector, class:pocket_desk_agent.gemini_client.ResolvedModel, class:pocket_desk_agent.rate_limiter.RateLimiter, class:pocket_desk_agent.scheduler_registry.ScheduledTask, class:pocket_desk_agent.startup_manager.StartupStatus, class:pocket_desk_agent.updater.UpdateInfo (+300 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (197): Management scripts for Pocket Desk Agent., PIL, PIL.Image, __future__, __future__.annotations, aiohttp, aiohttp.WSMsgType, aiohttp.web (+189 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (182): AUTHENTICATION_REQUIREMENTS.md, config/antigravity-chatbot/tokens.json, config/pdagent-gemini/tokens.json, /accounts, /antigravitychat, /antigravityclaudecodeopen, /antigravitymode, /antigravitymodel (+174 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (144): Event, getLogger, exists, home, joinpath, mkdir, tuple, getLogger (+136 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (143): main, Path, append, encode, exists, exit, get_encoding, glob (+135 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (142): Path, ValueError, append, dotenv_path_candidates, expanduser, expandvars, getenv, home (+134 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (118): Canny, CloseDesktop, Draw, GaussianBlur, GetUserObjectInformationW, ImportError, OpenInputDesktop, RuntimeError (+110 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (85): AntigravityOAuth, ConfigParser, GeminiCLIOAuth, Path, StartupManager, app_path, app_path_candidates, append (+77 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (80): HTTPServer, Thread, app_path, bool, chmod, clear, decode, digest (+72 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (48): Multi-mode Authentication, React Native APK Build Workflow, Claude and Antigravity Integration, Central Command Registry, Telegram Command Surface, Config.load Class Pattern, Runtime Dependency Stack, Large APK Upload via Dropbox (+40 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (61): capture_claude_screenshot(), claudeask_command(), claudebranch_command(), claudechat_command(), claudelatest_command(), claudemode_command(), claudemodel_command(), claudenew_command() (+53 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (60): CLAUDE.md, FILE.original.md, SKILL.md, config.yaml, directory_containing_this_SKILL.md, original.md, /caveman, /caveman lite|full|ultra (+52 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (45): benchmark_pair(), count_tokens(), main(), print_table(), main(), print_usage(), build_compress_prompt(), build_fix_prompt() (+37 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (46): class:pocket_desk_agent.gemini_cli_auth.GeminiCLIOAuth, class:pocket_desk_agent.gemini_client.GeminiClient, external_symbol:http.server.HTTPServer, external_symbol:pocket_desk_agent.antigravity_auth.AntigravityOAuth, external_symbol:pocket_desk_agent.antigravity_auth.TokenStorage, external_symbol:urllib.parse.urlencode, function:pocket_desk_agent.gemini_client._candidate_model_names, function:pocket_desk_agent.gemini_client._get_code_assist_endpoints (+38 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (37): class:pocket_desk_agent.file_manager.FileManager, class:pocket_desk_agent.startup_manager.StartupManager, external_symbol:pathlib.Path, external_symbol:pocket_desk_agent.app_paths.app_dir, method:pocket_desk_agent.file_manager.FileManager.__init__, method:pocket_desk_agent.file_manager.FileManager._format_size, method:pocket_desk_agent.file_manager.FileManager._is_safe_path, method:pocket_desk_agent.file_manager.FileManager.append_file (+29 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (32): apply_pypi_update(), apply_update(), check_for_updates(), check_pypi_version(), format_update_notification(), get_last_check(), get_local_commit_date(), get_local_sha() (+24 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (24): class:pocket_desk_agent.scheduler_registry.SchedulerRegistry, external_symbol:pocket_desk_agent.app_paths.existing_app_path, function:pocket_desk_agent.scheduling_utils.ensure_local_timezone, function:pocket_desk_agent.scheduling_utils.format_duration, function:pocket_desk_agent.scheduling_utils.format_eta, function:pocket_desk_agent.scheduling_utils.get_task_due_at, function:pocket_desk_agent.scheduling_utils.local_now, function:pocket_desk_agent.scheduling_utils.parse_duration_spec (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (23): AntigravityOAuth, GeminiCLIOAuth, append, bool, get, getattr, info, isinstance (+15 more)

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (17): _activate_window_with_pygetwindow(), build_window_inventory(), format_window_inventory(), _is_switchable_window(), list_open_windows(), _nudge_foreground_lock(), Helpers for listing and activating desktop windows on Windows., Best-effort extraction of a platform window handle. (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.62
Nodes (7): Caveman, Rounded square background, Brow or hairline arc, Brow or hairline arc, Left eye, Mouth arc, Right eye

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (6): brow or hairline, head, left eye, mouth, right eye, Caveman icon

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (6): Background circle, Caveman, Hairline/forehead stroke, Left eye, Mouth arc, Right eye

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Centralized command registry for the bot.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Shared constants for Pocket Desk Agent.  Single source of truth for API endpoi

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (2): plugins/caveman/skills/compress/scripts/__init__.py, plugins.caveman.skills.compress.scripts

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Generate PKCE verifier and challenge

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Clear state for a new login flow.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): (Re-)read every config value from ``os.environ``.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Validate required configuration.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Create an instance from persisted data.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Escape values inserted into Task Scheduler XML.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Combine stdout and stderr for error reporting.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return True when schtasks reports that the task does not exist.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Run a subprocess command and capture output as text.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): scripts.install.ps1

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): scripts

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Format an UpdateInfo into a user-friendly Telegram message.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Run an update check at startup and log the result.      This is meant to be ca

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Background coroutine that periodically checks for updates.      Args:

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Run an update check at startup and log the result.      This is meant to be ca

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Result of a check-for-updates query.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Run a git sub-command and return the completed process.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Return the current local HEAD commit SHA (full).

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Return the current local HEAD commit SHA (short 7-char).

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Human-readable version string: v1.0.0 (abc1234) for git, v1.0.0 for PyPI.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Return the date of the local HEAD commit.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Query PyPI for the latest published version of pocket-desk-agent.      Returns

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Check for updates. For PyPI installs, queries PyPI for the latest version.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Return the cached result and timestamp of the last update check.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Pull latest changes from GitHub and re-install requirements.      Returns (suc

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Background coroutine that periodically checks for updates.      Args:

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Format an UpdateInfo into a user-friendly Telegram message.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Handle Dropbox file deletion request.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Delete file from Dropbox.      Returns:         dict with 'success' and 'error'

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Handle user's choice for large file upload.

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): File system command handlers.

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Handle /pwd command - show current directory.

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Handle /cd command - change directory.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Handle /ls command - list directory.

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Handle /cat command - read file.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Handle /find command - search files.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Handle /info command - get file info.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): System control command handlers.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Track the last privacy-mode state requested by the bot.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Render a human-readable timestamp for privacy mode status.

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Return a status summary for privacy mode.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Turn the display off or wake it without locking the Windows session.

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Normalize privacy-mode command arguments into a supported action.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Handle /stopbot command - stop the bot process with confirmation.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Handle /shutdown command - shutdown laptop with confirmation.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Shutdown the host machine using the same OS-specific behavior as /shutdown.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Put the host to sleep and return a user-facing status message.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Handle /battery command - check battery status.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Handle /screenshot command - capture current screen.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Handle /sleep command - put PC to sleep.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Handle /wakeup command - wake up PC (requires Wake-on-LAN setup).

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Handle /privacy command - blank or wake the display without locking.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Handle /hotkey command - execute keyboard shortcuts.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Handle /windows command - list switchable desktop windows.

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Handle /focuswindow command - activate a previously listed window.

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Handle /clipboard command - set clipboard content.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Handle /viewclipboard command - get current clipboard content.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Grab the primary monitor and return a PIL Image.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Yield JPEG bytes forever until the session is torn down.      Emits ``b""`` as a

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Per-session input dispatcher with rate limit and fail-safe tracking.

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Apply a single event. Returns an optional status string.

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): RemoteSession state container.  Holds the per-user live remote-desktop session:

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (1): Idempotent teardown: stop WS, server, tunnel; drop from registry.      Each step

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (1): Process management utility for Pocket Desk Agent. Handles stopping and status ch

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (1): Check if process is running on Windows.

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (1): Return the canonical PID file, falling back to the legacy location.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (1): Terminate the bot process.

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (1): Check and print bot status.

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (1): Restart the bot process.

## Ambiguous Edges - Review These
- `PROJECT_STRUCTURE.md` → `README.md`  [AMBIGUOUS]
  PROJECT_STRUCTURE.md · relation: conceptually_related_to
- `docs/AUTHENTICATION_REQUIREMENTS.md` → `docs/COMMANDS.md`  [AMBIGUOUS]
  docs/AUTHENTICATION_REQUIREMENTS.md · relation: conceptually_related_to

## Knowledge Gaps
- **428 isolated node(s):** `Heuristic denylist for files that must never be shipped to a third-party API.`, `Strip outer ```markdown ... ``` fence when it wraps the entire output.`, `Check if a line looks like code.`, `Check if content is valid JSON.`, `Heuristic: check if content looks like YAML.` (+423 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (2 nodes): `Centralized command registry for the bot.`, `command_map.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `Shared constants for Pocket Desk Agent.  Single source of truth for API endpoi`, `constants.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `plugins/caveman/skills/compress/scripts/__init__.py`, `plugins.caveman.skills.compress.scripts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Generate PKCE verifier and challenge`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Clear state for a new login flow.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `(Re-)read every config value from ``os.environ``.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Validate required configuration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Create an instance from persisted data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Escape values inserted into Task Scheduler XML.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Combine stdout and stderr for error reporting.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Return True when schtasks reports that the task does not exist.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Run a subprocess command and capture output as text.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `scripts.install.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `scripts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Format an UpdateInfo into a user-friendly Telegram message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Run an update check at startup and log the result.      This is meant to be ca`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Background coroutine that periodically checks for updates.      Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Run an update check at startup and log the result.      This is meant to be ca`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Result of a check-for-updates query.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Run a git sub-command and return the completed process.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Return the current local HEAD commit SHA (full).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Return the current local HEAD commit SHA (short 7-char).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Human-readable version string: v1.0.0 (abc1234) for git, v1.0.0 for PyPI.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Return the date of the local HEAD commit.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Query PyPI for the latest published version of pocket-desk-agent.      Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Check for updates. For PyPI installs, queries PyPI for the latest version.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Return the cached result and timestamp of the last update check.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Pull latest changes from GitHub and re-install requirements.      Returns (suc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Background coroutine that periodically checks for updates.      Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Format an UpdateInfo into a user-friendly Telegram message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Handle Dropbox file deletion request.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Delete file from Dropbox.      Returns:         dict with 'success' and 'error'`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Handle user's choice for large file upload.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `File system command handlers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Handle /pwd command - show current directory.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Handle /cd command - change directory.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Handle /ls command - list directory.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Handle /cat command - read file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Handle /find command - search files.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Handle /info command - get file info.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `System control command handlers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Track the last privacy-mode state requested by the bot.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Render a human-readable timestamp for privacy mode status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Return a status summary for privacy mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Turn the display off or wake it without locking the Windows session.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Normalize privacy-mode command arguments into a supported action.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Handle /stopbot command - stop the bot process with confirmation.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Handle /shutdown command - shutdown laptop with confirmation.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Shutdown the host machine using the same OS-specific behavior as /shutdown.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Put the host to sleep and return a user-facing status message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Handle /battery command - check battery status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Handle /screenshot command - capture current screen.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Handle /sleep command - put PC to sleep.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Handle /wakeup command - wake up PC (requires Wake-on-LAN setup).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Handle /privacy command - blank or wake the display without locking.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `Handle /hotkey command - execute keyboard shortcuts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Handle /windows command - list switchable desktop windows.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Handle /focuswindow command - activate a previously listed window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Handle /clipboard command - set clipboard content.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Handle /viewclipboard command - get current clipboard content.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Grab the primary monitor and return a PIL Image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Yield JPEG bytes forever until the session is torn down.      Emits ``b""`` as a`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Per-session input dispatcher with rate limit and fail-safe tracking.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Apply a single event. Returns an optional status string.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `RemoteSession state container.  Holds the per-user live remote-desktop session:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `Idempotent teardown: stop WS, server, tunnel; drop from registry.      Each step`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `Process management utility for Pocket Desk Agent. Handles stopping and status ch`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `Check if process is running on Windows.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `Return the canonical PID file, falling back to the legacy location.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `Terminate the bot process.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `Check and print bot status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `Restart the bot process.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `PROJECT_STRUCTURE.md` and `README.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `docs/AUTHENTICATION_REQUIREMENTS.md` and `docs/COMMANDS.md`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `pocket_desk_agent.handlers.scheduling` connect `Community 4` to `Community 0`, `Community 3`, `Community 6`, `Community 9`, `Community 19`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 1` to `Community 0`, `Community 2`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `scripts.manage_auth` connect `Community 4` to `Community 8`, `Community 2`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 300 inferred relationships involving `Config` (e.g. with `AntigravityAuth` and `Authentication command handlers (login, authcode, checkauth, logout).  /login`) actually correct?**
  _`Config` has 300 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `GeminiCLIOAuth` (e.g. with `AntigravityAuth` and `Authentication command handlers (login, authcode, checkauth, logout).  /login`) actually correct?**
  _`GeminiCLIOAuth` has 92 INFERRED edges - model-reasoned connections that need verification._