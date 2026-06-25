"""Safe math expression calculator using Python's ast module."""

import ast
import operator
from dataclasses import dataclass
from morphos.tools.registry import Tool

SAFE_OPS = {
    "Add": operator.add,
    "Sub": operator.sub,
    "Mult": operator.mul,
    "Div": operator.truediv,
    "Pow": operator.pow,
    "USub": operator.neg,
    "UAdd": operator.pos,
}


def _safe_eval(expr: str) -> str:
    """Evaluate a math expression safely using AST."""

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, (ast.Constant, ast.Num)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_name = type(node.op).__name__
            if op_name not in SAFE_OPS:
                raise ValueError(f"Operator '{op_name}' not allowed")
            return SAFE_OPS[op_name](left, right)
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_name = type(node.op).__name__
            if op_name not in SAFE_OPS:
                raise ValueError(f"Operator '{op_name}' not allowed")
            return SAFE_OPS[op_name](operand)
        raise ValueError(f"Unsupported expression: {type(node)}")

    tree = ast.parse(expr, mode="eval")
    result = _eval(tree)

    if isinstance(result, float) and result == int(result):
        return str(int(result))
    return str(result)


@dataclass
class Calculator(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a math expression (e.g. '2+3*4'). Supports basic arithmetic."

    def execute(self, expression: str) -> str:
        try:
            result = _safe_eval(expression.strip())
            return f"= {result}"
        except ZeroDivisionError:
            return "Error: division by zero"
        except Exception as e:
            return f"Syntax error: {e}"
