"""
文件系统技能

提供文件读写操作能力。
"""

import os
from typing import List
from loom.stdlib.skills.base import Skill
from loom.node.tool import ToolNode
from loom.weave import create_tool


class FileSystemSkill(Skill):
    """
    文件系统技能。

    提供基本的文件读写操作。
    """

    def __init__(self, base_dir: str = "."):
        """
        初始化文件系统技能。

        Args:
            base_dir: 基础目录，限制文件操作范围
        """
        super().__init__(
            name="filesystem",
            description="读写文件"
        )
        self.base_dir = os.path.abspath(base_dir)

    def get_tools(self) -> List[ToolNode]:
        """返回文件系统工具"""

        def read_file(path: str) -> str:
            """
            读取文件内容。

            Args:
                path: 文件路径

            Returns:
                文件内容
            """
            try:
                full_path = os.path.join(self.base_dir, path)
                # 安全检查：确保路径在 base_dir 内
                if not os.path.abspath(full_path).startswith(self.base_dir):
                    return "错误：路径超出允许范围"

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"文件内容:\n{content}"
            except Exception as e:
                return f"读取错误: {str(e)}"

        def write_file(path: str, content: str) -> str:
            """
            写入文件内容。

            Args:
                path: 文件路径
                content: 要写入的内容

            Returns:
                操作结果
            """
            try:
                full_path = os.path.join(self.base_dir, path)
                # 安全检查
                if not os.path.abspath(full_path).startswith(self.base_dir):
                    return "错误：路径超出允许范围"

                # 确保目录存在
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"成功写入文件: {path}"
            except Exception as e:
                return f"写入错误: {str(e)}"

        return [
            create_tool("read_file", read_file, "读取文件内容"),
            create_tool("write_file", write_file, "写入文件内容")
        ]

    def get_system_prompt(self) -> str:
        """返回文件系统的系统提示词"""
        return f"""你可以使用文件系统工具来读写文件。
- read_file: 读取文件内容
- write_file: 写入文件内容
所有文件操作限制在目录: {self.base_dir}"""
