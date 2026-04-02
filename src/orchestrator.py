from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from prefect import flow, task
from prefect.futures import as_completed

from src.models.dag import ExecutionPlan, Node
from src.tools.registry import get_tool

_REPORT_TOOLS = frozenset({"report_error", "report_success"})


def _topological_levels(
    plan: ExecutionPlan, exclude: set[str] | None = None
) -> list[list[Node]]:
    """Group nodes into execution levels using Kahn's algorithm.

    Builds the graph from each node's depends_on field.
    Nodes in the same level are independent and can run in parallel.
    Nodes in `exclude` are skipped (e.g. fallback nodes).
    """
    exclude = exclude or set()
    active_nodes = [n for n in plan.nodes if n.id not in exclude]

    node_map = {node.id: node for node in active_nodes}
    in_degree: dict[str, int] = {node.id: 0 for node in active_nodes}
    children: dict[str, list[str]] = defaultdict(list)

    for node in active_nodes:
        for dep in node.depends_on:
            if dep not in exclude:
                in_degree[node.id] += 1
                children[dep].append(node.id)

    queue: deque[str] = deque(
        nid for nid, deg in in_degree.items() if deg == 0
    )

    levels: list[list[Node]] = []
    while queue:
        current_level_ids = list(queue)
        queue.clear()
        levels.append([node_map[nid] for nid in current_level_ids])

        for nid in current_level_ids:
            for child_id in children[nid]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

    scheduled = sum(len(level) for level in levels)
    if scheduled != len(active_nodes):
        raise ValueError(
            "Cycle detected in the execution plan — "
            f"scheduled {scheduled} of {len(active_nodes)} nodes"
        )

    return levels


@task(name="execute_node")
def execute_node(node: Node) -> Any:
    """Execute a single DAG node by calling its registered tool."""
    tool_fn = get_tool(node.tool)
    return tool_fn.fn(**node.params)


def _collect_descendants(
    node_id: str, children: dict[str, list[str]]
) -> set[str]:
    """Return all transitive descendants of a node (BFS)."""
    visited: set[str] = set()
    queue = deque(children.get(node_id, []))
    while queue:
        nid = queue.popleft()
        if nid not in visited:
            visited.add(nid)
            queue.extend(children.get(nid, []))
    return visited


def _build_children_map(plan: ExecutionPlan, exclude: set[str]) -> dict[str, list[str]]:
    """Build a parent -> children adjacency list from depends_on."""
    children: dict[str, list[str]] = defaultdict(list)
    for node in plan.nodes:
        if node.id in exclude:
            continue
        for dep in node.depends_on:
            if dep not in exclude:
                children[dep].append(node.id)
    return children


@flow(name="dag_orchestrator", log_prints=True)
def run_dag(plan: ExecutionPlan, run_dir: Path | None = None) -> dict[str, Any]:
    """Execute an entire DAG plan respecting dependencies and parallelism."""
    node_map = {node.id: node for node in plan.nodes}
    fallback_ids = plan.fallback_node_ids()
    levels = _topological_levels(plan, exclude=fallback_ids)
    children = _build_children_map(plan, exclude=fallback_ids)
    results: dict[str, Any] = {}
    failed: set[str] = set()

    for level_idx, level in enumerate(levels):
        runnables = [n for n in level if n.id not in failed]
        skipped = [n for n in level if n.id in failed]

        for node in skipped:
            results[node.id] = {"_skipped": True, "_reason": "predecessor failed"}
            print(f"  -- Skipped: {node.id} ({node.tool}) — predecessor failed")

        if not runnables:
            continue

        print(
            f"\n=== Level {level_idx} === "
            f"({len(runnables)} node(s) in parallel)"
        )

        futures = {}
        for node in runnables:
            extra_params: dict[str, object] = {}

            if node.tool in {"check_condition", "ai_insight"}:
                extra_params.update(
                    {
                        dep: results[dep]
                        for dep in node.depends_on
                        if dep in results
                    }
                )

            if node.tool in _REPORT_TOOLS and run_dir:
                extra_params["run_dir"] = str(run_dir)

            submit_node = node
            if extra_params:
                submit_node = node.model_copy(
                    update={"params": {**node.params, **extra_params}}
                )

            print(f"  -> Submitting: {node.id} ({node.tool})")
            future = execute_node.submit(submit_node)
            futures[node.id] = future

        for future in as_completed(futures.values()):
            node_id = next(
                nid for nid, f in futures.items() if f == future
            )
            node = node_map[node_id]

            try:
                result = future.result()
                results[node_id] = result
                print(f"  <- Completed: {node_id}")
            except Exception as exc:
                if node.on_error:
                    fallback = node_map[node.on_error]
                    print(
                        f"  !! {node_id} failed: {exc} "
                        f"-> running fallback: {fallback.id} ({fallback.tool})"
                    )
                    fallback_with_context = fallback.model_copy(
                        update={
                            "params": {
                                **fallback.params,
                                "node_id": node_id,
                                "tool": node.tool,
                                "error": str(exc),
                                **({"run_dir": str(run_dir)} if run_dir else {}),
                            }
                        }
                    )
                    fb_future = execute_node.submit(fallback_with_context)
                    fb_result = fb_future.result()
                    results[node_id] = {
                        "_error": str(exc),
                        "_fallback": fallback.id,
                        "_fallback_result": fb_result,
                    }
                    print(f"  <- Fallback completed: {fallback.id}")
                else:
                    print(f"  !! {node_id} failed with no fallback: {exc}")
                    results[node_id] = {"_error": str(exc)}

                descendants = _collect_descendants(node_id, children)
                failed |= descendants
                if descendants:
                    print(
                        f"     Downstream nodes will be skipped: "
                        f"{', '.join(sorted(descendants))}"
                    )

    return results
