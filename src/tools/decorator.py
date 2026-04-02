"""Decorator for registering DAG tools with auto-generated schemas."""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin

_REGISTRY: dict[str, Any] = {}
_TOOL_META: dict[str, dict] = {}

_TYPE_MAP: dict[type, str] = {
    int: "integer",
    str: "string",
    float: "number",
    bool: "boolean",
}


def tool(
    *,
    readonly: bool = True,
    description: str | None = None,
    exclude_params: set[str] | None = None,
    param_descriptions: dict[str, str] | None = None,
) -> Callable:
    """Register a Prefect task as a DAG tool with schema metadata.

    Must be applied **above** ``@task`` so it receives the Task object.

    Args:
        readonly: Whether the tool is safe to run in dry-run/test mode.
        description: Override for the schema description. When *None*,
            the first line of the underlying function's docstring is used.
        exclude_params: Parameter names to omit from the generated schema
            (e.g. params injected by the orchestrator at runtime).
        param_descriptions: Mapping of param name to a human-readable
            description for the LLM.  Params not listed here get an
            auto-generated description based on name and type.
    """
    _exclude = exclude_params or set()
    _param_descs = param_descriptions or {}

    def decorator(fn: Any) -> Any:
        original = fn.fn if hasattr(fn, "fn") else fn
        name = fn.name if hasattr(fn, "name") else original.__name__

        _REGISTRY[name] = fn
        _TOOL_META[name] = {
            "readonly": readonly,
            "description": description,
            "exclude_params": _exclude,
            "param_descriptions": _param_descs,
            "original_fn": original,
        }
        return fn

    return decorator


def _resolve_type(annotation: Any) -> str:
    """Map a Python type annotation to a JSON-schema type string."""
    if isinstance(annotation, types.UnionType) or get_origin(annotation) is Union:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if non_none:
            return _resolve_type(non_none[0])
    return _TYPE_MAP.get(annotation, "string")


def _build_schema(name: str, meta: dict) -> dict:
    """Build a single tool schema dict from function introspection + metadata."""
    original = meta["original_fn"]
    sig = inspect.signature(original)

    desc = meta["description"]
    if desc is None:
        doc = inspect.getdoc(original) or ""
        desc = doc.split("\n")[0].strip()

    params: dict[str, dict] = {}
    for pname, param in sig.parameters.items():
        if pname in meta["exclude_params"]:
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        ptype = _resolve_type(param.annotation) if param.annotation is not param.empty else "string"
        required = param.default is param.empty

        pdesc = meta["param_descriptions"].get(pname)
        if pdesc is None:
            label = pname.replace("_", " ").capitalize()
            pdesc = f"{label} ({ptype})." if required else f"{label} (optional, {ptype})."

        params[pname] = {
            "type": ptype,
            "description": pdesc,
            "required": required,
        }

    return {
        "name": name,
        "readonly": meta["readonly"],
        "description": desc,
        "parameters": params,
    }


def build_registry() -> dict[str, Callable[..., Any]]:
    """Return the tool name -> Prefect task mapping."""
    return dict(_REGISTRY)


def build_schemas() -> list[dict]:
    """Auto-generate ``TOOL_SCHEMAS`` from all registered tools."""
    return [_build_schema(name, meta) for name, meta in _TOOL_META.items()]
