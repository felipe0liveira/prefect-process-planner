from datetime import datetime, timezone
from pathlib import Path

from prefect import task

from src.tools.decorator import tool

DATA_DIR = Path("data")


def _resolve_dir(run_dir: str | None) -> Path:
    target = Path(run_dir) if run_dir else DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


@tool(
    readonly=False,
    description=(
        "Report an error by saving details to a log file. Use as an on_error "
        "fallback. The parameters node_id, tool and error are automatically "
        "injected by the orchestrator at runtime — set them to empty strings "
        "in the plan."
    ),
    exclude_params={"run_dir"},
    param_descriptions={
        "node_id": "ID of the node that failed (injected at runtime).",
        "tool": "Tool name that failed (injected at runtime).",
        "error": "Error message (injected at runtime).",
    },
)
@task(name="report_error")
def report_error(
    node_id: str, tool: str, error: str, run_dir: str | None = None
) -> dict:
    """Report an error by saving it to a log file in the run directory."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_dir = _resolve_dir(run_dir)
    log_path = target_dir / f"{ts}_error.log"

    content = (
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        f"Node:      {node_id}\n"
        f"Tool:      {tool}\n"
        f"Error:     {error}\n"
    )
    log_path.write_text(content, encoding="utf-8")

    return {"logged_to": str(log_path), "node_id": node_id, "tool": tool, "error": error}


@tool(
    readonly=False,
    description=(
        "Report a successful execution by saving a summary to a log file. Use "
        "as a final node in the DAG to log that a workflow completed successfully. "
        "The parameters node_id and tool are automatically injected by the "
        "orchestrator at runtime — set them to empty strings in the plan."
    ),
    exclude_params={"run_dir"},
    param_descriptions={
        "node_id": "ID of the node (injected at runtime).",
        "tool": "Tool name (injected at runtime).",
        "summary": "A short summary of what was accomplished.",
    },
)
@task(name="report_success")
def report_success(
    node_id: str, tool: str, summary: str = "", run_dir: str | None = None
) -> dict:
    """Report a successful execution by saving a summary to a log file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_dir = _resolve_dir(run_dir)
    log_path = target_dir / f"{ts}_success.log"

    content = (
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        f"Node:      {node_id}\n"
        f"Tool:      {tool}\n"
        f"Summary:   {summary}\n"
    )
    log_path.write_text(content, encoding="utf-8")

    return {
        "logged_to": str(log_path),
        "node_id": node_id,
        "tool": tool,
        "summary": summary,
    }
