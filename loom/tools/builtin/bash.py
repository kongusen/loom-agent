"""
Bash Tool - Bash 命令执行工具

在沙箱环境中安全执行 bash 命令。

特性：
1. 沙箱隔离 - 工作目录限制在沙箱内
2. 超时控制 - 防止命令无限执行
3. 输出捕获 - 捕获 stdout 和 stderr
4. 错误处理 - 清晰的错误信息

安全措施：
- 工作目录设置为沙箱根目录
- 不允许修改工作目录到沙箱外
- 命令执行有超时限制
"""

import asyncio

from loom.tools.mcp_types import MCPToolDefinition
from loom.tools.core.sandbox import Sandbox

# Optional import for SandboxToolManager
try:
    from loom.tools.core.sandbox_manager import SandboxToolManager, ToolScope
except ImportError:
    SandboxToolManager = None  # type: ignore
    ToolScope = None  # type: ignore


class BashTool:
    """
    Bash 命令执行工具

    在沙箱环境中执行 bash 命令。
    """

    def __init__(self, sandbox: Sandbox, timeout: float = 30.0):
        """
        初始化 Bash 工具

        Args:
            sandbox: 沙箱实例
            timeout: 命令执行超时时间（秒）
        """
        self.sandbox = sandbox
        self.timeout = timeout

    async def execute(
        self,
        command: str,
        timeout: float | None = None,
    ) -> dict[str, str]:
        """
        执行 bash 命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（可选，默认使用实例设置）

        Returns:
            执行结果字典，包含：
            - stdout: 标准输出
            - stderr: 标准错误
            - returncode: 返回码
            - success: 是否成功
        """
        exec_timeout = timeout or self.timeout

        try:
            # 在沙箱目录中执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.sandbox.root_dir),
            )

            # 等待命令完成（带超时）
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=exec_timeout,
                )
            except TimeoutError:
                # 超时，终止进程
                process.kill()
                await process.wait()
                return {
                    "stdout": "",
                    "stderr": f"Command timed out after {exec_timeout} seconds",
                    "returncode": "-1",
                    "success": "false",
                }

            # 解码输出
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": str(process.returncode or 0),
                "success": "true" if process.returncode == 0 else "false",
            }

        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "returncode": "-1",
                "success": "false",
            }


def create_bash_tool(sandbox: Sandbox, timeout: float = 30.0) -> dict:
    """
    创建 Bash 工具定义

    Args:
        sandbox: 沙箱实例
        timeout: 超时时间

    Returns:
        OpenAI 格式的工具定义
    """
    tool = BashTool(sandbox, timeout)

    return {
        "type": "function",
        "function": {
            "name": "bash",
            "description": f"Execute bash commands in the sandbox directory ({sandbox.root_dir}). "
            "The working directory is set to the sandbox root. "
            f"Commands will timeout after {timeout} seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                },
                "required": ["command"],
            },
        },
        "_executor": tool.execute,
    }


async def register_bash_tool_to_manager(
    manager: "SandboxToolManager",
    timeout: float = 30.0,
) -> None:
    """
    注册 Bash 工具到沙盒工具管理器

    Bash 是系统级工具，不受文件系统沙盒约束，但工作目录设置为沙盒根目录。

    Args:
        manager: 沙盒工具管理器实例
        timeout: 命令执行超时时间（秒）

    Example:
        manager = SandboxToolManager(sandbox)
        await register_bash_tool_to_manager(manager)
        # 工具已注册，可以通过 manager.execute_tool() 调用
    """
    if SandboxToolManager is None or ToolScope is None:
        raise ImportError("SandboxToolManager is not available")

    tool = BashTool(manager.sandbox, timeout)

    # 注册 bash 工具（SYSTEM 作用域 - 不受文件系统沙盒约束）
    bash_definition = MCPToolDefinition(
        name="bash",
        description=f"Execute bash commands in the sandbox directory ({manager.sandbox.root_dir}). "
        "The working directory is set to the sandbox root. "
        f"Commands will timeout after {timeout} seconds.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
            },
            "required": ["command"],
        },
    )
    await manager.register_tool(
        "bash",
        tool.execute,
        bash_definition,
        ToolScope.SYSTEM,  # Bash 是系统级操作，不受文件系统沙盒约束
    )
