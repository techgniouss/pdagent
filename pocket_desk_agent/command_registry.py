"""Command registry for storing and managing custom automation commands."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Registry file location — under the project's config directory
REGISTRY_PATH = Path.home() / ".pdagent" / "custom_commands.json"


@dataclass
class CommandAction:
    """Represents a single action in a command sequence."""
    type: str  # "hotkey", "clipboard", "findtext", "smartclick", "pasteenter"
    args: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {"type": self.type, "args": self.args}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CommandAction':
        """Create from dictionary."""
        return cls(type=data["type"], args=data["args"])


@dataclass
class CustomCommand:
    """Represents a saved custom command."""
    name: str
    actions: List[CommandAction]
    created_at: str
    last_used: Optional[str] = None
    use_count: int = 0


class CommandRegistry:
    """Manages persistent storage of custom commands."""
    
    def __init__(self):
        """Initialize the command registry."""
        self.registry: Dict[str, List[dict]] = {}
        self.load()
    
    def load(self) -> bool:
        """
        Load command registry from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if REGISTRY_PATH.exists():
                with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
                logger.info(f"Loaded {len(self.registry)} commands from registry")
                return True
            else:
                logger.info("No existing registry file, starting with empty registry")
                self.registry = {}
                return True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse registry JSON: {e}")
            logger.warning("Starting with empty registry due to corrupted file")
            self.registry = {}
            return False
        except Exception as e:
            logger.error(f"Failed to load command registry: {e}", exc_info=True)
            self.registry = {}
            return False
    
    def save(self) -> bool:
        """
        Save command registry to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.registry)} commands to registry")
            return True
        except Exception as e:
            logger.error(f"Failed to save command registry: {e}", exc_info=True)
            return False
    
    def add_command(self, name: str, actions: List[CommandAction]) -> bool:
        """
        Add or update a command in the registry.
        
        Args:
            name: Command name
            actions: List of CommandAction objects
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Convert actions to dict format
            action_dicts = [action.to_dict() for action in actions]
            self.registry[name] = action_dicts
            return self.save()
        except Exception as e:
            logger.error(f"Failed to add command '{name}': {e}", exc_info=True)
            return False
    
    def get_command(self, name: str) -> Optional[List[CommandAction]]:
        """
        Get a command from the registry.
        
        Args:
            name: Command name
            
        Returns:
            List of CommandAction objects, or None if not found
        """
        if name not in self.registry:
            return None
        
        try:
            action_dicts = self.registry[name]
            actions = [CommandAction.from_dict(d) for d in action_dicts]
            return actions
        except Exception as e:
            logger.error(f"Failed to parse command '{name}': {e}", exc_info=True)
            return None
    
    def delete_command(self, name: str) -> bool:
        """
        Delete a command from the registry.
        
        Args:
            name: Command name
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if name not in self.registry:
            return False
        
        try:
            del self.registry[name]
            return self.save()
        except Exception as e:
            logger.error(f"Failed to delete command '{name}': {e}", exc_info=True)
            return False
    
    def list_commands(self) -> Dict[str, int]:
        """
        Get a list of all command names with their action counts.
        
        Returns:
            Dictionary mapping command names to action counts
        """
        return {name: len(actions) for name, actions in self.registry.items()}
    
    def command_exists(self, name: str) -> bool:
        """
        Check if a command exists in the registry.
        
        Args:
            name: Command name
            
        Returns:
            True if command exists, False otherwise
        """
        return name in self.registry


# Global registry instance
_registry_instance: Optional[CommandRegistry] = None


def get_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CommandRegistry()
    return _registry_instance
