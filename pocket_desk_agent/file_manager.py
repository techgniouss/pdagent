"""File system manager for repository access."""

import os
import logging
from pathlib import Path
from typing import Optional, List, Tuple

from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file system access within approved directory."""
    
    def __init__(self):
        self.approved_dirs = Config.APPROVED_DIRECTORIES
        self.current_dirs = {}  # user_id -> current_directory
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within any of the approved directories.

        Uses Path.is_relative_to() (Python 3.9+) instead of string prefix
        matching, which is vulnerable to directory-prefix attacks
        (e.g. /home/user/projects_evil passing /home/user/projects).
        """
        try:
            resolved = path.resolve()
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
            # Default to the first approved directory
            self.current_dirs[user_id] = self.approved_dirs[0] if self.approved_dirs else Path(".")
        return self.current_dirs[user_id]
    
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
    
    def search_files(self, user_id: int, pattern: str, max_results: int = 20) -> Tuple[bool, str]:
        """Search for files matching pattern."""
        try:
            current = self.get_current_dir(user_id)
            
            matches = []
            for root, dirs, files in os.walk(current):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if pattern.lower() in file.lower():
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(current)
                        matches.append(str(rel_path))
                        
                        if len(matches) >= max_results:
                            break
                
                if len(matches) >= max_results:
                    break
            
            if not matches:
                return True, f"No files found matching: {pattern}"
            
            result = f"🔍 Found {len(matches)} file(s) matching '{pattern}':\n\n"
            result += "\n".join(f"📄 {m}" for m in matches)
            
            if len(matches) >= max_results:
                result += f"\n\n... search limited to {max_results} results"
            
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
    
    # Allowlist of safe command prefixes.  Only commands whose first token
    # (lowercased) matches one of these are executed.  This is far safer than
    # a blocklist because unknown/novel attack strings are rejected by default.
    _ALLOWED_COMMANDS = frozenset({
        # Navigation / inspection
        "dir", "ls", "type", "cat", "head", "tail", "more",
        "tree", "pwd", "cd", "where", "which",
        # File comparison / sorting
        "fc", "sort", "find", "findstr", "grep",
        # Dev tools
        "git", "python", "python3", "pip", "pip3",
        "npm", "npx", "node", "yarn", "pnpm",
        # System info (read-only)
        "whoami", "hostname", "echo", "tasklist",
        "ping", "ipconfig", "ifconfig", "netstat",
    })

    # Shell metacharacters that can chain or redirect commands.
    # Blocking these prevents `git status && rm -rf /` style attacks.
    _DANGEROUS_SHELL_CHARS = ("&&", "||", ";", "|", "`", "$(", ">", "<", "\n", "\r")

    def execute_command(self, user_id: int, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Execute a shell command in the current directory.

        Security model — allowlist + metacharacter block:
        1. The first token of the command must be in ``_ALLOWED_COMMANDS``.
        2. Shell metacharacters that could chain extra commands are rejected.
        3. The handler layer gates this behind user authorization; it is NOT
           exposed to the AI model as a callable tool.
        """
        try:
            import subprocess
            import shlex

            current = self.get_current_dir(user_id)
            stripped = command.strip()

            if not stripped:
                return False, "Blocked: empty command."

            # ── Metacharacter check (before splitting, since shlex
            #    won't help if the string is meant for shell=True) ──
            for meta in self._DANGEROUS_SHELL_CHARS:
                if meta in stripped:
                    return False, (
                        f"Blocked: command contains shell metacharacter `{meta}`. "
                        "Chain/redirect operators are not allowed."
                    )

            # ── Allowlist check on the first token ──
            try:
                tokens = shlex.split(stripped)
            except ValueError:
                return False, "Blocked: malformed command (unmatched quotes)."

            first_token = Path(tokens[0]).stem.lower()  # strip .exe / path prefix
            if first_token not in self._ALLOWED_COMMANDS:
                allowed_list = ", ".join(sorted(self._ALLOWED_COMMANDS))
                return False, (
                    f"Blocked: `{tokens[0]}` is not in the command allowlist.\n"
                    f"Permitted commands: {allowed_list}"
                )

            logger.info(f"Executing command for user {user_id}: {stripped}")

            # Execute command — shell=True is needed for built-in commands
            # like `dir` on Windows, but metacharacters are already stripped.
            result = subprocess.run(
                stripped,
                shell=True,
                cwd=str(current),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Format output
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"📤 STDOUT:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"⚠️ STDERR:\n{result.stderr}")
            
            if not result.stdout and not result.stderr:
                output_parts.append("(no output)")
            
            output_parts.append(f"\n📊 Exit Code: {result.returncode}")
            
            output = "\n\n".join(output_parts)
            
            # Truncate if too long
            if len(output) > 4000:
                output = output[:4000] + "\n\n... (output truncated)"
            
            success = result.returncode == 0
            status = "✅ Success" if success else "❌ Failed"
            
            final_output = f"🖥️ Command: {command}\n📂 Directory: {current}\n\n{status}\n\n{output}"
            
            return True, final_output
            
        except subprocess.TimeoutExpired:
            return False, f"⏱️ Command timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
