"""
Script Compiler - 将 Skill 脚本编译为可执行函数

支持将 Python 脚本编译为可以在沙盒中执行的函数。
"""

from typing import Any, Callable


class ScriptCompiler:
    """
    脚本编译器

    将 Skill 中的脚本编译为可执行的 Python 函数
    """

    def compile_script(
        self,
        script_content: str,
        script_name: str,
    ) -> Callable:
        """
        编译脚本为可执行函数

        Args:
            script_content: 脚本内容（Python 代码）
            script_name: 脚本名称（用于错误报告）

        Returns:
            可执行的异步函数

        Raises:
            SyntaxError: 脚本语法错误
            ValueError: 脚本格式不正确
        """
        # 1. 验证脚本内容
        if not script_content or not script_content.strip():
            raise ValueError(f"Script '{script_name}' is empty")

        # 2. 编译脚本
        try:
            # 创建一个命名空间来执行脚本
            namespace: dict[str, Any] = {}

            # 编译并执行脚本（定义函数）
            exec(script_content, namespace)

            # 3. 查找主函数
            # 约定：脚本应该定义一个 main() 或 execute() 函数
            main_func = namespace.get("main") or namespace.get("execute")

            if main_func is None:
                raise ValueError(
                    f"Script '{script_name}' must define a 'main()' or 'execute()' function"
                )

            if not callable(main_func):
                raise ValueError(
                    f"Script '{script_name}': 'main' or 'execute' is not callable"
                )

            return main_func

        except SyntaxError as e:
            raise SyntaxError(
                f"Script '{script_name}' has syntax error: {e}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Failed to compile script '{script_name}': {e}"
            ) from e

    def create_tool_wrapper(
        self,
        func: Callable,
        tool_name: str,
        description: str,
    ) -> dict[str, Any]:
        """
        为编译后的函数创建 Tool 包装器

        Args:
            func: 编译后的函数
            tool_name: Tool 名称
            description: Tool 描述

        Returns:
            Tool 定义字典
        """
        return {
            "name": tool_name,
            "description": description,
            "func": func,
        }
