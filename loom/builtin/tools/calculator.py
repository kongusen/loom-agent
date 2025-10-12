from __future__ import annotations

import ast
import operator as op
from typing import Any

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class CalcArgs(BaseModel):
    expression: str = Field(description="Arithmetic expression, e.g., '2+2*3'")


class Calculator(BaseTool):
    name = "calculator"
    description = "Evaluate simple arithmetic expressions"
    args_schema = CalcArgs

    async def run(self, **kwargs) -> Any:
        expr = kwargs.get("expression", "")
        return str(_safe_eval(expr))


# 安全 eval：仅支持基本算术
_ops = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}


def _safe_eval(expr: str) -> Any:
    def _eval(node: ast.AST) -> Any:
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            return _ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _ops[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body)

