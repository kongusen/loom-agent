"""
File Tools - 文件操作工具集

提供安全的文件读写和编辑功能，所有操作都在沙箱内进行。

工具列表：
1. read_file - 读取文件内容
2. write_file - 写入文件内容
3. edit_file - 编辑文件（字符串替换）

所有操作都通过沙箱验证，确保不会访问沙箱外的文件。
"""

from loom.tools.sandbox import Sandbox, SandboxViolation


class FileTools:
    """
    文件操作工具集

    提供安全的文件读写和编辑功能。
    """

    def __init__(self, sandbox: Sandbox):
        """
        初始化文件工具

        Args:
            sandbox: 沙箱实例
        """
        self.sandbox = sandbox

    async def read_file(self, file_path: str) -> dict[str, str]:
        """
        读取文件内容

        Args:
            file_path: 文件路径（相对于沙箱根目录）

        Returns:
            结果字典，包含：
            - content: 文件内容
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        try:
            content = self.sandbox.safe_read(file_path)
            return {
                "content": content,
                "success": "true",
            }
        except SandboxViolation as e:
            return {
                "content": "",
                "success": "false",
                "error": f"Sandbox violation: {str(e)}",
            }
        except FileNotFoundError:
            return {
                "content": "",
                "success": "false",
                "error": f"File not found: {file_path}",
            }
        except Exception as e:
            return {
                "content": "",
                "success": "false",
                "error": f"Read error: {str(e)}",
            }

    async def write_file(
        self,
        file_path: str,
        content: str,
        create_dirs: bool = True,
    ) -> dict[str, str]:
        """
        写入文件内容

        Args:
            file_path: 文件路径（相对于沙箱根目录）
            content: 文件内容
            create_dirs: 是否自动创建父目录

        Returns:
            结果字典，包含：
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        try:
            self.sandbox.safe_write(file_path, content, create_dirs=create_dirs)
            return {
                "success": "true",
                "message": f"File written successfully: {file_path}",
            }
        except SandboxViolation as e:
            return {
                "success": "false",
                "error": f"Sandbox violation: {str(e)}",
            }
        except Exception as e:
            return {
                "success": "false",
                "error": f"Write error: {str(e)}",
            }

    async def edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
    ) -> dict[str, str]:
        """
        编辑文件（字符串替换）

        Args:
            file_path: 文件路径（相对于沙箱根目录）
            old_string: 要替换的字符串
            new_string: 新字符串

        Returns:
            结果字典，包含：
            - success: 是否成功
            - replacements: 替换次数
            - error: 错误信息（如果失败）
        """
        try:
            # 读取文件
            content = self.sandbox.safe_read(file_path)

            # 检查 old_string 是否存在
            if old_string not in content:
                return {
                    "success": "false",
                    "error": f"String not found in file: {old_string}",
                }

            # 执行替换
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)

            # 写回文件
            self.sandbox.safe_write(file_path, new_content)

            return {
                "success": "true",
                "message": f"File edited successfully: {file_path}",
                "replacements": str(replacements),
            }
        except SandboxViolation as e:
            return {
                "success": "false",
                "error": f"Sandbox violation: {str(e)}",
            }
        except FileNotFoundError:
            return {
                "success": "false",
                "error": f"File not found: {file_path}",
            }
        except Exception as e:
            return {
                "success": "false",
                "error": f"Edit error: {str(e)}",
            }


def create_file_tools(sandbox: Sandbox) -> list[dict]:
    """
    创建文件工具集

    Args:
        sandbox: 沙箱实例

    Returns:
        工具定义列表
    """
    tools = FileTools(sandbox)

    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": f"Read file content from the sandbox ({sandbox.root_dir}). "
                "Provide the file path relative to the sandbox root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to sandbox root)",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            "_executor": tools.read_file,
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": f"Write content to a file in the sandbox ({sandbox.root_dir}). "
                "Creates parent directories if needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to sandbox root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
            "_executor": tools.write_file,
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": f"Edit a file by replacing a string in the sandbox ({sandbox.root_dir}). "
                "All occurrences of old_string will be replaced with new_string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to sandbox root)",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "String to replace",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "Replacement string",
                        },
                    },
                    "required": ["file_path", "old_string", "new_string"],
                },
            },
            "_executor": tools.edit_file,
        },
    ]
