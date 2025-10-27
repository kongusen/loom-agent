"""SQL 模板代理工具集。

基于 Loom 0.0.3 重构模式，优化工具性能和错误处理。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from loom.interfaces.tool import BaseTool

from .config import SQLTemplateConfig
from .metadata import DorisSchemaExplorer, TableInfo


class SchemaLookupArgs(BaseModel):
    placeholder: str = Field(description="正在分析的占位符，例如 '统计:总销售额'")
    hint: Optional[str] = Field(
        default=None, description="额外提示信息，例如占位符所属模块或指标含义"
    )
    table: Optional[str] = Field(
        default=None, description="指定表名，若已知候选表可加速查询"
    )


class DorisSelectArgs(BaseModel):
    sql: str = Field(description="需要执行的 SELECT 语句")
    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="最大返回行数，避免大结果集",
    )

    @validator("sql")
    def ensure_select(cls, value: str) -> str:
        statement = value.strip().lower()
        if not statement.startswith("select"):
            raise ValueError("只允许执行 SELECT 查询。")
        if ";" in statement[:-1]:
            raise ValueError("不允许一次执行多条语句。")
        return value


class SchemaLookupTool(BaseTool):
    """调用 Doris 信息模式，提供字段与表的候选信息。
    
    基于 Loom 0.0.3 重构模式，优化性能和配置管理。
    """

    name = "schema_lookup"
    description = "根据占位符需求搜索 Doris 数据库中的表和字段。"
    args_schema = SchemaLookupArgs
    is_read_only = True
    category = "general"

    def __init__(self, explorer: DorisSchemaExplorer) -> None:
        self._explorer = explorer

    async def run(self, **kwargs: Any) -> str:
        args = SchemaLookupArgs(**kwargs)
        schema = await self._explorer.load_schema()

        def score_table(table: TableInfo) -> int:
            base = 0
            text = f"{table.name} {table.comment}".lower()
            tokens = args.placeholder.lower().replace("_", " ").split()
            for token in tokens:
                if token in text:
                    base += 2
            hint = (args.hint or "").lower()
            if hint:
                for token in hint.split():
                    if token in text:
                        base += 1
            return base

        ranked_tables = sorted(
            schema.values(),
            key=score_table,
            reverse=True,
        )

        candidates: List[Dict[str, Any]] = []
        max_tables = self._explorer.config.max_schema_tables
        max_columns = self._explorer.config.max_table_columns
        
        for table in ranked_tables[:max_tables]:
            if args.table and table.name != args.table:
                continue
            column_matches: List[Dict[str, Any]] = []
            placeholder_lower = args.placeholder.lower()
            for column in table.columns:
                match_score = 0
                if column.name.lower() in placeholder_lower:
                    match_score += 3
                if (args.hint or "").lower() in column.comment.lower():
                    match_score += 1
                column_matches.append(
                    {
                        "column": column.name,
                        "data_type": column.data_type,
                        "comment": column.comment,
                        "score": match_score,
                    }
                )

            candidates.append(
                {
                    "table": table.name,
                    "table_comment": table.comment,
                    "columns": sorted(
                        column_matches, key=lambda item: item["score"], reverse=True
                    )[:max_columns],
                }
            )

        payload = {
            "placeholder": args.placeholder,
            "hint": args.hint,
            "candidates": candidates[:5],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


class DorisSelectTool(BaseTool):
    """在 Doris 中执行只读 SQL 查询。
    
    基于 Loom 0.0.3 重构模式，优化错误处理和超时管理。
    """

    name = "doris_select"
    description = "执行只读 SQL（SELECT），用于验证聚合逻辑或查看样例数据。"
    args_schema = DorisSelectArgs
    is_read_only = True
    category = "general"

    def __init__(self, explorer: DorisSchemaExplorer) -> None:
        self._explorer = explorer

    async def run(self, **kwargs: Any) -> str:
        args = DorisSelectArgs(**kwargs)
        return await self._execute_select(args.sql, args.limit)

    async def _execute_select(self, sql: str, limit: int) -> str:
        """执行 SELECT 查询，使用配置的超时时间。"""
        timeout = self._explorer.config.query_timeout
        return await asyncio.wait_for(
            asyncio.to_thread(self._query_sync, sql, limit),
            timeout=timeout
        )

    def _query_sync(self, sql: str, limit: int) -> str:
        """同步执行查询，优化错误处理。"""
        import pymysql

        try:
            conn = self._explorer.open_connection()
        except Exception as exc:
            return json.dumps(
                {
                    "sql": sql,
                    "error": f"连接失败: {str(exc)}",
                    "error_type": "connection_error"
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(f"{sql.strip()} LIMIT {limit}")
                rows = cur.fetchall()
        except Exception as exc:  # pragma: no cover - 取决数据库状态
            return json.dumps(
                {
                    "sql": sql,
                    "error": f"查询执行失败: {str(exc)}",
                    "error_type": "query_error",
                    "hint": "请确认 SQL 语法正确，且仅包含 SELECT。",
                },
                ensure_ascii=False,
                indent=2,
            )
        finally:
            conn.close()

        return json.dumps(
            {
                "sql": sql,
                "limit": limit,
                "rows": rows,
                "row_count": len(rows),
                "status": "success"
            },
            ensure_ascii=False,
            indent=2,
        )
