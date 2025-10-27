"""Doris 元数据访问封装。

基于 Loom 0.0.3 重构模式，优化缓存机制和性能。
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from .config import SQLTemplateConfig


@dataclass(frozen=True)
class TableColumn:
    name: str
    data_type: str
    comment: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    comment: str
    columns: List[TableColumn]


class DorisSchemaExplorer:
    """负责连接 Doris 并获取指定数据库的表结构。
    
    基于 Loom 0.0.3 重构模式，优化缓存机制和性能。
    """

    def __init__(
        self,
        *,
        hosts: List[str],
        mysql_port: int,
        user: str,
        password: str,
        database: str,
        connect_timeout: int = 10,
        config: Optional[SQLTemplateConfig] = None,
    ) -> None:
        self.hosts = hosts
        self.mysql_port = mysql_port
        self.user = user
        self.password = password
        self.database = database
        self.timeout = connect_timeout
        self.config = config or SQLTemplateConfig()
        
        # 优化的缓存机制
        self._schema_cache: Optional[Dict[str, TableInfo]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_hash: Optional[str] = None

    async def load_schema(self) -> Dict[str, TableInfo]:
        """加载数据库模式，使用优化的缓存机制。"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._schema_cache is not None and 
            self._cache_timestamp is not None and
            current_time - self._cache_timestamp < self.config.schema_cache_ttl):
            return self._schema_cache
        
        # 重新加载模式
        self._schema_cache = await asyncio.to_thread(self._load_schema_sync)
        self._cache_timestamp = current_time
        self._cache_hash = self._compute_schema_hash(self._schema_cache)
        
        return self._schema_cache

    async def fetch_table_columns(self, table: str) -> Optional[TableInfo]:
        """获取指定表的列信息。"""
        schema = await self.load_schema()
        return schema.get(table)
    
    def _compute_schema_hash(self, schema: Dict[str, TableInfo]) -> str:
        """使用 blake2b 计算模式哈希，基于 Loom 0.0.3 优化。"""
        hasher = hashlib.blake2b(digest_size=16)
        
        for table_name, table_info in schema.items():
            hasher.update(table_name.encode())
            hasher.update(table_info.comment.encode())
            for column in table_info.columns:
                hasher.update(column.name.encode())
                hasher.update(column.data_type.encode())
                hasher.update(column.comment.encode())
        
        return hasher.hexdigest()
    
    def invalidate_cache(self) -> None:
        """手动使缓存失效。"""
        self._schema_cache = None
        self._cache_timestamp = None
        self._cache_hash = None

    def _load_schema_sync(self) -> Dict[str, TableInfo]:
        last_error: Exception | None = None
        for host in self.hosts:
            try:
                return self._fetch_schema_from_host(host)
            except Exception as exc:  # pragma: no cover - 真实服务异常时触发
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Unable to load schema from any Doris host.")

    def _fetch_schema_from_host(self, host: str) -> Dict[str, TableInfo]:
        conn = pymysql.connect(
            host=host,
            port=self.mysql_port,
            user=self.user,
            password=self.password,
            database="information_schema",
            cursorclass=DictCursor,
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        t.table_name,
                        IFNULL(t.table_comment, '') AS table_comment,
                        c.column_name,
                        c.data_type,
                        IFNULL(c.column_comment, '') AS column_comment,
                        c.ordinal_position
                    FROM tables AS t
                    JOIN columns AS c
                      ON c.table_schema = t.table_schema
                     AND c.table_name = t.table_name
                    WHERE t.table_schema = %s
                    ORDER BY t.table_name, c.ordinal_position
                    """,
                    (self.database,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        tables: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            table_name = row["table_name"]
            entry = tables.setdefault(
                table_name,
                {
                    "comment": row["table_comment"],
                    "columns": [],
                },
            )
            entry["columns"].append(
                TableColumn(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    comment=row["column_comment"],
                )
            )

        return {
            name: TableInfo(
                name=name,
                comment=data["comment"],
                columns=data["columns"],
            )
            for name, data in tables.items()
        }

    def open_connection(self):
        """以同步方式返回一个连接，供查询工具使用。"""
        last_error: Exception | None = None
        for host in self.hosts:
            try:
                return pymysql.connect(
                    host=host,
                    port=self.mysql_port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    cursorclass=DictCursor,
                    connect_timeout=self.timeout,
                    read_timeout=self.timeout,
                    charset="utf8mb4",
                )
            except Exception as exc:  # pragma: no cover
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Unable to establish connection to Doris.")
