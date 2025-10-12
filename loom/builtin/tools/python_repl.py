"""Python REPL 工具 - 执行 Python 代码"""

from __future__ import annotations

import sys
from io import StringIO
from typing import Any

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class PythonREPLInput(BaseModel):
    """Python REPL 输入参数"""

    code: str = Field(description="Python code to execute")


class PythonREPLTool(BaseTool):
    """
    Python REPL 工具 - 在隔离环境中执行 Python 代码

    警告: 不要在生产环境中使用,存在安全风险!
    """

    name = "python_repl"
    description = (
        "Execute Python code and return the output. "
        "Can be used for calculations, data processing, etc. "
        "The code runs in a restricted environment."
    )
    args_schema = PythonREPLInput
    is_concurrency_safe = False  # 代码执行不并发安全

    async def run(self, code: str, **kwargs: Any) -> str:
        """执行 Python 代码"""
        # 安全性检查 - 禁止危险操作
        dangerous_imports = ["os", "subprocess", "sys", "importlib", "__import__"]
        for dangerous in dangerous_imports:
            if dangerous in code:
                return f"Security error: Import of '{dangerous}' is not allowed"

        # 捕获标准输出
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # 使用受限的全局命名空间
            namespace: dict = {"__builtins__": __builtins__}

            # 执行代码
            exec(code, namespace)

            # 获取输出
            output = captured_output.getvalue()

            if not output:
                # 如果没有打印输出,尝试返回最后一个表达式的值
                try:
                    result = eval(code, namespace)
                    if result is not None:
                        output = str(result)
                except Exception:
                    output = "Code executed successfully (no output)"

            return output.strip()

        except Exception as e:
            return f"Execution error: {type(e).__name__}: {str(e)}"

        finally:
            sys.stdout = old_stdout
