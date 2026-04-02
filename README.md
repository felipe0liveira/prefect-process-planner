# POC: Prefect + Vertex AI — DAG Orchestration

A proof-of-concept that uses **Gemini 2.5 Flash** (via Vertex AI) to generate
execution plans (DAGs) from natural language prompts, and **Prefect** to
orchestrate the execution of each node in the graph.

The example tools call the [JSONPlaceholder](https://jsonplaceholder.typicode.com) API.

## Architecture

```
User Prompt
    │
    ▼
┌──────────────────────┐
│  Planner (Gemini)    │  Generates a DAG (nodes + depends_on) as JSON
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Orchestrator        │  Prefect flow — topological sort,
│  (Prefect)           │  parallel execution by level,
│                      │  error handling + cascade skip,
│                      │  dry-run mode (blocks writes)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Tools               │  get_posts, get_user, create_post,
│  (JSONPlaceholder,   │  check_condition, ai_insight,
│   AI, Logic, Report) │  report_error, report_success, ...
└──────────────────────┘
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python project manager)
- A GCP project with Vertex AI API enabled
- Authenticated via `gcloud auth application-default login`

## Setup

```bash
make setup
```

This copies `.env.example` to `.env` and runs `uv sync`. Then edit `.env` with
your GCP project ID:

```
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash-preview-04-17
```

## Usage

### Make commands

| Command | Description |
|---------|-------------|
| `make plan p="..."` | Generate a DAG from a prompt without executing it |
| `make run p="..."` | Generate and execute a DAG in one step |
| `make execute d=<run_dir>` | Execute an existing `dag.json` from a run directory |
| `make test p="..."` | Generate and execute in test mode (write operations blocked) |
| `make readonly d=<run_dir>` | Re-execute an existing DAG in readonly/dry-run mode |
| `make preview` | Start local DAG visualizer at `http://localhost:8080` |
| `make clean` | Remove all saved outputs from `data/` |
| `make help` | Show all available commands |

### CLI

```bash
# Generate + execute
uv run python -m src.main "Busque o usuário 1 e liste os posts dele"

# Generate only (plan)
uv run python -m src.main --plan "Busque o usuário 1 e liste os posts dele"

# Execute an existing DAG
uv run python -m src.main --execute 20260401_143603

# Test mode — generate + execute with write tools blocked
uv run python -m src.main --test "Liste o usuário 1 e crie um post"

# Readonly — re-execute an existing DAG with write tools blocked
uv run python -m src.main --execute 20260401_143603 --dry-run
```

## DAG Format

The Gemini planner generates a JSON with this structure:

```json
{
  "description": "Fetch user 1, then list posts and todos in parallel",
  "nodes": [
    {"id": "n1", "tool": "get_user", "params": {"user_id": 1}, "depends_on": []},
    {"id": "n2", "tool": "get_posts", "params": {"user_id": 1}, "depends_on": ["n1"]},
    {"id": "n3", "tool": "get_todos", "params": {"user_id": 1}, "depends_on": ["n1"]}
  ]
}
```

- `depends_on` defines the execution order (topological sort). Nodes in the same
  level run in parallel.
- `on_error` (optional) points to a fallback node that runs if the node fails.

## Error Handling

Each node can have an `on_error` field pointing to a fallback node (e.g. `report_error`):

```json
{
  "id": "n1", "tool": "unreliable_get_post", "params": {"post_id": 2},
  "on_error": "n1_err"
},
{
  "id": "n1_err", "tool": "report_error",
  "params": {"node_id": "", "tool": "", "error": ""}
}
```

When a node fails:

1. If it has `on_error`: the fallback node runs (the orchestrator injects
   `node_id`, `tool`, and `error` into its params automatically), the error
   is logged, and **all downstream nodes are skipped**.
2. If it has no `on_error`: the error is recorded and **all downstream nodes
   are skipped**.
3. Independent nodes (no dependency on the failed node) continue normally.

The skip propagates transitively: if `n1 -> n2 -> n3` and `n1` fails, both
`n2` and `n3` are skipped.

## Test / Dry-Run Mode

Every tool declares a `readonly` flag in its schema. When running in test mode
(`--test` or `--dry-run`), the orchestrator blocks tools marked as
`readonly: false` (write operations) and cascade-skips their descendants.

Read-only tools execute normally, so you can validate the full DAG plan without
side effects.

```bash
# Generate + execute in test mode
make test p="Liste o usuário 1 e crie um post para ele"

# Re-execute an existing DAG in readonly mode
make readonly d=20260402_144544
```

In the DAG visualizer, blocked nodes are displayed in **cyan** with a dedicated
legend entry ("Blocked (dry-run)").

## AI Insight

The `ai_insight` tool uses Gemini to generate insights from the results of
previous nodes. The orchestrator injects dependency results automatically —
list the source nodes in `depends_on`.

```json
{
  "id": "analyze",
  "tool": "ai_insight",
  "params": {"prompt": "Summarize the main themes across these posts"},
  "depends_on": ["fetch_posts"]
}
```

### Examples

```bash
# Simple: fetch posts and summarize themes
make run p="Busque os posts do usuário 1 e gere um insight resumindo os principais temas"

# Complex: cross-reference user, posts, and todos
make run p="Busque o usuário 3, liste os posts e os todos dele em paralelo, e gere uma percepção cruzando todas as informações"
```

## Outputs

Each run saves its outputs to `data/<timestamp>/`:

| File | Content |
|------|---------|
| `dag.json` | The DAG generated by Gemini |
| `flow.json` | Full execution log: prompt, DAG, and result summaries |
| `results.json` | Complete raw results for each node |

Error/success reports are saved as timestamped `.log` files in the run directory.

Use `make clean` to remove all outputs.

## DAG Visualizer

Start the local preview server:

```bash
make preview
```

Open `http://localhost:8080` to explore DAGs with two view modes:

- **Plan** — shows the DAG structure with node details on click
- **Result** — shows execution results with color-coded status

### Color legend

| Color | Meaning |
|-------|---------|
| Blue | Normal node |
| Violet | Condition (`check_condition`) |
| Amber | Node with fallback (`on_error`) |
| Red (dark) | Fallback node |
| Green | Completed successfully |
| Cyan | Blocked by dry-run |
| Gray | Skipped (predecessor failed) |
| Red | Failed |

## Available Tools

| Tool | Readonly | Description |
|------|----------|-------------|
| `get_posts` | Yes | List posts (optionally filtered by user_id) |
| `get_post` | Yes | Get a single post by ID |
| `get_comments` | Yes | List comments for a post |
| `get_users` | Yes | List all users |
| `get_user` | Yes | Get a single user by ID |
| `get_todos` | Yes | List todos (optionally filtered by user_id) |
| `unreliable_get_post` | Yes | Get a post by ID — simulates failures on even IDs |
| `check_condition` | Yes | Evaluate a logical expression against dependency results |
| `ai_insight` | Yes | Generate AI-powered insights from dependency results |
| `create_post` | No | Create a new post |
| `report_error` | No | Log an error to a file (used as `on_error` fallback) |
| `report_success` | No | Log a success summary to a file |

## Project Structure

```
src/
├── main.py              # CLI entry point (plan, execute, run, test)
├── settings.py          # Centralized configuration (pydantic-settings + .env)
├── planner.py           # Vertex AI / Gemini integration
├── orchestrator.py      # Prefect flow — topological sort, parallel execution, error handling, dry-run
├── models/
│   └── dag.py           # Pydantic models (Node, ExecutionPlan)
└── tools/
    ├── registry.py      # Tool registry, schemas (with readonly flag), and lookup helpers
    ├── jsonplaceholder.py  # JSONPlaceholder API tools
    ├── ai.py            # AI insight tool (Gemini-powered analysis)
    ├── logic.py         # Condition evaluation tool (simpleeval)
    └── report.py        # Error and success reporting tools
preview/
├── index.html           # DAG visualizer UI
└── app.js               # LogicFlow-based DAG rendering
```
