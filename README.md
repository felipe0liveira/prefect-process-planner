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
│  Planner (Gemini)    │  Generates a DAG (nodes + edges) as JSON
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Orchestrator        │  Prefect flow — topological sort,
│  (Prefect)           │  parallel execution by level
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Tools               │  get_posts, get_user, get_comments,
│  (JSONPlaceholder)   │  create_post, get_todos, ...
└──────────────────────┘
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python project manager)
- A GCP project with Vertex AI API enabled
- Authenticated via `gcloud auth application-default login`

## Setup

```bash
# Install dependencies
uv sync

# Set required environment variables
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_LOCATION="us-central1"  # optional, defaults to us-central1
```

## Usage

```bash
uv run python -m src.main "Get user 1 data, then list their posts and todos in parallel"
```

This will:

1. Send the prompt to Gemini 2.5 Flash, which generates a DAG
2. Print the generated execution plan (JSON)
3. Execute the DAG via Prefect, respecting node dependencies and parallelism
4. Print the consolidated results

## Example Output

For the prompt above, Gemini might generate:

```json
{
  "description": "Fetch user 1, then list posts and todos in parallel",
  "nodes": [
    {"id": "n1", "tool": "get_user", "params": {"user_id": 1}, "depends_on": []},
    {"id": "n2", "tool": "get_posts", "params": {"user_id": 1}, "depends_on": ["n1"]},
    {"id": "n3", "tool": "get_todos", "params": {"user_id": 1}, "depends_on": ["n1"]}
  ],
  "edges": [
    {"source": "n1", "target": "n2"},
    {"source": "n1", "target": "n3"}
  ]
}
```

Prefect then executes `n1` first, followed by `n2` and `n3` in parallel.

## Available Tools

| Tool | Description |
|------|-------------|
| `get_posts` | List posts (optionally filtered by user_id) |
| `get_post` | Get a single post by ID |
| `get_comments` | List comments for a post |
| `get_users` | List all users |
| `get_user` | Get a single user by ID |
| `create_post` | Create a new post |
| `get_todos` | List todos (optionally filtered by user_id) |

## Project Structure

```
src/
├── main.py              # CLI entry point
├── planner.py           # Vertex AI / Gemini integration
├── orchestrator.py      # Prefect flow — DAG execution engine
├── models/
│   └── dag.py           # Pydantic models (Node, Edge, ExecutionPlan)
└── tools/
    ├── registry.py      # Tool registry and schemas
    └── jsonplaceholder.py  # API tool implementations
```
