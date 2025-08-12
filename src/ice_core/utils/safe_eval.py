"""Safe boolean expression evaluator using the Python ``ast`` module.

This helper evaluates simple boolean / arithmetic expressions **without** using
``eval`` or ``exec``.  Only a limited subset of Python syntax is permitted:

* Constants (ints, floats, bools, strings)
* Variable names (looked-up in the provided context dict)
* Boolean operators: ``and``, ``or``, ``not``
* Comparison operators: ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``
* Arithmetic ``+`` ``-`` ``*`` ``/`` ``%`` (if ever needed for metrics)

Attempting to evaluate any other syntax node raises ``ValueError``.

Example
-------
>>> safe_eval_bool("cost < 30 and error_rate < 0.05", {"cost": 25.4, "error_rate": 0.02})
True
"""

from __future__ import annotations

import ast
import operator as _op
from typing import Any, Dict

__all__ = ["safe_eval_bool"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ALLOWED_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.Mod: _op.mod,
}

_ALLOWED_CMP_OPS: dict[type[ast.cmpop], Any] = {
    ast.Eq: _op.eq,
    ast.NotEq: _op.ne,
    ast.Lt: _op.lt,
    ast.LtE: _op.le,
    ast.Gt: _op.gt,
    ast.GtE: _op.ge,
}

_ALLOWED_BOOL_OPS: dict[type[ast.boolop], Any] = {
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

_ALLOWED_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.Not: _op.not_,
    ast.USub: _op.neg,
    ast.UAdd: _op.pos,
}


class _SafeEvalVisitor(ast.NodeVisitor):
    """AST visitor that safely evaluates supported nodes."""

    def __init__(self, context: Dict[str, Any]):
        self._ctx = context

    # pylint: disable=invalid-name
    def visit(self, node: ast.AST) -> Any:  # type: ignore[override]
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.BoolOp):
            return self._eval_boolop(node)
        if isinstance(node, ast.BinOp):
            return self._eval_binop(node)
        if isinstance(node, ast.UnaryOp):
            return self._eval_unaryop(node)
        if isinstance(node, ast.Compare):
            return self._eval_compare(node)
        if isinstance(node, ast.Name):
            if node.id in self._ctx:
                return self._ctx[node.id]
            raise ValueError(f"Unknown variable '{node.id}' in expression.")
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(
            f"Unsupported expression element: {ast.dump(node, annotate_fields=False)}"
        )

    # ---------------------------------------------------------------------
    # Eval helpers
    # ---------------------------------------------------------------------
    def _eval_boolop(self, node: ast.BoolOp) -> Any:
        op_func = _ALLOWED_BOOL_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError("Unsupported boolean operator.")
        result = self.visit(node.values[0])
        for value in node.values[1:]:
            result = op_func(result, self.visit(value))
        return result

    def _eval_binop(self, node: ast.BinOp) -> Any:
        op_func = _ALLOWED_BIN_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError("Unsupported binary operator.")
        return op_func(self.visit(node.left), self.visit(node.right))

    def _eval_unaryop(self, node: ast.UnaryOp) -> Any:
        op_func = _ALLOWED_UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError("Unsupported unary operator.")
        return op_func(self.visit(node.operand))

    def _eval_compare(self, node: ast.Compare) -> Any:
        left_val = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            op_func = _ALLOWED_CMP_OPS.get(type(op))
            if op_func is None:
                raise ValueError("Unsupported comparison operator.")
            right_val = self.visit(comparator)
            if not op_func(left_val, right_val):
                return False
            left_val = right_val  # For chained comparisons
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def safe_eval_bool(expression: str, context: Dict[str, Any] | None = None) -> bool:  # noqa: D401
    """Evaluate a simple boolean expression safely.

    Parameters
    ----------
    expression : str
        Expression to evaluate (e.g. ``"cost < 30 and error_rate < 0.05"``).
    context : dict[str, Any] | None
        Mapping of variable names to values.

    Returns
    -------
    bool
        Resulting boolean value.

    Raises
    ------
    ValueError
        If the expression contains unsupported syntax or unknown variables.
    """
    if context is None:
        context = {}

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:  # pragma: no cover – caught upstream
        raise ValueError(f"Invalid expression syntax: {expression}") from exc

    visitor = _SafeEvalVisitor(context)
    result = visitor.visit(tree)
    return bool(result)
