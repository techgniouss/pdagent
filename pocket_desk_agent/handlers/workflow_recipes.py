"""Workflow recipe commands and execution helpers."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.automation_utils import find_text_in_image, validate_command_name
from pocket_desk_agent.command_registry import get_registry
from pocket_desk_agent.desktop_adapters import (
    activate_adapter_window,
    find_adapter_window,
    list_desktop_adapters,
    window_region,
)
from pocket_desk_agent.recipe_registry import (
    RecipeStep,
    STEP_KIND_CLAUDE_PROMPT,
    STEP_KIND_COMMAND,
    STEP_KIND_NOTIFY,
    STEP_KIND_WAIT_SECONDS,
    STEP_KIND_WAIT_TEXT,
    get_recipe_registry,
)
from pocket_desk_agent.scheduling_utils import parse_duration_spec

logger = logging.getLogger(__name__)


_WAIT_TEXT_SCOPE_PATTERN = re.compile(r"(?:^|\s)scope=([a-zA-Z_]+)(?:\s|$)")
_WAIT_TEXT_TIMEOUT_PATTERN = re.compile(r"(?:^|\s)timeout=([a-zA-Z0-9]+)(?:\s|$)")
_WAIT_TEXT_INTERVAL_PATTERN = re.compile(r"(?:^|\s)interval=([a-zA-Z0-9]+)(?:\s|$)")
_TEMPLATE_VAR_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _parse_template_variables(raw_args: list[str]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for token in raw_args:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        cleaned_key = key.strip()
        cleaned_value = value.strip()
        if not cleaned_key:
            continue
        variables[cleaned_key] = cleaned_value
    return variables


def _render_template(template: str, variables: dict[str, str]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return variables[key]
        missing.append(key)
        return match.group(0)

    rendered = _TEMPLATE_VAR_PATTERN.sub(_replace, template)
    return rendered, missing


async def recipecreate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipecreate <name>."""
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: /recipecreate <name>\nExample: /recipecreate claude_fix"
        )
        return

    name = context.args[0].strip()
    if not validate_command_name(name):
        await update.message.reply_text(
            "Recipe name can include letters, numbers, and underscore only."
        )
        return

    success, message = get_recipe_registry().create_recipe(name)
    await update.message.reply_text(message)
    if success:
        await update.message.reply_text(
            "Add steps with:\n"
            "/recipeaddcommand <name> <saved_custom_command>\n"
            "/recipeaddclaude <name> <prompt template>\n"
            "/recipeaddwait <name> <duration>\n"
            "/recipeaddwaittext <name> <text> | timeout=2m scope=claude interval=10s\n"
            "/recipeaddnotify <name> <message>"
        )


async def recipeaddcommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeaddcommand <recipe_name> <saved_custom_command>."""
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /recipeaddcommand <recipe_name> <saved_custom_command>"
        )
        return

    recipe_name = context.args[0].strip()
    command_name = context.args[1].strip()
    if not get_registry().command_exists(command_name):
        await update.message.reply_text(
            f"Custom command '{command_name}' not found. Use /listcommands first."
        )
        return

    step = RecipeStep(kind=STEP_KIND_COMMAND, payload=command_name)
    success, message = get_recipe_registry().append_step(recipe_name, step)
    await update.message.reply_text(message)


async def recipeaddclaude_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeaddclaude <recipe_name> <prompt template>."""
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /recipeaddclaude <recipe_name> <prompt>\n"
            "Example: /recipeaddclaude claude_fix Review repo {repo} on branch {branch}"
        )
        return

    recipe_name = context.args[0].strip()
    prompt = " ".join(context.args[1:]).strip()
    step = RecipeStep(kind=STEP_KIND_CLAUDE_PROMPT, payload=prompt)
    success, message = get_recipe_registry().append_step(recipe_name, step)
    await update.message.reply_text(message)


async def recipeaddwait_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeaddwait <recipe_name> <duration>."""
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /recipeaddwait <recipe_name> <duration>\nExample: /recipeaddwait claude_fix 15s"
        )
        return

    recipe_name = context.args[0].strip()
    duration_spec = context.args[1].strip().lower()
    delta = parse_duration_spec(duration_spec)
    if not delta:
        await update.message.reply_text("Invalid duration. Use values like 10s, 2m, or 1h.")
        return

    seconds = int(delta.total_seconds())
    step = RecipeStep(
        kind=STEP_KIND_WAIT_SECONDS,
        payload=str(seconds),
        metadata={"duration_spec": duration_spec},
    )
    success, message = get_recipe_registry().append_step(recipe_name, step)
    await update.message.reply_text(message)


async def recipeaddwaittext_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeaddwaittext with scoped OCR polling options."""
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /recipeaddwaittext <recipe_name> <text> | timeout=2m scope=claude interval=10s"
        )
        return

    recipe_name = context.args[0].strip()
    raw_tail = update.message.text.partition(" ")[2].strip()
    raw_payload = raw_tail[len(recipe_name) :].strip()
    if not raw_payload:
        await update.message.reply_text(
            "Please provide wait text and options.\n"
            "Example: /recipeaddwaittext claude_fix Ready to code | timeout=2m scope=claude interval=10s"
        )
        return

    if "|" not in raw_payload:
        await update.message.reply_text(
            "Use '|' to separate text from options.\n"
            "Example: /recipeaddwaittext claude_fix Ready | timeout=2m scope=claude"
        )
        return

    text_part, _, option_part = raw_payload.partition("|")
    wait_text = text_part.strip()
    options = option_part.strip()
    if not wait_text:
        await update.message.reply_text("Wait text cannot be empty.")
        return

    timeout_match = _WAIT_TEXT_TIMEOUT_PATTERN.search(options)
    if not timeout_match:
        await update.message.reply_text("Missing required option: timeout=<duration>.")
        return

    timeout_delta = parse_duration_spec(timeout_match.group(1).strip())
    if not timeout_delta:
        await update.message.reply_text("Invalid timeout value. Example: timeout=2m")
        return

    interval_seconds = 10
    interval_match = _WAIT_TEXT_INTERVAL_PATTERN.search(options)
    if interval_match:
        interval_delta = parse_duration_spec(interval_match.group(1).strip())
        if not interval_delta:
            await update.message.reply_text("Invalid interval value. Example: interval=10s")
            return
        interval_seconds = max(1, int(interval_delta.total_seconds()))

    scope = "screen"
    scope_match = _WAIT_TEXT_SCOPE_PATTERN.search(options)
    if scope_match:
        scope = scope_match.group(1).strip().lower()
    if scope not in {"screen", *list_desktop_adapters()}:
        await update.message.reply_text(
            f"Unsupported scope '{scope}'. Use screen or one of: {', '.join(list_desktop_adapters())}"
        )
        return

    step = RecipeStep(
        kind=STEP_KIND_WAIT_TEXT,
        payload=wait_text,
        metadata={
            "scope": scope,
            "timeout_seconds": int(timeout_delta.total_seconds()),
            "interval_seconds": interval_seconds,
        },
    )
    success, message = get_recipe_registry().append_step(recipe_name, step)
    await update.message.reply_text(message)


async def recipeaddnotify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeaddnotify <recipe_name> <message template>."""
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /recipeaddnotify <recipe_name> <message>"
        )
        return

    recipe_name = context.args[0].strip()
    message = " ".join(context.args[1:]).strip()
    step = RecipeStep(kind=STEP_KIND_NOTIFY, payload=message)
    success, response = get_recipe_registry().append_step(recipe_name, step)
    await update.message.reply_text(response)


async def recipelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipelist."""
    if not update.message:
        return

    recipes = get_recipe_registry().list_recipes()
    if not recipes:
        await update.message.reply_text("No workflow recipes found. Create one with /recipecreate.")
        return

    lines = ["Workflow recipes:\n"]
    for recipe in recipes:
        lines.append(
            f"- {recipe.name}: {len(recipe.steps)} steps, used {recipe.use_count} times"
        )
    await update.message.reply_text("\n".join(lines))


async def recipeshow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipeshow <name>."""
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("Usage: /recipeshow <name>")
        return

    recipe = get_recipe_registry().get_recipe(context.args[0].strip())
    if not recipe:
        await update.message.reply_text(f"Recipe '{context.args[0]}' not found.")
        return

    lines = [f"Recipe: {recipe.name}", ""]
    for index, step in enumerate(recipe.steps, start=1):
        details = step.payload
        if step.kind == STEP_KIND_WAIT_TEXT:
            details = (
                f"{step.payload} "
                f"[scope={step.metadata.get('scope', 'screen')}, "
                f"timeout={step.metadata.get('timeout_seconds', '?')}s, "
                f"interval={step.metadata.get('interval_seconds', '?')}s]"
            )
        lines.append(f"{index}. {step.kind}: {details}")
    await update.message.reply_text("\n".join(lines))


async def recipedelete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recipedelete <name>."""
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("Usage: /recipedelete <name>")
        return
    success, message = get_recipe_registry().delete_recipe(context.args[0].strip())
    await update.message.reply_text(message)


async def reciperun_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reciperun <name> [key=value ...]."""
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: /reciperun <recipe_name> [key=value ...]\n"
            "Example: /reciperun claude_fix repo=pdagent branch=main"
        )
        return

    recipe_name = context.args[0].strip()
    recipe = get_recipe_registry().get_recipe(recipe_name)
    if not recipe:
        await update.message.reply_text(f"Recipe '{recipe_name}' not found.")
        return
    if not recipe.steps:
        await update.message.reply_text(
            f"Recipe '{recipe.name}' has no steps yet. Add steps before running."
        )
        return

    variables = _parse_template_variables(context.args[1:])
    await update.message.reply_text(
        f"Running recipe '{recipe.name}' with {len(recipe.steps)} steps..."
    )
    ok, message = await _execute_recipe(recipe, variables, update, context)
    await update.message.reply_text(message)
    if ok:
        usage_saved = get_recipe_registry().mark_used(recipe.name)
        if not usage_saved:
            await update.message.reply_text(
                "Recipe run completed, but usage stats could not be saved."
            )
            logger.warning("Failed to persist recipe usage for '%s'", recipe.name)


async def _execute_recipe(recipe, variables: dict[str, str], update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, str]:
    from pocket_desk_agent.handlers.claude import ensure_claude_open, send_prompt_to_claude
    from pocket_desk_agent.handlers.scheduling import run_custom_actions

    user_id = update.effective_user.id
    registry = get_registry()

    for index, step in enumerate(recipe.steps, start=1):
        if step.kind == STEP_KIND_NOTIFY:
            text, missing = _render_template(step.payload, variables)
            if missing:
                return False, f"Recipe failed at step {index}: missing variables {sorted(set(missing))}"
            await context.bot.send_message(chat_id=user_id, text=text)
            continue

        if step.kind == STEP_KIND_WAIT_SECONDS:
            try:
                seconds = int(step.payload)
            except ValueError:
                return False, f"Recipe step {index} has invalid wait payload '{step.payload}'."
            await asyncio.sleep(max(0, seconds))
            continue

        if step.kind == STEP_KIND_COMMAND:
            command_name, missing = _render_template(step.payload, variables)
            if missing:
                return False, f"Recipe failed at step {index}: missing variables {sorted(set(missing))}"
            actions = registry.get_command(command_name)
            if not actions:
                return False, f"Recipe failed at step {index}: command '{command_name}' not found."
            await run_custom_actions(actions)
            continue

        if step.kind == STEP_KIND_CLAUDE_PROMPT:
            prompt, missing = _render_template(step.payload, variables)
            if missing:
                return False, f"Recipe failed at step {index}: missing variables {sorted(set(missing))}"
            window = ensure_claude_open()
            if not window:
                return False, f"Recipe failed at step {index}: Claude desktop window not found."
            try:
                window.activate()
            except Exception:
                pass
            await asyncio.sleep(1.0)
            send_prompt_to_claude(window, prompt)
            continue

        if step.kind == STEP_KIND_WAIT_TEXT:
            rendered_text, missing = _render_template(step.payload, variables)
            if missing:
                return False, f"Recipe failed at step {index}: missing variables {sorted(set(missing))}"
            matched = await _wait_for_text(
                rendered_text,
                scope=str(step.metadata.get("scope", "screen")).strip().lower(),
                timeout_seconds=int(step.metadata.get("timeout_seconds", 120) or 120),
                interval_seconds=max(1, int(step.metadata.get("interval_seconds", 10) or 10)),
            )
            if not matched:
                return False, f"Recipe step {index} timed out waiting for text: {rendered_text}"
            continue

        return False, f"Recipe failed at step {index}: unsupported step type '{step.kind}'."

    return True, f"Recipe '{recipe.name}' completed successfully."


async def _wait_for_text(
    search_text: str,
    *,
    scope: str,
    timeout_seconds: int,
    interval_seconds: int,
) -> bool:
    import pyautogui

    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() <= deadline:
        image = None
        if scope == "screen":
            image = pyautogui.screenshot()
        else:
            window = find_adapter_window(scope)
            if window:
                await activate_adapter_window(window)
                region = window_region(window)
                if region:
                    image = pyautogui.screenshot(region=region)

        if image is not None:
            matches = find_text_in_image(image, search_text)
            if matches:
                return True
        await asyncio.sleep(interval_seconds)
    return False
