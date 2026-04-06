"""Notebook 操作工具"""

from typing import Any
import json


async def notebook_edit(notebook_path: str, cell_id: str, new_source: str, cell_type: str = "code") -> dict[str, Any]:
    """编辑 Jupyter Notebook 单元格"""
    with open(notebook_path, 'r') as f:
        notebook = json.load(f)

    for cell in notebook.get('cells', []):
        if cell.get('id') == cell_id:
            cell['source'] = new_source.split('\n')
            cell['cell_type'] = cell_type
            break

    with open(notebook_path, 'w') as f:
        json.dump(notebook, f, indent=2)

    return {"notebook_path": notebook_path, "cell_id": cell_id, "status": "edited"}
