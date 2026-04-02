from collections.abc import Callable
from typing import Any

import src.tools.ai  # noqa: F401
import src.tools.jsonplaceholder  # noqa: F401
import src.tools.logic  # noqa: F401
import src.tools.report  # noqa: F401
from src.tools.decorator import build_registry, build_schemas

TOOL_REGISTRY: dict[str, Callable[..., Any]] = build_registry()
TOOL_SCHEMAS: list[dict] = build_schemas()

_SCHEMA_BY_NAME: dict[str, dict] = {s["name"]: s for s in TOOL_SCHEMAS}


def is_readonly(name: str) -> bool:
    """Check whether a tool is read-only (safe to run in test/dry-run mode)."""
    return _SCHEMA_BY_NAME[name].get("readonly", True)


def get_tool(name: str) -> Callable[..., Any]:
    """Retrieve a tool function by name. Raises KeyError if not found."""
    if name not in TOOL_REGISTRY:
        available = ", ".join(sorted(TOOL_REGISTRY.keys()))
        raise KeyError(f"Tool '{name}' not found. Available tools: {available}")
    return TOOL_REGISTRY[name]
