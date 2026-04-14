# Contributing to Pocket Desk Agent

Thank you for your interest in contributing. Pocket Desk Agent is designed to be a powerful, secure, and extensible tool for local desktop automation, with optional Gemini-powered AI features.

## Development Setup

1. **Clone & install**:
   ```bash
   git clone https://github.com/techgniouss/pocket-desk-agent.git
   cd pocket-desk-agent
   pip install -e ".[dev]"
   ```

2. **Configure credentials**: Follow [README.md](README.md) to set up your `.env` file, or run:
   ```bash
   pdagent configure
   ```

3. **Run in dev mode**:
   ```bash
   pdagent
   # or equivalently:
   python -m pocket_desk_agent.main
   ```

For the full local development guide (virtual environments, live reloader, make targets, resource profile), see **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**.

## Coding Standards

- **Formatter**: `black` — run `make format` before committing.
- **Linter**: `flake8` + `mypy` — run `make lint` to check types and style.
- **Type hints**: All new functions must include type annotations.
- **Logging**: Use `logger = logging.getLogger(__name__)` at module level. Never use `print()`.
- **Path handling**: Always use `pathlib.Path`, never raw strings.
- **Windows-only imports**: Wrap with `if platform.system() == "Windows":`.
- **Heavy dependencies**: Import inside handler functions, not at module level. This keeps idle RAM low (~55-70 MB). See `CLAUDE.md` for the full lazy-import convention.

## Adding a New Command

1. **Write the handler** in the appropriate module under `pocket_desk_agent/handlers/` (pick the domain that fits, or create a new module for a new domain). Every handler **must** use the `@safe_command` decorator — it enforces authorization, rate limiting, and exception safety automatically.

   ```python
   from telegram import Update
   from telegram.ext import ContextTypes
   from pocket_desk_agent.handlers._shared import safe_command

   @safe_command
   async def mycommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       args = context.args  # list of whitespace-split args after /mycommand
       await update.message.reply_text("Result here")
   ```

   **Never** add manual `is_user_allowed()` checks — `@safe_command` handles authorization.

2. **Export it** from `pocket_desk_agent/handlers/__init__.py`.

3. **Register it** in `pocket_desk_agent/command_map.py`:
   ```python
   ("mycommand", handlers.mycommand_command, "Short description"),
   ```

4. **Document it** in `docs/COMMANDS.md` and the README quick reference.

5. *(Optional)* If the command is expensive or sensitive, add a custom rate limit in `rate_limiter.py`:
   ```python
   rate_limiter.set_limit("mycommand", calls=3, window=60)
   ```

## Adding a New Gemini AI Tool

1. Implement the function in `file_manager.py` or a new module.
2. Add the JSON tool definition to `gemini_client.py` → `_get_api_tools()`.
3. Handle the tool call in `gemini_client.py` → `send_message()`.
4. Add the tool name to the `_ALLOWED_TOOLS` frozenset in `gemini_client.py`.

## Testing

Run the test suite with:
```bash
make test
```

UI automation features require Windows with Tesseract OCR installed, as `pywinauto` and `pytesseract` are platform-specific.

## Security Policy

- **Never commit** `.env`, OAuth token files, or `~/.pdagent/credentials`.
- **Always use** `FileManager._is_safe_path()` for any new file operations. It uses `Path.relative_to()` — never roll your own path validation.
- **Never expose** `subprocess` or shell access to the Gemini AI — this is a prompt-injection-to-RCE vector.
- `@safe_command` handles authorization on every handler. Do not add duplicate `is_user_allowed()` calls.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
