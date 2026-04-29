"""Build workflow, APK management, and file upload handlers."""

import logging
import os
import platform
import subprocess
import asyncio
import time
import io
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    build_state,
    build_monitor_state,
    build_screenshot_tasks,
    large_file_upload_state,
    apk_retrieval_state,
    DEFAULT_REPO_PATH,
    file_manager,
    safe_command,
)
from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)


def _discover_build_repositories(base_dir: str) -> list[str]:
    """Return repositories under ``base_dir`` that contain a package.json file."""
    repos: list[str] = []

    package_json_path = os.path.join(base_dir, "package.json")
    if os.path.exists(package_json_path):
        repos.append(base_dir)
        return repos

    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "package.json")):
            repos.append(item_path)

    return repos


def _filter_build_scripts(scripts: dict[str, str]) -> dict[str, str]:
    """Prefer build-related npm scripts while falling back to the full script map."""
    build_scripts = {
        key: value
        for key, value in scripts.items()
        if any(keyword in key.lower() for keyword in ["android", "build", "release", "debug"])
    }
    return build_scripts or scripts


def _load_repo_scripts(repo_path: str) -> dict[str, str]:
    """Load and filter scripts from a repository's package.json."""
    package_json_path = os.path.join(repo_path, "package.json")
    with open(package_json_path, "r", encoding="utf-8") as handle:
        package_data = json.load(handle)

    scripts = package_data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}

    normalized_scripts = {str(name): str(command) for name, command in scripts.items()}
    return _filter_build_scripts(normalized_scripts)


def prepare_build_workflow(
    user_id: int,
    current_dir: str,
    project_query: str | None = None,
) -> tuple[bool, str]:
    """Prime the existing build-selection state for slash commands or Gemini."""
    current_path = str(current_dir)
    if not os.path.exists(current_path):
        build_state.pop(user_id, None)
        return (
            False,
            f"Current directory not found:\n{current_path}\n\n"
            "Run '/cd <path>' to change directory or 'pdagent configure' to set CLAUDE_DEFAULT_REPO_PATH.",
        )

    try:
        repos = _discover_build_repositories(current_path)
    except Exception as exc:
        build_state.pop(user_id, None)
        logger.error("Failed to discover build repositories in %s: %s", current_path, exc, exc_info=True)
        return False, f"Error listing repositories: {exc}"

    if not repos:
        build_state.pop(user_id, None)
        return (
            False,
            f"No projects with package.json found in:\n{current_path}\n\n"
            "Use /cd to navigate to your projects directory first.",
        )

    filtered_repos = repos
    project_hint = (project_query or "").strip().lower()
    if project_hint:
        filtered_repos = [
            repo_path
            for repo_path in repos
            if project_hint in os.path.basename(repo_path).lower()
        ]
        if not filtered_repos:
            repo_names = ", ".join(os.path.basename(path) for path in repos[:10])
            if len(repos) > 10:
                repo_names += ", ..."
            build_state.pop(user_id, None)
            return (
                False,
                f"No project matched '{project_query}'.\n\n"
                f"Available projects here: {repo_names}",
            )

    if len(filtered_repos) == 1:
        selected_repo = filtered_repos[0]
        try:
            build_scripts = _load_repo_scripts(selected_repo)
        except Exception as exc:
            build_state.pop(user_id, None)
            logger.error("Failed to load package.json for %s: %s", selected_repo, exc, exc_info=True)
            return False, f"Error reading package.json: {exc}"

        if not build_scripts:
            build_state.pop(user_id, None)
            return False, f"No scripts found in package.json for {os.path.basename(selected_repo)}"

        build_state[user_id] = {
            "repos": filtered_repos,
            "selected_repo": selected_repo,
            "scripts": build_scripts,
            "step": "select_script",
            "timestamp": time.time(),
        }

        repo_name = os.path.basename(selected_repo)
        message = f"Project detected: {repo_name}\n\nAvailable npm scripts:\n\n"
        for index, (script_name, script_cmd) in enumerate(build_scripts.items(), 1):
            preview = f"{script_cmd[:60]}{'...' if len(script_cmd) > 60 else ''}"
            message += f"{index}. npm run {script_name}\n   -> {preview}\n\n"

        message += "Reply with the number or exact script name to run it.\n\nExample: 1 or android"
        return True, message

    build_state[user_id] = {
        "repos": filtered_repos,
        "step": "select_repo",
        "timestamp": time.time(),
    }

    message = f"Found {len(filtered_repos)} React Native repositories:\n\n"
    for index, repo_path in enumerate(filtered_repos, 1):
        message += f"{index}. {os.path.basename(repo_path)}\n"

    message += "\nReply with the number or name to select a repository.\n\nExample: 1 or MyApp"
    return True, message



def _discover_android_repositories(base_dir: str) -> list[str]:
    """Return repositories under ``base_dir`` that contain an Android project."""
    repos: list[str] = []

    android_path = os.path.join(base_dir, "android")
    if os.path.exists(android_path):
        repos.append(base_dir)
        return repos

    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "android")):
            repos.append(item_path)

    return repos


def _format_apk_folder_contents(folder_path: str) -> tuple[bool, str]:
    """Render a folder listing for the APK retrieval workflow."""
    try:
        items = os.listdir(folder_path)
    except Exception as exc:
        logger.error("Error reading APK output folder %s: %s", folder_path, exc, exc_info=True)
        return False, f"Error reading folder: {exc}"

    if not items:
        return True, "Folder is empty.\n\nReply with 'back' to go up."

    message = f"Current folder: {os.path.basename(folder_path)}\n\n"

    folders: list[str] = []
    files: list[str] = []
    for item in items:
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            folders.append(item)
        else:
            files.append(item)

    for index, folder in enumerate(sorted(folders), 1):
        message += f"{index}. [DIR] {folder}/\n"

    for index, filename in enumerate(sorted(files), len(folders) + 1):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith(".apk"):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            message += f"{index}. [APK] {filename} ({file_size_mb:.2f} MB)\n"
        else:
            message += f"{index}. [FILE] {filename}\n"

    message += "\nReply with:\n"
    message += "- Number to navigate/select\n"
    message += "- 'back' to go up\n"
    message += "- 'cancel' to exit\n\n"
    message += f"Path: {folder_path}"
    return True, message


def prepare_apk_retrieval_workflow(
    user_id: int,
    current_dir: str,
    project_query: str | None = None,
) -> tuple[bool, str]:
    """Prime the existing APK retrieval state for slash commands or Gemini."""
    current_path = str(current_dir)
    if not os.path.exists(current_path):
        apk_retrieval_state.pop(user_id, None)
        return (
            False,
            f"Current directory not found:\n{current_path}\n\n"
            "Run '/cd <path>' to change directory or 'pdagent configure' to set CLAUDE_DEFAULT_REPO_PATH.",
        )

    try:
        repos = _discover_android_repositories(current_path)
    except Exception as exc:
        apk_retrieval_state.pop(user_id, None)
        logger.error("Failed to discover Android repositories in %s: %s", current_path, exc, exc_info=True)
        return False, f"Error listing repositories: {exc}"

    if not repos:
        apk_retrieval_state.pop(user_id, None)
        return (
            False,
            f"No projects with android folder found in:\n{current_path}\n\n"
            "Use /cd to navigate to your projects directory first.",
        )

    filtered_repos = repos
    project_hint = (project_query or "").strip().lower()
    if project_hint:
        filtered_repos = [
            repo_path
            for repo_path in repos
            if project_hint in os.path.basename(repo_path).lower()
        ]
        if not filtered_repos:
            repo_names = ", ".join(os.path.basename(path) for path in repos[:10])
            if len(repos) > 10:
                repo_names += ", ..."
            apk_retrieval_state.pop(user_id, None)
            return (
                False,
                f"No project matched '{project_query}'.\n\n"
                f"Available Android projects here: {repo_names}",
            )

    if len(filtered_repos) == 1:
        selected_repo = filtered_repos[0]
        outputs_path = os.path.join(selected_repo, "android", "app", "build", "outputs")

        if not os.path.exists(outputs_path):
            apk_retrieval_state.pop(user_id, None)
            return (
                False,
                f"No build outputs found for {os.path.basename(selected_repo)}\n\n"
                "Build the app first using /build command.",
            )

        try:
            if not os.listdir(outputs_path):
                apk_retrieval_state.pop(user_id, None)
                return (
                    False,
                    f"Build outputs folder is empty for {os.path.basename(selected_repo)}\n\n"
                    "Build the app first using /build command.",
                )
        except Exception as exc:
            apk_retrieval_state.pop(user_id, None)
            logger.error("Failed to inspect APK outputs in %s: %s", outputs_path, exc, exc_info=True)
            return False, f"Error reading folder: {exc}"

        success, folder_message = _format_apk_folder_contents(outputs_path)
        if not success:
            apk_retrieval_state.pop(user_id, None)
            return False, folder_message

        apk_retrieval_state[user_id] = {
            "repos": filtered_repos,
            "selected_repo": selected_repo,
            "current_path": outputs_path,
            "step": "navigate",
            "timestamp": time.time(),
        }

        repo_name = os.path.basename(selected_repo)
        return True, f"Project detected: {repo_name}\n\nLoading build outputs...\n\n{folder_message}"

    apk_retrieval_state[user_id] = {
        "repos": filtered_repos,
        "step": "select_repo",
        "timestamp": time.time(),
    }

    message = f"Found {len(filtered_repos)} Android repositories:\n\n"
    for index, repo_path in enumerate(filtered_repos, 1):
        message += f"{index}. {os.path.basename(repo_path)}\n"

    message += "\nReply with the number or name to select a repository.\n\nExample: 1 or MyApp"
    return True, message


def upload_to_tempfile(file_path: str) -> dict:
    """
    Upload file to tempfile.org (up to 100MB, temporary storage).
    
    Returns:
        dict with 'success', 'link', 'error' keys
    """
    try:
        logger.info(f"Starting tempfile.org upload: {file_path}")
        
        # Check file size (100MB limit)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        if file_size > 100 * 1024 * 1024:
            return {'success': False, 'error': f'File too large ({file_size_mb:.1f}MB, max 100MB for tempfile.org)'}
        
        # Map config expiry to tempfile.org hours (1h, 6h, 24h, 48h)
        expiry_time = Config.UPLOAD_EXPIRY_TIME
        expiry_map = {
            '1h': '1',
            '12h': '6',  # Map 12h to 6h (closest available)
            '24h': '24',
            '72h': '48'  # Map 72h to 48h (max available)
        }
        expiry_hours = expiry_map.get(expiry_time, '1')
        
        filename = os.path.basename(file_path)
        
        # Upload file
        with open(file_path, 'rb') as f:
            files = {'files': (filename, f, 'application/octet-stream')}
            data = {'expiryHours': expiry_hours}
            
            response = requests.post(
                'https://tempfile.org/api/upload/local',
                files=files,
                data=data,
                timeout=600
            )
        
        logger.info(f"tempfile.org response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success') and result.get('files'):
                file_info = result['files'][0]
                download_url = file_info.get('url')
                
                logger.info(f"tempfile.org upload successful: {download_url}")
                return {
                    'success': True,
                    'link': download_url,
                    'expiry': f'{expiry_hours}h (auto-delete)'
                }
            else:
                error_msg = result.get('error', 'Upload failed')
                return {'success': False, 'error': error_msg}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    
    except Exception as e:
        logger.error(f"tempfile.org upload exception: {type(e).__name__}: {str(e)}")
        return {'success': False, 'error': str(e)}


def upload_to_dropbox(file_path: str) -> dict:
    """
    Upload file to Dropbox (requires DROPBOX_ACCESS_TOKEN in .env).

    Returns:
        dict with 'success', 'link', 'error' keys
    """
    try:
        import dropbox
        from dropbox.exceptions import AuthError, ApiError
        from dropbox import files as dbx_files
    except ImportError:
        return {
            'success': False,
            'error': 'Dropbox library not installed. Run: pip install dropbox'
        }

    try:
        logger.info(f"Starting Dropbox upload: {file_path}")

        # Get Dropbox access token from environment
        access_token = os.getenv('DROPBOX_ACCESS_TOKEN')
        if not access_token or access_token == 'your_dropbox_access_token_here':
            return {
                'success': False,
                'error': 'Dropbox not configured. Add DROPBOX_ACCESS_TOKEN to .env file.'
            }

        # Initialize Dropbox client with timeout
        dbx = dropbox.Dropbox(
            access_token,
            timeout=600  # 10 minutes timeout for large files
        )

        # Verify token works
        try:
            account = dbx.users_get_current_account()
            logger.info(f"Dropbox account: {account.email}")
        except AuthError as e:
            logger.error(f"Dropbox auth error: {e}")
            return {
                'success': False,
                'error': (
                    f'Dropbox authentication failed. Please check:\n'
                    f'1. Token has files.content.write permission\n'
                    f'2. Token was generated AFTER setting permissions\n'
                    f'3. Token is not expired\n\nError: {str(e)}'
                )
            }

        filename = os.path.basename(file_path)
        dropbox_path = f'/{filename}'  # Upload to root folder

        # Upload file
        file_size = os.path.getsize(file_path)
        logger.info(f"Uploading {file_size / (1024*1024):.2f} MB to Dropbox...")

        with open(file_path, 'rb') as f:
            if file_size > 150 * 1024 * 1024:
                # Chunked upload for files > 150 MB
                logger.info("Using chunked upload for large file...")
                CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB

                upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                cursor = dbx_files.UploadSessionCursor(
                    session_id=upload_session_start_result.session_id,
                    offset=f.tell()
                )
                commit = dbx_files.CommitInfo(
                    path=dropbox_path,
                    mode=dbx_files.WriteMode.overwrite
                )

                while f.tell() < file_size:
                    if (file_size - f.tell()) <= CHUNK_SIZE:
                        dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                    else:
                        dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                        cursor.offset = f.tell()
            else:
                # Simple upload for smaller files
                dbx.files_upload(
                    f.read(),
                    dropbox_path,
                    mode=dbx_files.WriteMode.overwrite
                )

        logger.info("File uploaded successfully, creating shared link...")

        # Create shared link — handle "already exists" gracefully
        link = None
        try:
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            link = shared_link_metadata.url
        except ApiError as e:
            logger.info(f"sharing_create_shared_link_with_settings error: {e} — trying to fetch existing link")
            # Any ApiError here (incl. shared_link_already_exists) — fall back to listing
            try:
                links = dbx.sharing_list_shared_links(path=dropbox_path, direct_only=True)
                if links.links:
                    link = links.links[0].url
            except Exception as list_err:
                logger.error(f"Could not list shared links: {list_err}")

        if not link:
            return {'success': False, 'error': 'File uploaded but could not create/fetch a shared link.'}

        # Convert to direct download link
        link = link.replace('?dl=0', '?dl=1').replace('www.dropbox.com', 'dl.dropboxusercontent.com')

        logger.info(f"Dropbox upload successful: {link}")
        return {
            'success': True,
            'link': link,
            'expiry': 'Permanent (until manually deleted)'
        }

    except AuthError as e:
        logger.error(f"Dropbox auth error: {e}")
        return {
            'success': False,
            'error': (
                f'Dropbox authentication error: {str(e)}\n\n'
                f'Make sure you:\n'
                f'1. Set permissions in Dropbox App Console\n'
                f'2. Generated NEW token after setting permissions\n'
                f'3. Updated .env with the new token'
            )
        }
    except Exception as e:
        logger.error(f"Dropbox upload exception: {type(e).__name__}: {str(e)}")
        return {
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}'
        }




def upload_large_file(file_path: str, service: str = 'tempfile') -> dict:
    """
    Upload file using specified service.
    
    Services:
    - tempfile: tempfile.org (up to 100MB, auto-delete)
    - dropbox: Dropbox (unlimited, permanent)
    
    Returns:
        dict with 'success', 'link', 'service', 'expiry', 'error' keys
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    logger.info(f"Uploading file: {file_path} ({file_size_mb:.2f} MB) to {service}")
    
    if service == 'dropbox':
        result = upload_to_dropbox(file_path)
        if result['success']:
            result['service'] = 'Dropbox'
            logger.info("Successfully uploaded to Dropbox")
        return result
    
    elif service == 'tempfile':
        # Check file size for tempfile.org
        if file_size_mb > 100:
            return {
                'success': False,
                'error': f'File too large ({file_size_mb:.2f} MB) for tempfile.org (max 100MB). Use Dropbox instead.',
                'service': None
            }
        
        result = upload_to_tempfile(file_path)
        if result['success']:
            result['service'] = 'tempfile.org'
            logger.info("Successfully uploaded to tempfile.org")
        return result
    
    else:
        return {
            'success': False,
            'error': f'Unknown service: {service}',
            'service': None
        }




async def build_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /build command - start build workflow."""
    if not update.message:
        return

    user_id = update.effective_user.id

    await update.message.reply_text("🔨 Starting build workflow...\n\nListing local repositories...")

    current_dir = str(file_manager.get_current_dir(user_id))
    success, message = prepare_build_workflow(user_id, current_dir)
    await update.message.reply_text(message)
    if success:
        logger.info("Prepared build workflow for user %s in %s", user_id, current_dir)
    else:
        logger.warning("Build workflow preparation failed for user %s: %s", user_id, message)


async def check_build_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if message is part of build workflow. Returns True if handled."""
    if not update.effective_user or not update.message or not update.message.text:
        return False
    
    user_id = update.effective_user.id
    
    # Check if user is in build workflow
    if user_id not in build_state:
        return False
    
    # Check if state is too old (10 minutes)
    if time.time() - build_state[user_id]['timestamp'] > 600:
        del build_state[user_id]
        return False
    
    selection = update.message.text.strip()
    current_step = build_state[user_id]['step']
    
    # Step 1: Repository selection
    if current_step == 'select_repo':
        repos = build_state[user_id]['repos']
        selected_repo = None
        
        # Check if selection is a number
        if selection.isdigit():
            position = int(selection)
            if 1 <= position <= len(repos):
                selected_repo = repos[position - 1]
        else:
            # Try to match by name
            for repo_path in repos:
                repo_name = os.path.basename(repo_path)
                if selection.lower() in repo_name.lower():
                    selected_repo = repo_path
                    break
        
        if not selected_repo:
            await update.message.reply_text(
                f"❌ Invalid selection. Please reply with a number (1-{len(repos)}) or repository name."
            )
            return True
        
        # Read package.json to get available scripts
        package_json_path = os.path.join(selected_repo, 'package.json')
        
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            scripts = package_data.get('scripts', {})
            
            if not scripts:
                await update.message.reply_text(
                    f"❌ No scripts found in package.json for {os.path.basename(selected_repo)}"
                )
                del build_state[user_id]
                return True
            
            # Filter for build-related scripts (android, build, etc.)
            build_scripts = {k: v for k, v in scripts.items() if any(
                keyword in k.lower() for keyword in ['android', 'build', 'release', 'debug']
            )}
            
            if not build_scripts:
                # Show all scripts if no build-specific ones found
                build_scripts = scripts
            
            # Update state - store the FILTERED scripts that we're showing
            build_state[user_id].update({
                'selected_repo': selected_repo,
                'scripts': build_scripts,  # Store filtered scripts, not all scripts
                'step': 'select_script',
                'timestamp': time.time()
            })
            
            # Build message with available scripts
            repo_name = os.path.basename(selected_repo)
            message = f"✅ Selected: {repo_name}\n\n"
            message += f"📋 Available npm scripts:\n\n"
            
            for i, (script_name, script_cmd) in enumerate(build_scripts.items(), 1):
                message += f"{i}. npm run {script_name}\n"
                message += f"   → {script_cmd[:60]}{'...' if len(script_cmd) > 60 else ''}\n\n"
            
            message += f"💡 Reply with the number or script name to execute.\n\nExample: 1 or android"
            
            await update.message.reply_text(message)
            logger.info(f"Showed {len(build_scripts)} scripts for {repo_name}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading package.json: {str(e)}")
            logger.error(f"Error reading package.json: {e}")
            del build_state[user_id]
        
        return True
    
    # Step 2: Script selection and execution
    elif current_step == 'select_script':
        scripts = build_state[user_id]['scripts']
        selected_repo = build_state[user_id]['selected_repo']
        selected_script = None
        
        # Check if selection is a number
        script_list = list(scripts.keys())
        if selection.isdigit():
            position = int(selection)
            if 1 <= position <= len(script_list):
                selected_script = script_list[position - 1]
        else:
            # Try to match by script name
            for script_name in script_list:
                if selection.lower() in script_name.lower():
                    selected_script = script_name
                    break
        
        if not selected_script:
            await update.message.reply_text(
                f"❌ Invalid selection. Please reply with a number (1-{len(script_list)}) or script name."
            )
            return True
        
        # Execute the build command
        await execute_build_command(update, context, selected_repo, selected_script)
        
        # Clear state after execution starts
        del build_state[user_id]
        return True
    
    return False


async def execute_build_command(update: Update, context: ContextTypes.DEFAULT_TYPE, repo_path: str, script_name: str):
    """Execute the build command in a new terminal window with screenshot monitoring."""
    repo_name = os.path.basename(repo_path)
    system = platform.system()
    
    try:
        # Determine if it's a debug or release build
        is_release = 'release' in script_name.lower()
        build_type = 'release' if is_release else 'debug'
        
        # Run the build command directly — no .bat generation to avoid
        # shell injection via malicious package.json script names.
        import re
        if not re.match(r'^[a-zA-Z0-9:_\-]+$', script_name):
            await update.message.reply_text(
                f"Blocked: script name `{script_name}` contains unsafe characters."
            )
            return

        if system == "Windows":
            window_title = f"Build: {repo_name} - {script_name}"

            # Run npm directly without shell interpolation
            subprocess.Popen(
                ["cmd.exe", "/c", "npm", "run", script_name],
                cwd=repo_path,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )

            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

            # Store monitor params for the screenshot confirmation callback
            build_monitor_state[user_id] = {
                "window_title": window_title,
                "repo_path": repo_path,
                "build_type": build_type,
                "chat_id": chat_id,
                "user_id": user_id,
            }

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📸 Yes, send screenshots",
                        callback_data=f"build_screenshot_yes_{user_id}",
                    ),
                    InlineKeyboardButton(
                        "🚫 No thanks",
                        callback_data=f"build_screenshot_no_{user_id}",
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🚀 Build started in new Command Prompt window!\n\n"
                f"Repository: {repo_name}\n"
                f"Command: npm run {script_name}\n"
                f"Build Type: {build_type}\n\n"
                f"Do you want me to send screenshots every minute to track progress?",
                reply_markup=reply_markup,
            )
            
        else:
            # Linux/Mac — run npm directly (script_name already validated above)
            if system == "Darwin":  # macOS
                subprocess.Popen(["npm", "run", script_name], cwd=repo_path)
            else:  # Linux
                subprocess.Popen(["npm", "run", script_name], cwd=repo_path)
            
            await update.message.reply_text(
                f"🚀 Build started in new terminal window!\n\n"
                f"Repository: {repo_name}\n"
                f"Command: npm run {script_name}\n"
                f"Build Type: {build_type}\n\n"
                f"📺 Watch the build progress in the opened window.\n"
                f"⏱️ This may take several minutes.\n\n"
                f"I'll check for the APK when you're ready.\n"
                f"Use /getapk to retrieve it after build completes."
            )
        
        logger.info(f"Started build in new terminal: npm run {script_name} in {repo_path}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error starting build: {str(e)}")
        logger.error(f"Error in execute_build_command: {e}")


async def monitor_build_window(bot, chat_id: int, user_id: int, window_title: str, repo_path: str, build_type: str):
    """Send periodic full-screen screenshots to track build progress.

    Stores itself in ``build_screenshot_tasks[user_id]`` (done by the caller).
    Cleans up that entry when it finishes or is cancelled.
    """
    max_screenshots = 20  # up to 20 minutes

    try:
        await asyncio.sleep(5)  # brief wait for the terminal window to open

        logger.info("Starting build screenshot monitoring for window: %s", window_title)

        for i in range(max_screenshots):
            screenshot = capture_full_screen()
            if screenshot:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=screenshot,
                    caption=f"📸 Build Progress (Update #{i + 1} of {max_screenshots})",
                )
                logger.info("Sent build screenshot #%d", i + 1)
            else:
                logger.warning("Failed to capture build screenshot #%d", i + 1)

            await asyncio.sleep(60)

        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"⏱️ Screenshot monitoring stopped after {max_screenshots} minutes.\n\n"
                "Use /getapk to retrieve the APK when the build completes."
            ),
        )

    except asyncio.CancelledError:
        logger.info("Build screenshot monitoring cancelled for user %d", user_id)
        raise
    except Exception as exc:
        logger.error("Error in monitor_build_window: %s", exc, exc_info=True)
    finally:
        build_screenshot_tasks.pop(user_id, None)




@safe_command
async def stopbuildscreenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stopbuildscreenshot — cancel active build screenshot monitoring."""
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    task = build_screenshot_tasks.pop(user_id, None)
    build_monitor_state.pop(user_id, None)
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("📸 Screenshot monitoring stopped.")
    else:
        await update.message.reply_text("No active screenshot monitoring to stop.")


def capture_full_screen():
    """Capture full screen screenshot."""
    try:
        import pyautogui
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
        
    except Exception as e:
        logger.error(f"Error capturing full screen screenshot: {e}")
        return None


def capture_window_screenshot(window):
    """Capture screenshot of a specific window."""
    try:
        # Get window position and size
        left, top, width, height = window.left, window.top, window.width, window.height
        
        # Use PIL to capture screenshot
        from PIL import ImageGrab
        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
        
    except Exception as e:
        logger.error(f"Error capturing window screenshot: {e}")
        return None




async def find_and_send_apk(update: Update, context: ContextTypes.DEFAULT_TYPE, repo_path: str, build_type: str):
    """Find the APK file and send it via Telegram."""
    try:
        # Common APK locations
        apk_search_paths = [
            os.path.join(repo_path, 'android', 'app', 'build', 'outputs', 'apk', build_type),
            os.path.join(repo_path, 'android', 'app', 'build', 'outputs', 'apk', build_type.capitalize()),
        ]
        
        apk_file = None
        
        # Search for APK file
        for search_path in apk_search_paths:
            if os.path.exists(search_path):
                for file in os.listdir(search_path):
                    if file.endswith('.apk'):
                        apk_file = os.path.join(search_path, file)
                        break
                if apk_file:
                    break
        
        if not apk_file:
            await update.message.reply_text(
                f"⚠️ Build completed but APK file not found in expected locations:\n\n"
                + "\n".join(f"• {path}" for path in apk_search_paths) +
                f"\n\nPlease check the build output folder manually."
            )
            return
        
        # Get file info
        file_size = os.path.getsize(apk_file)
        file_size_mb = file_size / (1024 * 1024)
        
        await update.message.reply_text(
            f"📦 Found APK file!\n\n"
            f"File: {os.path.basename(apk_file)}\n"
            f"Size: {file_size_mb:.2f} MB\n"
            f"Path: {apk_file}\n\n"
            f"Uploading to Telegram..."
        )
        
        # Check file size (Telegram limit is 50MB for bots)
        if file_size_mb > 50:
            # Show upload options to user
            user_id = update.effective_user.id
            
            # File too large for Telegram - let user choose upload method
            large_file_upload_state[user_id] = {
                'file_path': apk_file,
                'file_size_mb': file_size_mb,
                'timestamp': time.time(),
                'source': 'build'
            }
            
            # Create inline keyboard with options
            keyboard = [
                [
                    InlineKeyboardButton("⚡ TempFile (Auto-delete)", callback_data=f"upload_tempfile_{user_id}"),
                ],
                [
                    InlineKeyboardButton("☁️ Dropbox (Permanent)", callback_data=f"upload_dropbox_{user_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ APK file is too large ({file_size_mb:.2f} MB) for Telegram (max 50 MB).\n\n"
                f"📤 Choose upload method:\n\n"
                f"⚡ TempFile.org\n"
                f"  • Fast upload (max 100MB)\n"
                f"  • Auto-deletes after {Config.UPLOAD_EXPIRY_TIME}\n"
                f"  • No setup required\n\n"
                f"☁️ Dropbox\n"
                f"  • Unlimited file size\n"
                f"  • Permanent storage\n"
                f"  • Requires DROPBOX_ACCESS_TOKEN in .env\n\n"
                f"Select an option below:",
                reply_markup=reply_markup
            )
            
            return
        
        # Send the APK file
        with open(apk_file, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(apk_file),
                caption=f"✅ {os.path.basename(repo_path)} - {build_type.capitalize()} Build"
            )
        
        logger.info(f"Sent APK file: {apk_file}")
        
        await update.message.reply_text(
            f"✅ Build workflow completed!\n\n"
            f"APK file sent successfully."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error finding/sending APK: {str(e)}")
        logger.error(f"Error in find_and_send_apk: {e}")



# APK Retrieval Commands

async def getapk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getapk command - retrieve existing APK files."""
    if not update.message:
        return

    user_id = update.effective_user.id

    await update.message.reply_text("APK Retrieval Tool\n\nListing local repositories...")

    current_dir = str(file_manager.get_current_dir(user_id))
    success, message = prepare_apk_retrieval_workflow(user_id, current_dir)
    await update.message.reply_text(message)
    if success:
        logger.info("Prepared APK retrieval workflow for user %s in %s", user_id, current_dir)
    else:
        logger.warning("APK retrieval workflow preparation failed for user %s: %s", user_id, message)


async def check_apk_retrieval_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if message is part of APK retrieval workflow. Returns True if handled."""
    if not update.effective_user or not update.message or not update.message.text:
        return False
    
    user_id = update.effective_user.id
    
    # Check if user is in APK retrieval workflow
    if user_id not in apk_retrieval_state:
        return False
    
    # Check if state is too old (10 minutes)
    if time.time() - apk_retrieval_state[user_id]['timestamp'] > 600:
        del apk_retrieval_state[user_id]
        return False
    
    selection = update.message.text.strip()
    current_step = apk_retrieval_state[user_id]['step']
    
    # Step 1: Repository selection
    if current_step == 'select_repo':
        repos = apk_retrieval_state[user_id]['repos']
        selected_repo = None
        
        # Check if selection is a number
        if selection.isdigit():
            position = int(selection)
            if 1 <= position <= len(repos):
                selected_repo = repos[position - 1]
        else:
            # Try to match by name
            for repo_path in repos:
                repo_name = os.path.basename(repo_path)
                if selection.lower() in repo_name.lower():
                    selected_repo = repo_path
                    break
        
        if not selected_repo:
            await update.message.reply_text(
                f"❌ Invalid selection. Please reply with a number (1-{len(repos)}) or repository name."
            )
            return True
        
        # Check for APK output folder
        outputs_path = os.path.join(selected_repo, 'android', 'app', 'build', 'outputs')
        
        if not os.path.exists(outputs_path):
            await update.message.reply_text(
                f"❌ No build outputs found for {os.path.basename(selected_repo)}\n\n"
                f"Path doesn't exist:\n{outputs_path}\n\n"
                f"Build the app first using /build command."
            )
            del apk_retrieval_state[user_id]
            return True
        
        # List contents of outputs folder
        try:
            items = os.listdir(outputs_path)
            
            if not items:
                await update.message.reply_text(
                    f"❌ Build outputs folder is empty for {os.path.basename(selected_repo)}\n\n"
                    f"Build the app first using /build command."
                )
                del apk_retrieval_state[user_id]
                return True
            
            # Update state
            apk_retrieval_state[user_id].update({
                'selected_repo': selected_repo,
                'current_path': outputs_path,
                'step': 'navigate',
                'timestamp': time.time()
            })
            
            # Build message with folder contents
            repo_name = os.path.basename(selected_repo)
            message = f"✅ Selected: {repo_name}\n\n"
            message += f"📂 Contents of outputs folder:\n\n"
            
            folders = []
            files = []
            
            for item in items:
                item_path = os.path.join(outputs_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                else:
                    files.append(item)
            
            # Show folders first
            for i, folder in enumerate(sorted(folders), 1):
                message += f"{i}. 📁 {folder}/\n"
            
            # Show files
            for i, file in enumerate(sorted(files), len(folders) + 1):
                file_size = os.path.getsize(os.path.join(outputs_path, file))
                file_size_mb = file_size / (1024 * 1024)
                if file.endswith('.apk'):
                    message += f"{i}. 📦 {file} ({file_size_mb:.2f} MB)\n"
                else:
                    message += f"{i}. 📄 {file}\n"
            
            message += f"\n💡 Reply with:\n"
            message += f"• Number to navigate into folder or select APK\n"
            message += f"• 'back' to go up one level\n"
            message += f"• 'cancel' to exit\n\n"
            message += f"Current path: {outputs_path}"
            
            await update.message.reply_text(message)
            logger.info(f"Showed outputs folder for {repo_name}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading folder: {str(e)}")
            logger.error(f"Error reading outputs folder: {e}")
            del apk_retrieval_state[user_id]
        
        return True
    
    # Step 2: Navigation and file selection
    elif current_step == 'navigate':
        current_path = apk_retrieval_state[user_id]['current_path']
        selected_repo = apk_retrieval_state[user_id]['selected_repo']
        
        # Handle special commands
        if selection.lower() == 'cancel':
            await update.message.reply_text("❌ APK retrieval cancelled.")
            del apk_retrieval_state[user_id]
            return True
        
        if selection.lower() == 'back':
            # Go up one level
            parent_path = os.path.dirname(current_path)
            outputs_base = os.path.join(selected_repo, 'android', 'app', 'build', 'outputs')
            
            # Don't go above outputs folder
            if not parent_path.startswith(outputs_base):
                await update.message.reply_text(
                    "⚠️ Already at the top level (outputs folder).\n"
                    "Use 'cancel' to exit."
                )
                return True
            
            apk_retrieval_state[user_id]['current_path'] = parent_path
            apk_retrieval_state[user_id]['timestamp'] = time.time()
            
            # Show parent folder contents
            await show_folder_contents(update, user_id, parent_path)
            return True
        
        # Handle number selection
        if not selection.isdigit():
            await update.message.reply_text(
                "❌ Please reply with a number, 'back', or 'cancel'."
            )
            return True
        
        position = int(selection)
        
        try:
            items = os.listdir(current_path)
            folders = sorted([item for item in items if os.path.isdir(os.path.join(current_path, item))])
            files = sorted([item for item in items if os.path.isfile(os.path.join(current_path, item))])
            all_items = folders + files
            
            if position < 1 or position > len(all_items):
                await update.message.reply_text(
                    f"❌ Invalid selection. Please choose 1-{len(all_items)}."
                )
                return True
            
            selected_item = all_items[position - 1]
            selected_item_path = os.path.join(current_path, selected_item)
            
            # If it's a folder, navigate into it
            if os.path.isdir(selected_item_path):
                apk_retrieval_state[user_id]['current_path'] = selected_item_path
                apk_retrieval_state[user_id]['timestamp'] = time.time()
                
                await show_folder_contents(update, user_id, selected_item_path)
                return True
            
            # If it's a file, check if it's an APK
            if selected_item.endswith('.apk'):
                # Send the APK
                await send_apk_file(update, context, selected_item_path)
                del apk_retrieval_state[user_id]
                return True
            else:
                await update.message.reply_text(
                    f"⚠️ Selected file is not an APK: {selected_item}\n\n"
                    f"Please select an APK file (.apk extension)."
                )
                return True
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error in APK retrieval navigation: {e}")
            del apk_retrieval_state[user_id]
        
        return True
    
    return False


async def show_folder_contents(update: Update, user_id: int, folder_path: str):
    """Show contents of a folder during APK retrieval."""
    success, message = _format_apk_folder_contents(folder_path)
    await update.message.reply_text(message)
    if not success:
        logger.error("Error showing folder contents for %s: %s", folder_path, message)


async def send_apk_file(update: Update, context: ContextTypes.DEFAULT_TYPE, apk_path: str):
    """Send APK file via Telegram or file.io."""
    try:
        # Get file info
        file_size = os.path.getsize(apk_path)
        file_size_mb = file_size / (1024 * 1024)
        
        await update.message.reply_text(
            f"📦 Found APK file!\n\n"
            f"File: {os.path.basename(apk_path)}\n"
            f"Size: {file_size_mb:.2f} MB\n"
            f"Path: {apk_path}\n\n"
            f"Preparing to send..."
        )
        
        # Check file size (Telegram limit is 50MB for bots)
        if file_size_mb > 50:
            # Show upload options to user
            user_id = update.effective_user.id
            
            # Store file info for callback
            large_file_upload_state[user_id] = {
                'file_path': apk_path,
                'file_size_mb': file_size_mb,
                'timestamp': time.time(),
                'source': 'getapk'
            }
            
            # File too large for Telegram - let user choose upload method
            keyboard = [
                [
                    InlineKeyboardButton("⚡ TempFile (Auto-delete)", callback_data=f"upload_tempfile_{user_id}"),
                ],
                [
                    InlineKeyboardButton("☁️ Dropbox (Permanent)", callback_data=f"upload_dropbox_{user_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ APK file is too large ({file_size_mb:.2f} MB) for Telegram (max 50 MB).\n\n"
                f"📤 Choose upload method:\n\n"
                f"⚡ TempFile.org\n"
                f"  • Fast upload (max 100MB)\n"
                f"  • Auto-deletes after {Config.UPLOAD_EXPIRY_TIME}\n"
                f"  • No setup required\n\n"
                f"☁️ Dropbox\n"
                f"  • Unlimited file size\n"
                f"  • Permanent storage\n"
                f"  • Requires DROPBOX_ACCESS_TOKEN in .env\n\n"
                f"Select an option below:",
                reply_markup=reply_markup
            )
            
            return
        
        # Send the APK file via Telegram
        await update.message.reply_text("📤 Uploading to Telegram...")
        
        with open(apk_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(apk_path),
                caption=f"📦 {os.path.basename(apk_path)}"
            )
        
        logger.info(f"Sent APK file: {apk_path}")
        
        await update.message.reply_text(
            f"✅ APK file sent successfully!"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending APK: {str(e)}")
        logger.error(f"Error in send_apk_file: {e}")

# Scheduler Commands
