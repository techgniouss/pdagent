"""Pocket Desk Agent — secure Telegram remote control for your PC."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pocket-desk-agent")
except PackageNotFoundError:
    # Running from source without `pip install -e .`
    __version__ = "0.0.0.dev"
