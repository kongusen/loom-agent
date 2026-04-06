"""LSP 工具"""

from typing import Any


async def lsp_get_diagnostics(uri: str | None = None) -> dict[str, Any]:
    """获取语言诊断信息"""
    return {
        "uri": uri,
        "diagnostics": [],
        "message": "LSP not implemented"
    }


async def lsp_execute_code(code: str) -> dict[str, Any]:
    """执行代码（REPL）"""
    return {
        "code": code,
        "output": None,
        "message": "Code execution not implemented"
    }
