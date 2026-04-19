"""Windows autorun management via Task Scheduler.

This module intentionally manages only "start after user logon" behavior.
It does not implement true Windows Service hosting because the bot's UI
automation features require the logged-in desktop session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET

from pocket_desk_agent.app_paths import app_dir


TASK_NAME = "PocketDeskAgent"
TASK_DELAY_ISO = "PT30S"
TASK_DELAY_DISPLAY = "30 seconds"
TASK_DESCRIPTION = (
    "Starts Pocket Desk Agent in the background after you sign in to Windows. "
    "This is not a Windows Service and preserves desktop automation features."
)
_TASK_NS = {"task": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


@dataclass
class StartupStatus:
    """Represents the current autorun configuration state."""

    supported: bool
    configured: bool
    enabled: bool
    state: str
    message: str
    details: list[str] = field(default_factory=list)


class StartupManager:
    """Manage autorun-at-logon using Windows Task Scheduler."""

    def __init__(
        self,
        runner=None,
        platform_name: str | None = None,
        python_executable: str | None = None,
        home_dir: Path | None = None,
    ):
        self._runner = runner or self._default_runner
        self._platform_name = platform_name or sys.platform
        self._python_executable = python_executable or sys.executable
        self._home_dir = home_dir or Path.home()

    def is_supported(self) -> bool:
        """Return True when autorun management is available."""
        return self._platform_name == "win32" and self._schtasks_available()

    def get_status(self) -> StartupStatus:
        """Return the current autorun status."""
        if self._platform_name != "win32":
            return StartupStatus(
                supported=False,
                configured=False,
                enabled=False,
                state="unsupported",
                message="Automatic startup is currently supported on Windows only.",
            )

        if not self._schtasks_available():
            return StartupStatus(
                supported=False,
                configured=False,
                enabled=False,
                state="unsupported",
                message=(
                    "Automatic startup is unavailable because Task Scheduler "
                    "(`schtasks`) was not found on this system."
                ),
            )

        query = self._run_schtasks("/Query", "/TN", TASK_NAME, "/XML")
        if query.returncode != 0:
            if self._task_missing(query):
                return StartupStatus(
                    supported=True,
                    configured=False,
                    enabled=False,
                    state="disabled",
                    message=(
                        "Automatic startup is disabled. Pocket Desk Agent will "
                        "not launch automatically after Windows login."
                    ),
                )

            error_text = self._combined_output(query) or "Unknown error."
            return StartupStatus(
                supported=True,
                configured=False,
                enabled=False,
                state="broken",
                message="Automatic startup status could not be determined.",
                details=[error_text],
            )

        try:
            task_info = self._parse_task_xml(query.stdout)
        except ValueError as exc:
            return StartupStatus(
                supported=True,
                configured=True,
                enabled=False,
                state="broken",
                message="Automatic startup exists but its task definition is unreadable.",
                details=[str(exc)],
            )

        details = self._validate_task_configuration(task_info)
        task_is_disabled = not task_info.get("settings_enabled", True) or not task_info.get(
            "trigger_enabled", True
        )
        if task_is_disabled:
            details.append("The scheduled task exists but is disabled in Task Scheduler.")

        enabled = not details
        if enabled:
            return StartupStatus(
                supported=True,
                configured=True,
                enabled=True,
                state="enabled",
                message=(
                    "Automatic startup is enabled. Pocket Desk Agent will launch "
                    f"in the background about {TASK_DELAY_DISPLAY} after you sign in."
                ),
            )

        return StartupStatus(
            supported=True,
            configured=True,
            enabled=False,
            state="disabled" if task_is_disabled else "broken",
            message=(
                "Automatic startup needs attention. The scheduled task exists, "
                "but it is disabled or does not match the expected configuration."
            ),
            details=details,
        )

    def enable_startup(self) -> tuple[bool, str]:
        """Create or update the autorun task."""
        if self._platform_name != "win32":
            return False, "Automatic startup is currently supported on Windows only."
        if not self._schtasks_available():
            return False, (
                "Task Scheduler (`schtasks`) was not found. Automatic startup "
                "cannot be configured on this system."
            )

        self._working_dir().mkdir(parents=True, exist_ok=True)
        try:
            xml_text = self._build_task_xml()
        except RuntimeError as exc:
            return False, str(exc)

        xml_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-16",
                suffix=".xml",
                delete=False,
            ) as temp_file:
                temp_file.write(xml_text)
                xml_path = Path(temp_file.name)

            create = self._run_schtasks(
                "/Create",
                "/TN",
                TASK_NAME,
                "/XML",
                str(xml_path),
                "/F",
            )
            if create.returncode != 0:
                return False, (
                    "Could not enable automatic startup.\n"
                    + (self._combined_output(create) or "Task Scheduler returned an error.")
                )
        finally:
            if xml_path:
                xml_path.unlink(missing_ok=True)

        status = self.get_status()
        if status.enabled:
            return True, (
                "Automatic startup enabled. Pocket Desk Agent will launch in the "
                f"background about {TASK_DELAY_DISPLAY} after you sign in to Windows."
            )

        message = "Task Scheduler accepted the task, but validation did not pass."
        if status.details:
            message += "\n" + "\n".join(f"- {detail}" for detail in status.details)
        return False, message

    def disable_startup(self) -> tuple[bool, str]:
        """Remove the autorun task."""
        if self._platform_name != "win32":
            return False, "Automatic startup is currently supported on Windows only."
        if not self._schtasks_available():
            return False, (
                "Task Scheduler (`schtasks`) was not found. Automatic startup "
                "cannot be managed on this system."
            )

        delete = self._run_schtasks("/Delete", "/TN", TASK_NAME, "/F")
        if delete.returncode != 0 and not self._task_missing(delete):
            return False, (
                "Could not disable automatic startup.\n"
                + (self._combined_output(delete) or "Task Scheduler returned an error.")
            )

        return True, "Automatic startup disabled."

    def configure_interactive(self) -> int:
        """Interactively enable or disable autorun."""
        status = self.get_status()
        print("\nAutomatic Background Startup")
        print("-" * 40)
        print(
            "Pocket Desk Agent can start automatically in the background after "
            "you sign in to Windows."
        )
        print("This is not a Windows Service.")
        print(
            "Startup-at-logon keeps screenshots, OCR, Claude Desktop control, "
            "and VS Code automation available because the bot runs in your "
            "logged-in desktop session."
        )

        if not status.supported:
            print(f"\n{status.message}")
            return 0

        print(f"\nCurrent status: {status.message}")
        if status.details:
            for detail in status.details:
                print(f"  - {detail}")

        if status.enabled:
            answer = input("\nDisable automatic startup? [y/N]: ").strip().lower()
            if answer in ("y", "yes"):
                success, message = self.disable_startup()
                print(f"\n{message}")
                return 0 if success else 1
            print("\nAutomatic startup left enabled.")
            return 0

        prompt = (
            "\nEnable automatic startup after Windows login? [y/N]: "
            if not status.configured
            else "\nRepair and enable automatic startup now? [y/N]: "
        )
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            success, message = self.enable_startup()
            print(f"\n{message}")
            return 0 if success else 1

        print("\nAutomatic startup remains disabled.")
        print("You can change this later with: pdagent startup configure")
        return 0

    def _build_task_xml(self) -> str:
        """Build the Task Scheduler XML definition."""
        user_id = self._get_current_user()
        if not user_id:
            raise RuntimeError(
                "Could not determine the current Windows user for Task Scheduler."
            )

        command_path = self._resolve_python_command()
        start_boundary = datetime.now().replace(microsecond=0).isoformat()
        working_dir = str(self._working_dir())

        return textwrap.dedent(
            f"""\
            <?xml version="1.0" encoding="UTF-16"?>
            <Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
              <RegistrationInfo>
                <Description>{TASK_DESCRIPTION}</Description>
                <URI>\\{TASK_NAME}</URI>
              </RegistrationInfo>
              <Principals>
                <Principal id="Author">
                  <UserId>{self._xml_escape(user_id)}</UserId>
                  <LogonType>InteractiveToken</LogonType>
                  <RunLevel>LeastPrivilege</RunLevel>
                </Principal>
              </Principals>
              <Settings>
                <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
                <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
                <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
                <AllowHardTerminate>true</AllowHardTerminate>
                <StartWhenAvailable>true</StartWhenAvailable>
                <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
                <IdleSettings>
                  <StopOnIdleEnd>false</StopOnIdleEnd>
                  <RestartOnIdle>false</RestartOnIdle>
                </IdleSettings>
                <AllowStartOnDemand>true</AllowStartOnDemand>
                <Enabled>true</Enabled>
                <Hidden>false</Hidden>
                <RunOnlyIfIdle>false</RunOnlyIfIdle>
                <WakeToRun>false</WakeToRun>
                <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
                <Priority>7</Priority>
              </Settings>
              <Triggers>
                <LogonTrigger>
                  <StartBoundary>{start_boundary}</StartBoundary>
                  <Enabled>true</Enabled>
                  <Delay>{TASK_DELAY_ISO}</Delay>
                  <UserId>{self._xml_escape(user_id)}</UserId>
                </LogonTrigger>
              </Triggers>
              <Actions Context="Author">
                <Exec>
                  <Command>{self._xml_escape(command_path)}</Command>
                  <Arguments>-m pocket_desk_agent.main</Arguments>
                  <WorkingDirectory>{self._xml_escape(working_dir)}</WorkingDirectory>
                </Exec>
              </Actions>
            </Task>
            """
        )

    @staticmethod
    def _xml_escape(value: str) -> str:
        """Escape values inserted into Task Scheduler XML."""
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _validate_task_configuration(self, task_info: dict[str, str]) -> list[str]:
        """Return human-readable differences from the expected task definition."""
        issues: list[str] = []

        expected_command = self._resolve_python_command()
        expected_working_dir = str(self._working_dir())
        actual_command = task_info.get("command", "")
        actual_arguments = task_info.get("arguments", "")
        actual_working_dir = task_info.get("working_directory", "")
        actual_delay = task_info.get("delay", "")

        if actual_command.lower() != expected_command.lower():
            issues.append(
                f"Expected command '{expected_command}', found '{actual_command or '(missing)'}'."
            )
        if actual_arguments.strip() != "-m pocket_desk_agent.main":
            issues.append(
                "Expected arguments '-m pocket_desk_agent.main', "
                f"found '{actual_arguments or '(missing)'}'."
            )
        if Path(actual_working_dir or "").as_posix().lower() != Path(
            expected_working_dir
        ).as_posix().lower():
            issues.append(
                f"Expected working directory '{expected_working_dir}', found "
                f"'{actual_working_dir or '(missing)'}'."
            )
        if actual_delay != TASK_DELAY_ISO:
            issues.append(
                f"Expected startup delay '{TASK_DELAY_ISO}', found '{actual_delay or '(missing)'}'."
            )

        return issues

    def _parse_task_xml(self, xml_text: str) -> dict[str, str | bool]:
        """Parse the Task Scheduler XML definition."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ValueError(f"Task XML could not be parsed: {exc}") from exc

        def find_text(path: str) -> str:
            node = root.find(path, _TASK_NS)
            return (node.text or "").strip() if node is not None and node.text else ""

        return {
            "command": find_text(".//task:Actions/task:Exec/task:Command"),
            "arguments": find_text(".//task:Actions/task:Exec/task:Arguments"),
            "working_directory": find_text(".//task:Actions/task:Exec/task:WorkingDirectory"),
            "delay": find_text(".//task:Triggers/task:LogonTrigger/task:Delay"),
            "settings_enabled": find_text(".//task:Settings/task:Enabled").lower() != "false",
            "trigger_enabled": find_text(".//task:Triggers/task:LogonTrigger/task:Enabled").lower()
            != "false",
        }

    def _get_current_user(self) -> str:
        """Return the current Windows user in DOMAIN\\User form."""
        result = self._runner(["whoami"])
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _resolve_python_command(self) -> str:
        """Return the preferred interpreter path for background startup."""
        current = Path(self._python_executable)
        if current.name.lower() == "pythonw.exe":
            return str(current)

        pythonw = current.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)

        return str(current)

    def _working_dir(self) -> Path:
        """Return the autorun working directory."""
        return app_dir(self._home_dir)

    def _run_schtasks(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run schtasks with the provided arguments."""
        return self._runner(["schtasks", *args])

    def _schtasks_available(self) -> bool:
        """Return True when the schtasks executable exists."""
        return shutil.which("schtasks") is not None

    @staticmethod
    def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
        """Combine stdout and stderr for error reporting."""
        return "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
        ).strip()

    @staticmethod
    def _task_missing(result: subprocess.CompletedProcess[str]) -> bool:
        """Return True when schtasks reports that the task does not exist."""
        text = StartupManager._combined_output(result).lower()
        return (
            "cannot find the file specified" in text
            or "cannot find the path specified" in text
            or "does not exist" in text
        )

    @staticmethod
    def _default_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a subprocess command and capture output as text."""
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
