# Local Development Guide

This guide covers local setup, day-to-day development commands, and runtime behavior when working from source.

---

## Requirements

- Python 3.11+
- Git
- Windows for desktop automation features such as screenshots, OCR interaction, and window control

File system features and much of the Gemini integration are cross-platform, but the full automation feature set is designed for Windows.

---

## Setup From Source

1. Clone the repository:

   ```bash
   git clone https://github.com/techgniouss/pocket-desk-agent.git
   cd pocket-desk-agent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

3. Install the project in editable mode with development tools:

   ```bash
   pip install -e ".[dev]"
   ```

4. Configure the bot:

   ```bash
   pdagent configure
   ```

   The setup wizard configures Telegram credentials, authorized users, and optional Gemini authentication. On Windows it can also configure startup after login. Configuration is stored in `~/.pdagent/config`.

5. Install OCR support if needed:

   ```bash
   pdagent setup
   ```

   This checks for Tesseract OCR, which is required for OCR-driven commands such as `/findtext` and `/smartclick`.

---

## Running Locally

```bash
pdagent
# or
python -m pocket_desk_agent.main
```

Use foreground mode during development so logs and reload behavior stay visible.

### CLI Commands

| Command | Description |
|---|---|
| `pdagent` | Run in the foreground |
| `pdagent start` | Start the background daemon |
| `pdagent stop` | Stop the background daemon |
| `pdagent restart` | Restart the daemon |
| `pdagent status` | Show daemon status |
| `pdagent configure` | Run the setup wizard |
| `pdagent setup` | Check and install system dependencies |
| `pdagent startup enable` | Enable startup after Windows login |
| `pdagent startup disable` | Disable startup after Windows login |
| `pdagent startup status` | Show startup status |
| `pdagent startup configure` | Configure startup interactively |
| `pdagent auth` | Manage Gemini authentication credentials |
| `pdagent version` | Show the installed version |

---

## Development Behavior

### Live Reloading

When the project is run from a git checkout, `main.py` enables a file-watching reloader that monitors Python source files and restarts the process automatically on change.

- Git checkout: reloader enabled
- Installed package: reloader disabled

This keeps the development experience responsive without adding unnecessary overhead in normal installed usage.

### Logging

Logs are written to both the console and `bot.log` in the working directory.

For more verbose output, set:

```ini
LOG_LEVEL=DEBUG
```

---

## Tests and Tooling

```bash
make test
make lint
make format
```

### Make Targets

| Command | Description |
|---|---|
| `make install` | Install the project in editable mode with development dependencies |
| `make run` | Run the bot in the foreground |
| `make dev` | Install and run in one step |
| `make test` | Run `pytest -v` |
| `make lint` | Run `flake8` and `mypy` |
| `make format` | Format code with `black` |
| `make build` | Build the source distribution and wheel |
| `make clean` | Remove build artifacts and caches |

---

## Resource Profile

Approximate idle runtime footprint:

| Metric | Value |
|---|---|
| Idle RAM | ~55-70 MB |
| Idle CPU | <0.5% |
| Startup time | ~2-3 seconds |

Heavy dependencies such as OpenCV, NumPy, Dropbox, and Tesseract are loaded on demand rather than at startup.

---

## Related Documentation

- [README.md](../README.md)
- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)
- [COMMANDS.md](COMMANDS.md)
