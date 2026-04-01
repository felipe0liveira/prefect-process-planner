import ast
import operator as op

from prefect import task
from simpleeval import SimpleEval

MAX_EXPRESSION_LENGTH = 300

SAFE_OPERATORS: dict[type, object] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.UAdd: op.pos,
    ast.USub: op.neg,
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Gt: op.gt,
    ast.Lt: op.lt,
    ast.GtE: op.ge,
    ast.LtE: op.le,
    ast.Not: op.not_,
    ast.In: lambda x, y: op.contains(y, x),
    ast.NotIn: lambda x, y: not op.contains(y, x),
}

SAFE_FUNCTIONS: dict[str, object] = {"len": len}


def _make_evaluator(names: dict) -> SimpleEval:
    """Create a sandboxed evaluator with only the operators and functions we need."""
    evaluator = SimpleEval()
    evaluator.operators = SAFE_OPERATORS
    evaluator.functions = SAFE_FUNCTIONS
    evaluator.names = names
    return evaluator


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
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(
            f"Expression too long ({len(expression)} chars, "
            f"max {MAX_EXPRESSION_LENGTH})"
        )

    evaluator = _make_evaluator(context)
    result = evaluator.eval(expression)

    if not result:
        raise ValueError(error_message)
    return {"expression": expression, "result": result}
