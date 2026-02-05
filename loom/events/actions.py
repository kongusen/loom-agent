"""
事件动作类型定义

提供类型安全的事件动作枚举，替代字符串键值。
"""

from enum import Enum


class TaskAction(str, Enum):
    """任务动作类型（类型安全）"""

    EXECUTE = "execute"
    CANCEL = "cancel"
    QUERY = "query"
    STREAM = "stream"


class MemoryAction(str, Enum):
    """记忆动作类型（类型安全）"""

    READ = "read_memory"
    WRITE = "write_memory"
    SEARCH = "search_memory"
    SYNC = "sync_memory"


class AgentAction(str, Enum):
    """Agent动作类型（类型安全）"""

    START = "start_agent"
    STOP = "stop_agent"
    STATUS = "agent_status"
    HEARTBEAT = "agent_heartbeat"
