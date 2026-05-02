"""Workflow recipe registry for reusable automation flows."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from pocket_desk_agent.app_paths import app_path, existing_app_path

logger = logging.getLogger(__name__)

RECIPES_PATH = app_path("workflow_recipes.json")

STEP_KIND_COMMAND = "command"
STEP_KIND_CLAUDE_PROMPT = "claude_prompt"
STEP_KIND_WAIT_SECONDS = "wait_seconds"
STEP_KIND_WAIT_TEXT = "wait_text"
STEP_KIND_NOTIFY = "notify"
SUPPORTED_STEP_KINDS = {
    STEP_KIND_COMMAND,
    STEP_KIND_CLAUDE_PROMPT,
    STEP_KIND_WAIT_SECONDS,
    STEP_KIND_WAIT_TEXT,
    STEP_KIND_NOTIFY,
}


@dataclass
class RecipeStep:
    """One executable step in a workflow recipe."""

    kind: str
    payload: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RecipeStep":
        return cls(
            kind=str(data.get("kind", "")).strip(),
            payload=str(data.get("payload", "")).strip(),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class RecipeDefinition:
    """Persistent recipe definition."""

    name: str
    created_at: float
    updated_at: float
    steps: list[RecipeStep] = field(default_factory=list)
    use_count: int = 0
    last_used_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.to_dict() for step in self.steps],
            "use_count": self.use_count,
            "last_used_at": self.last_used_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecipeDefinition":
        return cls(
            name=str(data.get("name", "")).strip(),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            steps=[RecipeStep.from_dict(item) for item in list(data.get("steps") or [])],
            use_count=int(data.get("use_count", 0) or 0),
            last_used_at=(
                float(data["last_used_at"]) if data.get("last_used_at") is not None else None
            ),
        )


class RecipeRegistry:
    """Persistent storage manager for workflow recipes."""

    def __init__(self) -> None:
        self.recipes: dict[str, dict] = {}
        self.load()

    def load(self) -> bool:
        try:
            load_path = RECIPES_PATH
            if not load_path.exists():
                load_path = existing_app_path("workflow_recipes.json")
            if not load_path.exists():
                self.recipes = {}
                return True
            with open(load_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self.recipes = dict(raw) if isinstance(raw, dict) else {}
            logger.info("Loaded %s workflow recipes", len(self.recipes))
            return True
        except Exception as exc:
            logger.error("Failed to load workflow recipes: %s", exc, exc_info=True)
            self.recipes = {}
            return False

    def save(self) -> bool:
        try:
            RECIPES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(RECIPES_PATH, "w", encoding="utf-8") as handle:
                json.dump(self.recipes, handle, indent=2, ensure_ascii=False)
            return True
        except Exception as exc:
            logger.error("Failed to save workflow recipes: %s", exc, exc_info=True)
            return False

    def list_recipes(self) -> list[RecipeDefinition]:
        items = [RecipeDefinition.from_dict(v) for v in self.recipes.values()]
        items.sort(key=lambda recipe: recipe.name.lower())
        return items

    def get_recipe(self, name: str) -> Optional[RecipeDefinition]:
        key = name.strip().lower()
        data = self.recipes.get(key)
        if not data:
            return None
        return RecipeDefinition.from_dict(data)

    def create_recipe(self, name: str) -> tuple[bool, str]:
        key = name.strip().lower()
        normalized = name.strip()
        if not normalized:
            return False, "Recipe name cannot be empty."
        if key in self.recipes:
            return False, f"Recipe '{normalized}' already exists."

        now = time.time()
        recipe = RecipeDefinition(
            name=normalized,
            created_at=now,
            updated_at=now,
            steps=[],
        )
        self.recipes[key] = recipe.to_dict()
        self.save()
        return True, f"Recipe '{normalized}' created."

    def delete_recipe(self, name: str) -> tuple[bool, str]:
        key = name.strip().lower()
        if key not in self.recipes:
            return False, f"Recipe '{name}' was not found."
        del self.recipes[key]
        self.save()
        return True, f"Recipe '{name}' deleted."

    def append_step(self, name: str, step: RecipeStep) -> tuple[bool, str]:
        if step.kind not in SUPPORTED_STEP_KINDS:
            return False, f"Unsupported step kind '{step.kind}'."

        recipe = self.get_recipe(name)
        if not recipe:
            return False, f"Recipe '{name}' was not found."

        recipe.steps.append(step)
        recipe.updated_at = time.time()
        self.recipes[recipe.name.strip().lower()] = recipe.to_dict()
        self.save()
        return True, f"Added {step.kind} step to '{recipe.name}'."

    def mark_used(self, name: str) -> None:
        recipe = self.get_recipe(name)
        if not recipe:
            return
        recipe.use_count += 1
        recipe.last_used_at = time.time()
        recipe.updated_at = time.time()
        self.recipes[recipe.name.strip().lower()] = recipe.to_dict()
        self.save()


_recipe_registry: Optional[RecipeRegistry] = None


def get_recipe_registry() -> RecipeRegistry:
    """Return singleton recipe registry."""
    global _recipe_registry
    if _recipe_registry is None:
        _recipe_registry = RecipeRegistry()
    return _recipe_registry
