"""文件操作工具 - 基于 Claude Code 实现"""

from pathlib import Path
from typing import Any
import os


async def read_file(file_path: str, offset: int = 1, limit: int | None = None) -> dict[str, Any]:
    """读取文件内容"""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_lines = len(lines)
    start = max(0, offset - 1)
    end = start + limit if limit else total_lines

    content_lines = lines[start:end]
    content = ''.join(content_lines)

    return {
        "file_path": file_path,
        "content": content,
        "start_line": offset,
        "num_lines": len(content_lines),
        "total_lines": total_lines
    }


async def write_file(file_path: str, content: str) -> dict[str, Any]:
    """写入文件"""
    path = Path(file_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {"file_path": file_path, "status": "written"}


async def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
    """编辑文件 - 精确字符串替换"""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if old_string not in content:
        raise ValueError(f"String not found in file: {old_string}")

    count = content.count(old_string)
    if count > 1 and not replace_all:
        raise ValueError(f"Found {count} matches. Set replace_all=True to replace all.")

    new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {
        "file_path": file_path,
        "old_string": old_string,
        "new_string": new_string,
        "replace_all": replace_all,
        "status": "edited"
    }


async def glob_files(pattern: str, path: str = ".") -> dict[str, Any]:
    """文件模式匹配"""
    from glob import glob
    base_path = Path(path).expanduser().resolve()

    matches = glob(str(base_path / pattern), recursive=True)
    filenames = [str(Path(m).relative_to(base_path)) for m in matches]

    return {
        "pattern": pattern,
        "num_files": len(filenames),
        "filenames": filenames[:100],
        "truncated": len(filenames) > 100
    }


async def grep_files(pattern: str, path: str = ".", glob_pattern: str = "*") -> dict[str, Any]:
    """内容搜索"""
    import re
    from glob import glob as file_glob

    base_path = Path(path).expanduser().resolve()
    files = file_glob(str(base_path / "**" / glob_pattern), recursive=True)

    regex = re.compile(pattern)
    matches = []

    for file in files[:1000]:
        if not Path(file).is_file():
            continue
        try:
            with open(file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(Path(file).relative_to(base_path)),
                            "line": line_num,
                            "content": line.rstrip()
                        })
                        if len(matches) >= 100:
                            break
        except:
            continue

    return {
        "pattern": pattern,
        "num_matches": len(matches),
        "matches": matches,
        "truncated": len(matches) >= 100
    }
