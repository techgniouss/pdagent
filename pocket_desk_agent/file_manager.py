"""File system manager for repository access."""

import os
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from pocket_desk_agent.app_paths import app_dir, legacy_app_dirs
from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file system access within approved directory."""

    _BLOCKED_DOWNLOAD_EXTENSIONS = frozenset(
        {".exe", ".msi", ".bat", ".cmd", ".ps1", ".com", ".scr"}
    )
    
    def __init__(self):
        self.approved_dirs = [Path(path) for path in Config.APPROVED_DIRECTORIES]
        
        # Always allow access to the default projects directory
        if Config.CLAUDE_DEFAULT_REPO_PATH:
            repo_path = Path(Config.CLAUDE_DEFAULT_REPO_PATH)
            if repo_path not in self.approved_dirs:
                self.approved_dirs.append(repo_path)

        if not self.approved_dirs:
            self.approved_dirs = [Path.home()]
                
        self.current_dirs = {}  # user_id -> current_directory
    
    @staticmethod
    def _protected_dirs() -> list[Path]:
        """Credential stores that are off limits even inside an approved directory.

        The default approved directory is the whole home folder, which holds the
        bot's own secrets (Telegram token, API keys, OAuth tokens) and the
        user's SSH/cloud credentials. File tools feed the AI provider, and a
        prompt injection could read — or, with a careless approval, overwrite —
        them, so they are denied regardless of what is approved.
        """
        home = Path.home()
        return [
            app_dir(),
            *legacy_app_dirs(),
            home / ".config" / "antigravity-chatbot",
            home / ".config" / "pdagent-gemini",
            home / ".ssh",
            home / ".gnupg",
            home / ".aws",
            home / ".azure",
            home / ".kube",
            home / ".config" / "gcloud",
        ]

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within any of the approved directories.

        Uses Path.is_relative_to() (Python 3.9+) instead of string prefix
        matching, which is vulnerable to directory-prefix attacks
        (e.g. /home/user/projects_evil passing /home/user/projects).
        Paths inside a protected credential directory are always refused.
        """
        try:
            resolved = path.resolve()
            for protected in self._protected_dirs():
                try:
                    resolved.relative_to(protected.resolve())
                    return False
                except ValueError:
                    continue
            for approved in self.approved_dirs:
                approved_resolved = approved.resolve()
                try:
                    resolved.relative_to(approved_resolved)
                    return True
                except ValueError:
                    continue
            return False
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False
    
    def get_current_dir(self, user_id: int) -> Path:
        """Get user's current directory."""
        if user_id not in self.current_dirs:
            # Default to the default repo path if available, else first approved directory
            if Config.CLAUDE_DEFAULT_REPO_PATH and Path(Config.CLAUDE_DEFAULT_REPO_PATH).exists():
                self.current_dirs[user_id] = Path(Config.CLAUDE_DEFAULT_REPO_PATH)
            else:
                self.current_dirs[user_id] = self.approved_dirs[0] if self.approved_dirs else Path.home()
        return self.current_dirs[user_id]

    @classmethod
    def is_blocked_download_file(cls, path: Path) -> bool:
        """Return True when the file extension is blocked for /getfile downloads."""
        return path.suffix.lower() in cls._BLOCKED_DOWNLOAD_EXTENSIONS

    def resolve_downloadable_file(self, user_id: int, path: str) -> tuple[bool, Path | str]:
        """Resolve a candidate file path for /getfile within the approved sandbox."""
        try:
            current = self.get_current_dir(user_id)

            if os.path.isabs(path):
                target = Path(path)
            else:
                target = current / path

            resolved = target.resolve()

            if not self._is_safe_path(resolved):
                return False, "Access denied: Path outside approved directory"

            if not resolved.exists():
                return False, f"File not found: {path}"

            if not resolved.is_file():
                return False, f"Not a file: {path}"

            return True, resolved
        except Exception as e:
            logger.error(f"Error resolving downloadable file: {e}")
            return False, f"Error: {str(e)}"
    
    def set_current_dir(self, user_id: int, path: str) -> Tuple[bool, str]:
        """Change user's current directory."""
        try:
            current = self.get_current_dir(user_id)
            
            # Handle absolute vs relative paths
            if os.path.isabs(path):
                new_path = Path(path)
            else:
                new_path = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(new_path):
                return False, "Access denied: Path outside approved directory"
            
            # Check if exists
            if not new_path.exists():
                return False, f"Directory not found: {path}"
            
            if not new_path.is_dir():
                return False, f"Not a directory: {path}"
            
            self.current_dirs[user_id] = new_path
            return True, str(new_path)
            
        except Exception as e:
            logger.error(f"Error changing directory: {e}")
            return False, f"Error: {str(e)}"
    
    def list_directory(self, user_id: int, path: Optional[str] = None) -> Tuple[bool, str]:
        """List contents of directory."""
        try:
            if path:
                current = self.get_current_dir(user_id)
                target = (current / path).resolve()
            else:
                target = self.get_current_dir(user_id)
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"Path not found: {path or '.'}"
            
            if not target.is_dir():
                return False, f"Not a directory: {path or '.'}"
            
            # List contents
            items = []
            dirs = []
            files = []
            
            for item in sorted(target.iterdir()):
                try:
                    if item.is_dir():
                        dirs.append(f"📁 {item.name}/")
                    else:
                        size = item.stat().st_size
                        size_str = self._format_size(size)
                        files.append(f"📄 {item.name} ({size_str})")
                except Exception:
                    continue
            
            items = dirs + files
            
            if not items:
                return True, f"📂 {target}\n\n(empty directory)"
            
            result = f"📂 {target}\n\n" + "\n".join(items[:50])
            if len(items) > 50:
                result += f"\n\n... and {len(items) - 50} more items"
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return False, f"Error: {str(e)}"
    
    def read_file(self, user_id: int, path: str, max_lines: int = 100) -> Tuple[bool, str]:
        """Read contents of a file."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"File not found: {path}"
            
            if not target.is_file():
                return False, f"Not a file: {path}"
            
            # Check file size
            size = target.stat().st_size
            if size > 1024 * 1024:  # 1MB limit
                return False, f"File too large: {self._format_size(size)} (max 1MB)"
            
            # Read file
            try:
                with open(target, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                return False, "Cannot read file: Binary or unsupported encoding"
            
            # Limit lines
            total_lines = len(lines)
            if total_lines > max_lines:
                content = ''.join(lines[:max_lines])
                result = f"📄 {target.name} (showing {max_lines}/{total_lines} lines)\n\n```\n{content}\n```\n\n... truncated"
            else:
                content = ''.join(lines)
                result = f"📄 {target.name} ({total_lines} lines)\n\n```\n{content}\n```"
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return False, f"Error: {str(e)}"
    
    # Directories that are huge, machine-generated, and never what a user is
    # looking for with /find. Skipping them keeps a search of the home folder fast.
    _SEARCH_SKIP_DIRS = frozenset({
        "node_modules", "__pycache__", "venv", "site-packages",
        "$recycle.bin", "system volume information",
    })
    _SEARCH_TIME_LIMIT_SECONDS = 10.0

    def search_files(self, user_id: int, pattern: str, max_results: int = 20) -> Tuple[bool, str]:
        """Search for files matching pattern (stops after a time limit)."""
        try:
            current = self.get_current_dir(user_id)
            deadline = time.monotonic() + self._SEARCH_TIME_LIMIT_SECONDS
            timed_out = False
            needle = (pattern or "").lower()

            matches = []
            for root, dirs, files in os.walk(current):
                if time.monotonic() > deadline:
                    timed_out = True
                    break

                # Skip hidden and generated directories
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith('.') and d.lower() not in self._SEARCH_SKIP_DIRS
                ]

                for file in files:
                    if needle in file.lower():
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(current)
                        matches.append(str(rel_path))

                        if len(matches) >= max_results:
                            break

                if len(matches) >= max_results:
                    break

            note = (
                f"\n\n⏱️ Search stopped after {int(self._SEARCH_TIME_LIMIT_SECONDS)}s — "
                "narrow it with /cd or a longer pattern."
                if timed_out else ""
            )

            if not matches:
                return True, f"No files found matching: {pattern}{note}"

            result = f"🔍 Found {len(matches)} file(s) matching '{pattern}':\n\n"
            result += "\n".join(f"📄 {m}" for m in matches)

            if len(matches) >= max_results:
                result += f"\n\n... search limited to {max_results} results"
            result += note

            return True, result

        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return False, f"Error: {str(e)}"

    def get_file_info(self, user_id: int, path: str) -> Tuple[bool, str]:
        """Get information about a file or directory."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"Path not found: {path}"
            
            stat = target.stat()
            
            info = f"📋 {target.name}\n\n"
            info += f"Type: {'Directory' if target.is_dir() else 'File'}\n"
            info += f"Path: {target}\n"
            info += f"Size: {self._format_size(stat.st_size)}\n"
            
            if target.is_file():
                # Try to count lines for text files
                try:
                    with open(target, 'r', encoding='utf-8') as f:
                        lines = sum(1 for _ in f)
                    info += f"Lines: {lines}\n"
                except Exception:
                    pass
            
            return True, info
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return False, f"Error: {str(e)}"
    
    def write_file(self, user_id: int, path: str, content: str) -> Tuple[bool, str]:
        """Write content to a file (creates or overwrites)."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            # Create parent directories if needed
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            
            size = target.stat().st_size
            lines = content.count('\n') + 1
            
            return True, f"✅ File written successfully\n\nPath: {target}\nSize: {self._format_size(size)}\nLines: {lines}"
            
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False, f"Error: {str(e)}"
    
    def append_file(self, user_id: int, path: str, content: str) -> Tuple[bool, str]:
        """Append content to an existing file."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"File not found: {path}. Use write_file to create new files."
            
            if not target.is_file():
                return False, f"Not a file: {path}"
            
            # Append to file
            with open(target, 'a', encoding='utf-8') as f:
                f.write(content)
            
            size = target.stat().st_size
            
            return True, f"✅ Content appended successfully\n\nPath: {target}\nNew size: {self._format_size(size)}"
            
        except Exception as e:
            logger.error(f"Error appending to file: {e}")
            return False, f"Error: {str(e)}"
    
    def delete_file(self, user_id: int, path: str) -> Tuple[bool, str]:
        """Delete a file."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"File not found: {path}"
            
            if not target.is_file():
                return False, f"Not a file: {path}. Use delete_directory for directories."
            
            # Delete file
            target.unlink()
            
            return True, f"✅ File deleted successfully\n\nPath: {target}"
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False, f"Error: {str(e)}"
    
    def create_directory(self, user_id: int, path: str) -> Tuple[bool, str]:
        """Create a new directory."""
        try:
            current = self.get_current_dir(user_id)
            target = (current / path).resolve()
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if target.exists():
                return False, f"Path already exists: {path}"
            
            # Create directory
            target.mkdir(parents=True, exist_ok=False)
            
            return True, f"✅ Directory created successfully\n\nPath: {target}"
            
        except Exception as e:
            logger.error(f"Error creating directory: {e}")
            return False, f"Error: {str(e)}"
    
    def get_tree_structure(self, user_id: int, path: Optional[str] = None, max_depth: int = 3, max_files: int = 100) -> Tuple[bool, str]:
        """Get tree structure of directory."""
        try:
            if path:
                current = self.get_current_dir(user_id)
                target = (current / path).resolve()
            else:
                target = self.get_current_dir(user_id)
            
            # Security check
            if not self._is_safe_path(target):
                return False, "Access denied: Path outside approved directory"
            
            if not target.exists():
                return False, f"Path not found: {path or '.'}"
            
            if not target.is_dir():
                return False, f"Not a directory: {path or '.'}"
            
            # Build tree
            tree_lines = [f"📂 {target.name}/"]
            file_count = [0]  # Use list to allow modification in nested function
            
            def build_tree(dir_path: Path, prefix: str = "", depth: int = 0):
                if depth >= max_depth or file_count[0] >= max_files:
                    return
                
                try:
                    items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                    # Filter out hidden files and common ignore patterns
                    items = [
                        item for item in items 
                        if not item.name.startswith('.') 
                        and item.name not in ['node_modules', '__pycache__', 'venv', 'env', 'dist', 'build']
                    ]
                    
                    for idx, item in enumerate(items):
                        if file_count[0] >= max_files:
                            tree_lines.append(f"{prefix}└── ... (truncated, max {max_files} items)")
                            return
                        
                        is_last = idx == len(items) - 1
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        
                        if item.is_dir():
                            tree_lines.append(f"{prefix}{current_prefix}📁 {item.name}/")
                            build_tree(item, next_prefix, depth + 1)
                        else:
                            size = item.stat().st_size
                            size_str = self._format_size(size)
                            tree_lines.append(f"{prefix}{current_prefix}📄 {item.name} ({size_str})")
                            file_count[0] += 1
                            
                except PermissionError:
                    tree_lines.append(f"{prefix}└── [Permission Denied]")
                except Exception as e:
                    tree_lines.append(f"{prefix}└── [Error: {str(e)}]")
            
            build_tree(target)
            
            result = "\n".join(tree_lines)
            if file_count[0] >= max_files:
                result += f"\n\n⚠️ Output truncated at {max_files} files"
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error getting tree structure: {e}")
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
