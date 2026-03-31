from collections.abc import Callable
from typing import Any

from src.tools.jsonplaceholder import (
    create_post,
    get_comments,
    get_post,
    get_posts,
    get_todos,
    get_user,
    get_users,
    report_error,
    unreliable_get_post,
)

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "get_posts": get_posts,
    "get_post": get_post,
    "get_comments": get_comments,
    "get_users": get_users,
    "get_user": get_user,
    "create_post": create_post,
    "get_todos": get_todos,
    "report_error": report_error,
    "unreliable_get_post": unreliable_get_post,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "get_posts",
        "description": "List posts from JSONPlaceholder API. Can filter by user ID.",
        "parameters": {
            "user_id": {
                "type": "integer",
                "description": "Optional user ID to filter posts by author.",
                "required": False,
            }
        },
    },
    {
        "name": "get_post",
        "description": "Get a single post by its ID.",
        "parameters": {
            "post_id": {
                "type": "integer",
                "description": "The ID of the post to retrieve.",
                "required": True,
            }
        },
    },
    {
        "name": "get_comments",
        "description": "List all comments for a given post.",
        "parameters": {
            "post_id": {
                "type": "integer",
                "description": "The ID of the post to get comments for.",
                "required": True,
            }
        },
    },
    {
        "name": "get_users",
        "description": "List all users.",
        "parameters": {},
    },
    {
        "name": "get_user",
        "description": "Get a single user by their ID.",
        "parameters": {
            "user_id": {
                "type": "integer",
                "description": "The ID of the user to retrieve.",
                "required": True,
            }
        },
    },
    {
        "name": "create_post",
        "description": "Create a new post with a title, body, and user ID.",
        "parameters": {
            "title": {
                "type": "string",
                "description": "The title of the new post.",
                "required": True,
            },
            "body": {
                "type": "string",
                "description": "The body content of the new post.",
                "required": True,
            },
            "user_id": {
                "type": "integer",
                "description": "The ID of the user creating the post.",
                "required": True,
            },
        },
    },
    {
        "name": "get_todos",
        "description": "List todos from JSONPlaceholder API. Can filter by user ID.",
        "parameters": {
            "user_id": {
                "type": "integer",
                "description": "Optional user ID to filter todos.",
                "required": False,
            }
        },
    },
    {
        "name": "unreliable_get_post",
        "description": "Get a post by ID, but simulates an unstable service that fails on even post IDs. Use this instead of get_post when you want to test error handling.",
        "parameters": {
            "post_id": {
                "type": "integer",
                "description": "The ID of the post to retrieve.",
                "required": True,
            }
        },
    },
    {
        "name": "report_error",
        "description": "Report an error by saving details to a log file. Use as an on_error fallback. The parameters node_id, tool and error are automatically injected by the orchestrator at runtime — set them to empty strings in the plan.",
        "parameters": {
            "node_id": {
                "type": "string",
                "description": "ID of the node that failed (injected at runtime).",
                "required": True,
            },
            "tool": {
                "type": "string",
                "description": "Tool name that failed (injected at runtime).",
                "required": True,
            },
            "error": {
                "type": "string",
                "description": "Error message (injected at runtime).",
                "required": True,
            },
        },
    },
]


def get_tool(name: str) -> Callable[..., Any]:
    """Retrieve a tool function by name. Raises KeyError if not found."""
    if name not in TOOL_REGISTRY:
        available = ", ".join(sorted(TOOL_REGISTRY.keys()))
        raise KeyError(f"Tool '{name}' not found. Available tools: {available}")
    return TOOL_REGISTRY[name]
