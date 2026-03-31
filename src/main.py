import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python -m src.main '<prompt>'")
        print()
        print('Example: uv run python -m src.main "Get user 1 data, '
              'then list their posts and todos in parallel"')
        sys.exit(1)

    user_prompt = " ".join(sys.argv[1:])
    run_dir = _build_run_dir()

    print("=" * 60)
    print("STEP 1: Generating execution plan with Gemini 2.5 Flash")
    print("=" * 60)
    print(f"Prompt: {user_prompt}\n")

    plan = generate_plan(user_prompt)
    dag_data = plan.model_dump()

    print("Generated DAG:")
    print(json.dumps(dag_data, indent=2, ensure_ascii=False))
    _save_json(dag_data, run_dir / "dag.json")

    print()
    print("=" * 60)
    print("STEP 2: Executing DAG with Prefect orchestrator")
    print("=" * 60)

    results = run_dag(plan, run_dir=run_dir)

    flow_log = {
        "prompt": user_prompt,
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


def _summarize(result: object) -> object:
    """Create a short summary for the flow log (avoid dumping huge lists)."""
    if isinstance(result, list):
        return {"_type": "list", "_count": len(result), "_preview": result[:2]}
    return result


if __name__ == "__main__":
    main()
