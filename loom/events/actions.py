"""
事件动作类型定义

提供类型安全的事件动作枚举，替代字符串键值。
"""

from enum import StrEnum


class TaskAction(StrEnum):
    """任务动作类型（类型安全）"""

    EXECUTE = "execute"
    CANCEL = "cancel"
    QUERY = "query"
    STREAM = "stream"


class MemoryAction(StrEnum):
    """记忆动作类型（类型安全）"""

    READ = "read_memory"
    WRITE = "write_memory"
    SEARCH = "search_memory"
    SYNC = "sync_memory"


class AgentAction(StrEnum):
    """Agent动作类型（类型安全）"""

    START = "start_agent"
    STOP = "stop_agent"
    STATUS = "agent_status"
    HEARTBEAT = "agent_heartbeat"
