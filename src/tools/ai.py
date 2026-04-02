import json
from typing import Any

import vertexai
from prefect import task
from vertexai.generative_models import GenerativeModel

from src.settings import settings
from src.tools.decorator import tool

_SYSTEM_PROMPT = """\
You are a data analyst. You will receive structured data produced by previous \
steps in an automated pipeline, along with a user instruction describing what \
kind of insight or perception to extract.

Analyze the data carefully and provide a clear, concise insight. Focus on \
patterns, anomalies, summaries, or whatever the user instruction requests. \
Reply in plain text (no JSON, no markdown fences).
"""


@tool(
    readonly=True,
    description=(
        "Use an AI model to analyze the results of dependency nodes and "
        "generate insights or perceptions. The results of all depends_on "
        "nodes are automatically injected as context at runtime. "
        "Provide a prompt describing what kind of insight or analysis you want."
    ),
    param_descriptions={
        "prompt": (
            "Instruction describing what to analyze or what insight to generate "
            "from the dependency data. E.g. 'Summarize the main themes in these posts'"
        ),
    },
)
@task(name="ai_insight", retries=1, retry_delay_seconds=5)
def ai_insight(prompt: str, **context: Any) -> dict:
    """Generate an AI-powered insight from dependency node results.

    The orchestrator injects the results of all ``depends_on`` nodes as
    keyword arguments (``context``), so their data is available for analysis.
    """
    vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)

    model = GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=_SYSTEM_PROMPT,
    )

    context_block = json.dumps(context, indent=2, default=str)
    user_message = (
        f"## Instruction\n{prompt}\n\n"
        f"## Data from previous pipeline steps\n```json\n{context_block}\n```"
    )

    response = model.generate_content(
        user_message,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4096,
        },
    )

    return {
        "insight": response.text.strip(),
        "prompt": prompt,
        "context_keys": list(context.keys()),
    }
