"""
08_sandbox_tools.py - 沙盒工具

演示：
- Sandbox 创建
- 文件/Bash/搜索工具
- 安全的工具执行环境
"""

import asyncio
import tempfile
from pathlib import Path

from loom.tools.builtin.bash import create_bash_tool
from loom.tools.builtin.file import create_file_tools
from loom.tools.core.sandbox import Sandbox


async def main():
    # 1. 创建临时沙盒目录
    sandbox_dir = tempfile.mkdtemp(prefix="loom_demo_")
    print(f"沙盒目录: {sandbox_dir}")

    # 2. 创建 Sandbox
    sandbox = Sandbox(sandbox_dir, auto_create=True)

    # 3. 创建文件工具
    file_tools = create_file_tools(sandbox)
    print(f"文件工具: {[t['function']['name'] for t in file_tools]}")

    # 4. 创建 Bash 工具
    bash_tool = create_bash_tool(sandbox, timeout=10.0)
    print(f"Bash 工具: {bash_tool['function']['name']}")

    # 5. 使用沙盒写入文件
    test_file = Path(sandbox_dir) / "test.txt"
    test_file.write_text("Hello from sandbox!")
    print(f"写入文件: {test_file}")

    # 6. 验证文件
    content = test_file.read_text()
    print(f"文件内容: {content}")


if __name__ == "__main__":
    asyncio.run(main())
