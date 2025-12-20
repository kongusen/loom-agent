"""
Loom Studio Database
使用 SQLite 存储 Trace 和 Events
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

class TraceDB:
    def __init__(self, db_path: str = "loom.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Trace 表：一次完整的执行（Run）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT,
                    metadata TEXT
                )
            """)
            
            # Events 表：详细的事件流
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT,
                    type TEXT,
                    agent_name TEXT,
                    data TEXT,
                    timestamp REAL,
                    FOREIGN KEY(trace_id) REFERENCES traces(id)
                )
            """)
            conn.commit()

    def create_trace(self, name: str = "Untitled Trace") -> str:
        trace_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO traces (id, name, start_time, status, metadata) VALUES (?, ?, ?, ?, ?)",
                (trace_id, name, datetime.now(), "running", "{}")
            )
        return trace_id

    def add_event(self, trace_id: str, event: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (trace_id, type, agent_name, data, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    trace_id,
                    event.get("type"),
                    event.get("agent_name"),
                    json.dumps(event.get("data", {})),
                    event.get("timestamp")
                )
            )
            
            # 如果是 End 事件，更新 Trace 状态
            if event.get("type", "").endswith("_end") and not event.get("agent_name"):
                # 只有顶层结束才算结束？这里简化处理，任何 END 都更新一下最后时间
                conn.execute(
                    "UPDATE traces SET end_time = ?, status = ? WHERE id = ?",
                    (datetime.now(), "completed", trace_id)
                )

    def get_traces(self, limit: int = 50) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM traces ORDER BY start_time DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_trace_events(self, trace_id: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM events WHERE trace_id = ? ORDER BY id ASC", (trace_id,))
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                d = dict(row)
                d["data"] = json.loads(d["data"]) if d["data"] else {}
                events.append(d)
            return events

    def get_trace_details(self, trace_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            trace = dict(row)
            trace["events"] = self.get_trace_events(trace_id)
            return trace
