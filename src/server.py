import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

DATA_DIR = Path("data")
ROOT_DIR = Path(".")

app = FastAPI(title="DAG Visualizer")


@app.get("/api/latest-dag")
def latest_dag() -> JSONResponse:
    """Return the most recent dag.json and results.json."""
    if not DATA_DIR.exists():
        return JSONResponse(
            {"error": "No data directory found. Run a DAG first."},
            status_code=404,
        )

    run_dirs = sorted(
        [d for d in DATA_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )

    if not run_dirs:
        return JSONResponse(
            {"error": "No runs found in data/. Run a DAG first."},
            status_code=404,
        )

    latest = run_dirs[0]
    dag_path = latest / "dag.json"
    results_path = latest / "results.json"

    if not dag_path.exists():
        return JSONResponse(
            {"error": f"dag.json not found in {latest.name}"},
            status_code=404,
        )

    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    results = None
    if results_path.exists():
        results = json.loads(results_path.read_text(encoding="utf-8"))

    return JSONResponse({
        "run_id": latest.name,
        "dag": dag,
        "results": results,
    })


@app.get("/api/runs")
def list_runs() -> JSONResponse:
    """List all available runs."""
    if not DATA_DIR.exists():
        return JSONResponse({"runs": []})

    run_dirs = sorted(
        [d.name for d in DATA_DIR.iterdir() if d.is_dir()],
        reverse=True,
    )
    return JSONResponse({"runs": run_dirs})


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> JSONResponse:
    """Return dag.json and results.json for a specific run."""
    run_dir = DATA_DIR / run_id
    if not run_dir.is_dir():
        return JSONResponse({"error": f"Run '{run_id}' not found"}, status_code=404)

    dag_path = run_dir / "dag.json"
    results_path = run_dir / "results.json"

    if not dag_path.exists():
        return JSONResponse({"error": "dag.json not found"}, status_code=404)

    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    results = None
    if results_path.exists():
        results = json.loads(results_path.read_text(encoding="utf-8"))

    return JSONResponse({
        "run_id": run_id,
        "dag": dag,
        "results": results,
    })


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")
