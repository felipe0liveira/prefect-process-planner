import json

import vertexai
from vertexai.generative_models import GenerativeModel

from src.models.dag import ExecutionPlan
from src.settings import settings
from src.tools.registry import TOOL_SCHEMAS

SYSTEM_PROMPT = """\
You are an execution planner. Given a user request and a set of available tools,
you must produce a JSON execution plan — a DAG (Directed Acyclic Graph) that
describes which tools to call and in what order.

## Available Tools

{tools_json}

## Output Format

You MUST return ONLY a valid JSON object (no markdown, no extra text) with this schema:

{{
  "description": "A short description of what the plan does",
  "nodes": [
    {{
      "id": "unique_node_id",
      "tool": "tool_name",
      "params": {{}},
      "depends_on": ["ids of nodes that must complete before this one"],
      "on_error": "optional_fallback_node_id"
    }}
  ]
}}

## Rules

1. Each node has a unique string "id".
2. "tool" must be one of the available tool names.
3. "params" must match the tool's parameter specification.
4. "depends_on" lists the IDs of predecessor nodes. Use an empty list for root nodes.
5. "on_error" is optional. If set, it must reference the ID of another node that
   will be executed as a fallback if this node fails. The fallback node must also
   be defined in the nodes list. Fallback nodes stay dormant and only run on error.
6. When the user asks to "report errors", "log errors", or handle failures,
   use the "report_error" tool as the on_error fallback. Its params (node_id,
   tool, error) are injected automatically at runtime — always set them to
   empty strings in the plan.
7. The graph must be a DAG (no cycles).
8. Maximize parallelism: nodes that can run independently should NOT depend on each other.
9. Return ONLY the JSON — no markdown fences, no explanatory text.
10. When the user asks to validate, verify, or check a condition on the result of a
    previous step, use the "check_condition" tool. The variable names in the expression
    MUST match the IDs of the nodes listed in depends_on. The orchestrator injects
    dependency results as variables automatically at runtime. Examples:
    - "len(list_posts) > 10" (where "list_posts" is a depends_on node ID)
    - "get_user['name'] == 'Leanne Graham'" (indexing into a dict result)
    Combine with on_error + report_error to handle condition failures.
"""


def generate_plan(user_prompt: str) -> ExecutionPlan:
    """Use Gemini 2.5 Flash via Vertex AI to generate an execution plan."""
    vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)

    model = GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SYSTEM_PROMPT.format(
            tools_json=json.dumps(TOOL_SCHEMAS, indent=2)
        ),
    )

    response = model.generate_content(
        user_prompt,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
        },
    )

    raw_text = response.text.strip()

    plan = ExecutionPlan.model_validate_json(raw_text)
    return plan
