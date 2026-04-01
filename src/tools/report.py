from datetime import datetime, timezone
from pathlib import Path

from prefect import task

DATA_DIR = Path("data")


def _resolve_dir(run_dir: str | None) -> Path:
    target = Path(run_dir) if run_dir else DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


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
