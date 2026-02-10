"""
Search Tools - 搜索工具集

提供文件名和内容搜索功能，所有操作都在沙箱内进行。

工具列表：
1. glob - 文件名模式匹配
2. grep - 文件内容搜索

所有操作都通过沙箱验证，确保不会访问沙箱外的文件。
"""

import re

from loom.tools.mcp_types import MCPToolDefinition
from loom.tools.core.sandbox import Sandbox

# Optional import for SandboxToolManager
try:
    from loom.tools.core.sandbox_manager import SandboxToolManager, ToolScope
except ImportError:
    SandboxToolManager = None  # type: ignore
    ToolScope = None  # type: ignore


class SearchTools:
    """
    搜索工具集

    提供文件名和内容搜索功能。
    """

    def __init__(self, sandbox: Sandbox):
        """
        初始化搜索工具

        Args:
            sandbox: 沙箱实例
        """
        self.sandbox = sandbox

    async def glob(
        self,
        pattern: str,
        max_results: int = 100,
    ) -> dict[str, str | list[str]]:
        """
        文件名模式匹配

        Args:
            pattern: Glob 模式（如 "*.py", "**/*.txt"）
            max_results: 最大结果数

        Returns:
            结果字典，包含：
            - files: 匹配的文件列表（相对路径）
            - count: 匹配数量
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        try:
            # 在沙箱根目录中执行 glob
            matches = list(self.sandbox.root_dir.glob(pattern))

            # 限制结果数量
            matches = matches[:max_results]

            # 转换为相对路径
            relative_paths = [str(match.relative_to(self.sandbox.root_dir)) for match in matches]

            return {
                "files": relative_paths,
                "count": str(len(relative_paths)),
                "success": "true",
            }
        except Exception as e:
            return {
                "files": [],
                "count": "0",
                "success": "false",
                "error": f"Glob error: {str(e)}",
            }

    async def grep(
        self,
        pattern: str,
        file_pattern: str = "**/*",
        max_results: int = 100,
        case_sensitive: bool = True,
    ) -> dict[str, str | list[dict]]:
        """
        文件内容搜索

        Args:
            pattern: 搜索模式（正则表达式）
            file_pattern: 文件名模式（默认搜索所有文件）
            max_results: 最大结果数
            case_sensitive: 是否区分大小写

        Returns:
            结果字典，包含：
            - matches: 匹配列表，每个匹配包含 file, line_number, line
            - count: 匹配数量
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        try:
            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            # 获取要搜索的文件
            files = list(self.sandbox.root_dir.glob(file_pattern))

            matches = []
            for file_path in files:
                # 只搜索文件，跳过目录
                if not file_path.is_file():
                    continue

                # 跳过二进制文件（简单检测）
                try:
                    content = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue

                # 搜索每一行
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        relative_path = str(file_path.relative_to(self.sandbox.root_dir))
                        matches.append(
                            {
                                "file": relative_path,
                                "line_number": line_num,
                                "line": line.strip(),
                            }
                        )

                        # 限制结果数量
                        if len(matches) >= max_results:
                            break

                if len(matches) >= max_results:
                    break

            return {
                "matches": matches,
                "count": str(len(matches)),
                "success": "true",
            }
        except re.error as e:
            return {
                "matches": [],
                "count": "0",
                "success": "false",
                "error": f"Invalid regex pattern: {str(e)}",
            }
        except Exception as e:
            return {
                "matches": [],
                "count": "0",
                "success": "false",
                "error": f"Grep error: {str(e)}",
            }


def create_search_tools(sandbox: Sandbox) -> list[dict]:
    """
    创建搜索工具集

    Args:
        sandbox: 沙箱实例

    Returns:
        工具定义列表
    """
    tools = SearchTools(sandbox)

    return [
        {
            "type": "function",
            "function": {
                "name": "glob",
                "description": f"Search for files by name pattern in the sandbox ({sandbox.root_dir}). "
                "Supports glob patterns like '*.py', '**/*.txt', etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '*.py', '**/*.txt')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 100)",
                            "default": 100,
                        },
                    },
                    "required": ["pattern"],
                },
            },
            "_executor": tools.glob,
        },
        {
            "type": "function",
            "function": {
                "name": "grep",
                "description": f"Search for text patterns in files in the sandbox ({sandbox.root_dir}). "
                "Uses regular expressions for pattern matching.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (regular expression)",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "File name pattern to search in (default: '**/*')",
                            "default": "**/*",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 100)",
                            "default": 100,
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether to match case sensitively (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["pattern"],
                },
            },
            "_executor": tools.grep,
        },
    ]


async def register_search_tools_to_manager(
    manager: "SandboxToolManager",
) -> None:
    """
    注册搜索工具到沙盒工具管理器

    这是新的推荐方式，通过 SandboxToolManager 管理所有工具。

    Args:
        manager: 沙盒工具管理器实例

    Example:
        manager = SandboxToolManager(sandbox)
        await register_search_tools_to_manager(manager)
        # 工具已注册，可以通过 manager.execute_tool() 调用
    """
    if SandboxToolManager is None or ToolScope is None:
        raise ImportError("SandboxToolManager is not available")

    tools = SearchTools(manager.sandbox)

    # 注册 glob 工具
    glob_definition = MCPToolDefinition(
        name="glob",
        description=f"Search for files by name pattern in the sandbox ({manager.sandbox.root_dir}). "
        "Supports glob patterns like '*.py', '**/*.txt', etc.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '*.py', '**/*.txt')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 100)",
                },
            },
            "required": ["pattern"],
        },
    )
    await manager.register_tool(
        "glob",
        tools.glob,
        glob_definition,
        ToolScope.SANDBOXED,
    )

    # 注册 grep 工具
    grep_definition = MCPToolDefinition(
        name="grep",
        description=f"Search for text patterns in files in the sandbox ({manager.sandbox.root_dir}). "
        "Uses regular expressions for pattern matching.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (regular expression)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File name pattern to search in (default: '**/*')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 100)",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether to match case sensitively (default: true)",
                },
            },
            "required": ["pattern"],
        },
    )
    await manager.register_tool(
        "grep",
        tools.grep,
        grep_definition,
        ToolScope.SANDBOXED,
    )
