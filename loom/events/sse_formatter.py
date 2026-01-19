"""
SSE Formatter - Server-Sent Events格式化工具

基于公理A2（事件主权公理）和Google A2A协议标准。
提供SSE格式化功能。

设计原则：
1. 轻量级 - 基于HTTP协议
2. 标准化 - 符合SSE规范
3. 简单专注 - 只负责格式化，序列化由Pydantic处理
"""


class SSEFormatter:
    """
    SSE格式化工具

    提供SSE事件流格式化功能。
    任务序列化由Pydantic的model_dump_json()处理。
    """

    @staticmethod
    def format_sse_message(event_type: str, data: str, event_id: str | None = None) -> str:
        """
        格式化SSE消息

        SSE格式：
        id: <event_id>
        event: <event_type>
        data: <data>
        (空行)

        Args:
            event_type: 事件类型
            data: 事件数据
            event_id: 事件ID（可选）

        Returns:
            格式化的SSE消息
        """
        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event_type}")
        lines.append(f"data: {data}")
        lines.append("")  # 空行表示消息结束
        return "\n".join(lines) + "\n"
