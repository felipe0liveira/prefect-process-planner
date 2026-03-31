from prefect import task
from simpleeval import simple_eval


@task(name="check_condition")
def check_condition(
    expression: str,
    error_message: str = "Condition failed",
    **context: object,
) -> dict:
    """Evaluate an expression against dependency results.

    The orchestrator injects the results of all depends_on nodes as
    keyword arguments (``context``), so variable names in the expression
    must match the dependency node IDs.

    Raises ``ValueError`` when the expression evaluates to a falsy value.
    """
    result = simple_eval(expression, names=context, functions={"len": len})
    if not result:
        raise ValueError(error_message)
    return {"expression": expression, "result": result}
