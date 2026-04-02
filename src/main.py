import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.models.dag import ExecutionPlan
from src.orchestrator import run_dag
from src.planner import generate_plan

DATA_DIR = Path("data")


def _save_json(data: dict, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Saved: {filepath}")


def _build_run_dir() -> Path:
    """Create a timestamped run directory under data/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = DATA_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _generate(user_prompt: str, run_dir: Path) -> ExecutionPlan:
    """Generate a DAG from a prompt and save it to disk."""
    print("=" * 60)
    print("Generating execution plan with Gemini 2.5 Flash")
    print("=" * 60)
    print(f"Prompt: {user_prompt}\n")

    plan = generate_plan(user_prompt)
    dag_data = plan.model_dump()

    print("Generated DAG:")
    print(json.dumps(dag_data, indent=2, ensure_ascii=False))
    _save_json(dag_data, run_dir / "dag.json")
    return plan


def _execute(
    plan: ExecutionPlan,
    run_dir: Path,
    user_prompt: str | None = None,
    dry_run: bool = False,
) -> None:
    """Execute a DAG and save results to disk."""
    dag_data = plan.model_dump()

    print()
    print("=" * 60)
    print(
        "Executing DAG with Prefect orchestrator"
        + (" [TEST MODE]" if dry_run else "")
    )
    print("=" * 60)

    results = run_dag(plan, run_dir=run_dir, dry_run=dry_run)

    flow_log = {
        "prompt": user_prompt or "(executed from existing dag.json)",
        "dag": dag_data,
        "results": {
            node_id: _summarize(result) for node_id, result in results.items()
        },
    }
    _save_json(flow_log, run_dir / "flow.json")

    _save_json(
        {node_id: result for node_id, result in results.items()},
        run_dir / "results.json",
    )

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    for node_id, result in results.items():
        print(f"\n--- {node_id} ---")
        if isinstance(result, list):
            print(f"  ({len(result)} items)")
            for item in result[:3]:
                print(f"  {json.dumps(item, indent=4, ensure_ascii=False)}")
            if len(result) > 3:
                print(f"  ... and {len(result) - 3} more")
        else:
            print(f"  {json.dumps(result, indent=4, ensure_ascii=False)}")

    print()
    print(f"All outputs saved to: {run_dir}/")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prefect Process Planner — AI-driven workflow orchestration",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--plan",
        metavar="PROMPT",
        help="generate a DAG from a prompt without executing it",
    )
    group.add_argument(
        "--execute",
        metavar="RUN_DIR",
        help="execute an existing dag.json from a run directory (name or path)",
    )
    group.add_argument(
        "--test",
        metavar="PROMPT",
        help="generate and execute a DAG in test mode (write operations are blocked)",
    )
    group.add_argument(
        "prompt",
        nargs="?",
        help="generate and execute a DAG in one step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="block write operations (use with --execute for readonly re-runs)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.plan:
        run_dir = _build_run_dir()
        _generate(args.plan, run_dir)
        print(f"\nPlan saved to: {run_dir}/dag.json")

    elif args.execute:
        run_dir = Path(args.execute)
        if not run_dir.is_absolute():
            run_dir = DATA_DIR / run_dir
        dag_path = run_dir / "dag.json"
        if not dag_path.exists():
            print(f"Error: {dag_path} not found", file=sys.stderr)
            sys.exit(1)
        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        plan = ExecutionPlan.model_validate(dag_data)
        _execute(plan, run_dir, dry_run=args.dry_run)

    elif args.test:
        user_prompt = args.test
        run_dir = _build_run_dir()
        plan = _generate(user_prompt, run_dir)
        _execute(plan, run_dir, user_prompt, dry_run=True)

    else:
        user_prompt = args.prompt
        run_dir = _build_run_dir()
        plan = _generate(user_prompt, run_dir)
        _execute(plan, run_dir, user_prompt)


def _summarize(result: object) -> object:
    """Create a short summary for the flow log (avoid dumping huge lists)."""
    if isinstance(result, list):
        return {"_type": "list", "_count": len(result), "_preview": result[:2]}
    return result


if __name__ == "__main__":
    main()
