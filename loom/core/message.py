"""
统一消息协议 (Unified Message Protocol)

Loom Agent v0.1.5 的核心消息架构，支持：
- 多模态内容（文本、图片、文件等）
- 工具调用和结果
- 对话树/图结构
- 完整的 OpenAI 兼容性

设计原则：
1. 不可变性 (Immutable) - 使用 frozen dataclass
2. 类型安全 - 完整的类型注解
3. 向后兼容 - 支持纯文本快捷方式
4. 可序列化 - 支持 JSON 序列化/反序列化
5. 可追溯 - 支持 parent_id 构建对话树
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Optional, Dict, Any, List, Union, Literal
from uuid import uuid4
from enum import Enum


# ===== Content Types (多模态内容) =====


class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "text"
    IMAGE_URL = "image_url"
    IMAGE_FILE = "image_file"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass(frozen=True)
class TextContent:
    """文本内容"""
    type: Literal["text"] = "text"
    text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "text": self.text}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TextContent:
        return TextContent(text=data["text"])


@dataclass(frozen=True)
class ImageURLContent:
    """图片 URL 内容"""
    type: Literal["image_url"] = "image_url"
    image_url: str = ""
    detail: Literal["auto", "low", "high"] = "auto"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "image_url": {"url": self.image_url, "detail": self.detail}
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ImageURLContent:
        img_data = data["image_url"]
        return ImageURLContent(
            image_url=img_data["url"],
            detail=img_data.get("detail", "auto")
        )


@dataclass(frozen=True)
class ImageFileContent:
    """图片文件内容（base64 编码）"""
    type: Literal["image_file"] = "image_file"
    data: str = ""  # base64 encoded
    mime_type: str = "image/png"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "mime_type": self.mime_type
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ImageFileContent:
        return ImageFileContent(
            data=data["data"],
            mime_type=data.get("mime_type", "image/png")
        )


@dataclass(frozen=True)
class FileContent:
    """通用文件内容"""
    type: Literal["file"] = "file"
    filename: str = ""
    data: str = ""  # base64 encoded or URL
    mime_type: str = "application/octet-stream"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "filename": self.filename,
            "data": self.data,
            "mime_type": self.mime_type
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> FileContent:
        return FileContent(
            filename=data["filename"],
            data=data["data"],
            mime_type=data.get("mime_type", "application/octet-stream")
        )


# 内容块类型（支持所有多模态内容）
ContentPart = Union[TextContent, ImageURLContent, ImageFileContent, FileContent]


# ===== Tool Calls (工具调用) =====


@dataclass(frozen=True)
class ToolCall:
    """
    工具调用信息

    表示 Agent 请求执行的工具调用。

    Attributes:
        id: 工具调用的唯一标识符
        type: 调用类型（默认 "function"）
        function: 函数调用信息
            - name: 函数名
            - arguments: 函数参数（JSON 字符串）

    Example:
        >>> tool_call = ToolCall(
        ...     id="call_123",
        ...     function=FunctionCall(
        ...         name="get_weather",
        ...         arguments='{"city": "Beijing"}'
        ...     )
        ... )
    """
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall = field(default_factory=lambda: FunctionCall(name="", arguments=""))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments
            }
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ToolCall:
        return ToolCall(
            id=data["id"],
            type=data.get("type", "function"),
            function=FunctionCall(
                name=data["function"]["name"],
                arguments=data["function"]["arguments"]
            )
        )


@dataclass(frozen=True)
class FunctionCall:
    """函数调用信息"""
    name: str
    arguments: str  # JSON string


# ===== Message (统一消息) =====


@dataclass(frozen=True)
class Message:
    """
    统一消息类

    Loom Agent 的核心消息结构，支持：
    - 多模态内容（文本、图片、文件等）
    - 工具调用和结果
    - 对话树结构（parent_id）
    - OpenAI 格式兼容

    Attributes:
        role: 消息角色（user/assistant/system/tool）
        content: 消息内容（支持纯文本或多模态列表）
        name: 可选的发送者名称（用于多 Agent 场景）
        tool_calls: 工具调用列表（仅 assistant 角色）
        tool_call_id: 工具调用 ID（仅 tool 角色）
        metadata: 自定义元数据
        id: 唯一标识符（自动生成）
        timestamp: 创建时间戳（自动生成）
        parent_id: 父消息 ID（用于构建对话树）

    Example:
        >>> # 简单文本消息
        >>> msg = Message(role="user", content="Hello!")

        >>> # 多模态消息
        >>> msg = Message(
        ...     role="user",
        ...     content=[
        ...         TextContent(text="What's in this image?"),
        ...         ImageURLContent(image_url="https://example.com/image.jpg")
        ...     ]
        ... )

        >>> # 工具调用消息
        >>> msg = Message(
        ...     role="assistant",
        ...     content="Let me check the weather",
        ...     tool_calls=[
        ...         ToolCall(
        ...             id="call_123",
        ...             function=FunctionCall(
        ...                 name="get_weather",
        ...                 arguments='{"city": "Beijing"}'
        ...             )
        ...         )
        ...     ]
        ... )

        >>> # 工具结果消息
        >>> msg = Message(
        ...     role="tool",
        ...     content="Temperature is 20°C",
        ...     tool_call_id="call_123",
        ...     name="get_weather"
        ... )
    """

    # 核心字段
    role: str  # user, assistant, system, tool
    content: Union[str, List[ContentPart]]  # 支持文本或多模态内容

    # 工具相关
    tool_calls: Optional[List[ToolCall]] = None  # assistant 角色的工具调用
    tool_call_id: Optional[str] = None  # tool 角色的调用 ID

    # 可选字段
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 自动生成字段
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    # 对话历史（v0.1.9 新增：正式字段，替代影子属性）
    history: Optional[List["Message"]] = field(default=None, repr=False)

    def __post_init__(self):
        """验证消息字段"""
        # 验证 role
        valid_roles = {"user", "assistant", "system", "tool"}
        if self.role not in valid_roles:
            raise ValueError(
                f"Invalid role '{self.role}'. Must be one of: {valid_roles}"
            )

        # 验证 content 类型
        if not isinstance(self.content, (str, list)):
            raise TypeError(
                f"Content must be str or List[ContentPart], got {type(self.content).__name__}"
            )

        # 验证 tool_calls 只用于 assistant
        if self.tool_calls and self.role != "assistant":
            raise ValueError("tool_calls can only be used with role='assistant'")

        # 验证 tool_call_id 只用于 tool
        if self.tool_call_id and self.role != "tool":
            raise ValueError("tool_call_id can only be used with role='tool'")

    # ===== 便捷方法 =====

    def reply(
        self,
        content: Union[str, List[ContentPart]],
        name: Optional[str] = None,
        role: str = "assistant",
        tool_calls: Optional[List[ToolCall]] = None,
    ) -> Message:
        """
        创建对当前消息的回复

        自动设置 parent_id 指向当前消息。

        Args:
            content: 回复内容
            name: 回复者名称
            role: 回复者角色（默认 "assistant"）
            tool_calls: 工具调用列表

        Returns:
            新的 Message 对象
        """
        return Message(
            role=role,
            content=content,
            name=name,
            tool_calls=tool_calls,
            parent_id=self.id,
        )

    def with_history(self, history: List[Message]) -> Message:
        """
        创建带有历史记录的新消息（v0.1.9 优化：使用 dataclass replace）

        这个方法用于为消息附加完整的对话历史。

        Args:
            history: 完整的消息历史列表（包括当前消息）

        Returns:
            带有历史记录的新消息（immutable）

        Note:
            v0.1.9 起使用 dataclasses.replace() 而不是 object.__setattr__()，
            确保类型安全和正确的序列化行为。
        """
        # 使用 dataclasses.replace() 创建不可变副本
        return replace(self, history=history)

    def get_text_content(self) -> str:
        """
        获取纯文本内容

        如果 content 是字符串，直接返回。
        如果是多模态内容，提取所有文本部分并拼接。

        Returns:
            纯文本内容
        """
        if isinstance(self.content, str):
            return self.content

        # 提取所有 TextContent
        texts = [
            part.text
            for part in self.content
            if isinstance(part, TextContent)
        ]
        return " ".join(texts)

    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return self.tool_calls is not None and len(self.tool_calls) > 0

    def is_multimodal(self) -> bool:
        """是否为多模态消息"""
        return isinstance(self.content, list)

    # ===== 序列化 =====

    def to_dict(self, include_history: bool = True) -> Dict[str, Any]:
        """
        序列化为字典（v0.1.9 优化：支持 history）

        Args:
            include_history: 是否包含对话历史（默认 True）
                注意：只序列化一层 history，避免指数级增长

        Returns:
            消息的字典表示

        Note:
            v0.1.9 起正确序列化 history 字段，确保持久化不丢失上下文。
        """
        # 序列化 content
        if isinstance(self.content, str):
            content_data = self.content
        else:
            content_data = [part.to_dict() for part in self.content]

        # 序列化 tool_calls
        tool_calls_data = None
        if self.tool_calls:
            tool_calls_data = [tc.to_dict() for tc in self.tool_calls]

        # 基础数据
        data = {
            "role": self.role,
            "content": content_data,
            "name": self.name,
            "tool_calls": tool_calls_data,
            "tool_call_id": self.tool_call_id,
            "id": self.id,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }

        # 序列化 history（只序列化一层，不递归）
        if include_history and self.history:
            data["history"] = [m.to_dict(include_history=False) for m in self.history]

        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Message:
        """
        从字典反序列化（v0.1.9 优化：恢复 history）

        Args:
            data: 包含消息字段的字典

        Returns:
            Message 对象（包含完整 history）

        Note:
            v0.1.9 起正确恢复 history 字段，确保反序列化不丢失上下文。
        """
        # 反序列化 content
        content_data = data["content"]
        if isinstance(content_data, str):
            content = content_data
        else:
            content = []
            for part_data in content_data:
                part_type = part_data["type"]
                if part_type == "text":
                    content.append(TextContent.from_dict(part_data))
                elif part_type == "image_url":
                    content.append(ImageURLContent.from_dict(part_data))
                elif part_type == "image_file":
                    content.append(ImageFileContent.from_dict(part_data))
                elif part_type == "file":
                    content.append(FileContent.from_dict(part_data))

        # 反序列化 tool_calls
        tool_calls = None
        if data.get("tool_calls"):
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]

        # 反序列化 history（递归）
        history = None
        if data.get("history"):
            history = [Message.from_dict(h) for h in data["history"]]

        return Message(
            role=data["role"],
            content=content,
            name=data.get("name"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
            id=data["id"],
            timestamp=data["timestamp"],
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {}),
            history=history,  # v0.1.9 新增：恢复 history
        )

    def to_openai_format(self) -> Dict[str, Any]:
        """
        转换为 OpenAI API 格式

        Returns:
            OpenAI 格式的消息字典
        """
        result: Dict[str, Any] = {"role": self.role}

        # 处理 content
        if isinstance(self.content, str):
            result["content"] = self.content
        else:
            # 多模态内容
            result["content"] = [part.to_dict() for part in self.content]

        # 可选字段
        if self.name:
            result["name"] = self.name

        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        return result

    @staticmethod
    def from_openai_format(data: Dict[str, Any]) -> Message:
        """
        从 OpenAI 格式创建消息

        Args:
            data: OpenAI 格式的消息字典

        Returns:
            Message 对象
        """
        # 解析 content
        content_data = data["content"]
        if isinstance(content_data, str):
            content = content_data
        else:
            content = []
            for part in content_data:
                if part["type"] == "text":
                    content.append(TextContent(text=part["text"]))
                elif part["type"] == "image_url":
                    img_url = part["image_url"]["url"]
                    detail = part["image_url"].get("detail", "auto")
                    content.append(ImageURLContent(image_url=img_url, detail=detail))

        # 解析 tool_calls
        tool_calls = None
        if "tool_calls" in data:
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]

        return Message(
            role=data["role"],
            content=content,
            name=data.get("name"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
        )

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        name_str = f" ({self.name})" if self.name else ""

        # 内容预览
        if isinstance(self.content, str):
            content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        else:
            types = [part.type for part in self.content]
            content_preview = f"[{', '.join(types)}]"

        # 工具调用标记
        tool_str = ""
        if self.tool_calls:
            tool_names = [tc.function.name for tc in self.tool_calls]
            tool_str = f" +tools({', '.join(tool_names)})"

        return f"Message[{self.role}{name_str}]: {content_preview}{tool_str}"

    def __repr__(self) -> str:
        """详细的字符串表示"""
        return (
            f"Message("
            f"id='{self.id[:8]}...', "
            f"role='{self.role}', "
            f"multimodal={self.is_multimodal()}, "
            f"tool_calls={len(self.tool_calls) if self.tool_calls else 0}, "
            f"parent_id={self.parent_id[:8] + '...' if self.parent_id else None})"
        )


# ===== 便捷工厂函数 =====


def create_user_message(
    content: Union[str, List[ContentPart]],
    name: Optional[str] = None
) -> Message:
    """
    创建用户消息

    Args:
        content: 消息内容（文本或多模态）
        name: 用户名称

    Returns:
        用户消息
    """
    return Message(role="user", content=content, name=name)


def create_assistant_message(
    content: Union[str, List[ContentPart]],
    name: Optional[str] = None,
    tool_calls: Optional[List[ToolCall]] = None
) -> Message:
    """
    创建助手消息

    Args:
        content: 消息内容
        name: 助手名称
        tool_calls: 工具调用列表

    Returns:
        助手消息
    """
    return Message(
        role="assistant",
        content=content,
        name=name,
        tool_calls=tool_calls
    )


def create_system_message(content: str) -> Message:
    """
    创建系统消息

    Args:
        content: 系统提示内容

    Returns:
        系统消息
    """
    return Message(role="system", content=content)


def create_tool_message(
    content: str,
    tool_call_id: str,
    name: str
) -> Message:
    """
    创建工具结果消息

    Args:
        content: 工具执行结果
        tool_call_id: 对应的工具调用 ID
        name: 工具名称

    Returns:
        工具消息
    """
    return Message(
        role="tool",
        content=content,
        tool_call_id=tool_call_id,
        name=name
    )


# ===== 对话树工具函数 =====


def get_message_history(message: Message) -> List[Message]:
    """
    安全提取消息历史（v0.1.9 新增）

    这个函数取代了代码库中所有 hasattr() 检查模式，
    提供统一、安全的 history 提取方式。

    Args:
        message: 要提取历史的消息

    Returns:
        消息历史列表：
        - 如果 message.history 存在且有效：返回 history 的防御性副本
        - 如果 message.history 为 None 或空：返回 [message]

    Raises:
        ValueError: 如果 history 存在但类型无效

    Example:
        >>> msg = create_user_message("Hello").with_history([msg1, msg2])
        >>> history = get_message_history(msg)
        >>> # history 是 [msg1, msg2] 的副本

        >>> msg = create_user_message("Hello")  # 无 history
        >>> history = get_message_history(msg)
        >>> # history 是 [msg]

    Note:
        - 返回防御性副本，防止外部修改
        - v0.1.9 起 history 是正式字段，不再使用 hasattr() 检查
    """
    # v0.1.9 起 history 是正式字段，始终存在（可能为 None）
    if message.history is None:
        return [message]

    # 类型验证
    if not isinstance(message.history, list):
        raise ValueError(
            f"Invalid history type: expected List[Message], "
            f"got {type(message.history).__name__}"
        )

    # 空列表
    if not message.history:
        return [message]

    # 验证所有元素都是 Message
    if not all(isinstance(m, Message) for m in message.history):
        invalid_types = [
            type(m).__name__
            for m in message.history
            if not isinstance(m, Message)
        ]
        raise ValueError(
            f"History contains non-Message objects: {', '.join(set(invalid_types))}"
        )

    # 返回防御性副本
    return message.history.copy()


def build_history_chain(
    base_history: List[Message],
    new_message: Message
) -> List[Message]:
    """
    构建历史链条（不可变追加，v0.1.9 新增）

    将新消息追加到历史链条中，返回新列表（不修改原列表）。

    Args:
        base_history: 基础历史列表
        new_message: 要追加的新消息

    Returns:
        新的历史列表（base_history + [new_message]）

    Example:
        >>> history = [msg1, msg2]
        >>> new_history = build_history_chain(history, msg3)
        >>> # new_history = [msg1, msg2, msg3]
        >>> # history 保持不变（不可变）

    Note:
        这个函数确保历史追加的不可变性，
        符合 Message 的 frozen dataclass 设计。
    """
    return base_history + [new_message]


def trace_message_chain(
    message: Message,
    messages_by_id: Dict[str, Message]
) -> List[Message]:
    """
    追溯消息链（从根到当前）

    Args:
        message: 当前消息
        messages_by_id: 消息 ID 到消息的映射

    Returns:
        消息链（从根到当前消息）
    """
    chain = [message]
    current = message

    while current.parent_id and current.parent_id in messages_by_id:
        current = messages_by_id[current.parent_id]
        chain.insert(0, current)

    return chain


def build_message_tree(messages: List[Message]) -> Dict[str, List[Message]]:
    """
    构建消息树（parent_id -> children 映射）

    Args:
        messages: 消息列表

    Returns:
        parent_id 到子消息列表的映射
    """
    tree: Dict[str, List[Message]] = {}

    for msg in messages:
        parent_id = msg.parent_id or "root"
        if parent_id not in tree:
            tree[parent_id] = []
        tree[parent_id].append(msg)

    return tree


def get_conversation_branches(
    message: Message,
    messages_by_id: Dict[str, Message]
) -> List[List[Message]]:
    """
    获取从当前消息开始的所有对话分支

    Args:
        message: 起始消息
        messages_by_id: 消息 ID 到消息的映射

    Returns:
        所有分支的列表（每个分支是消息列表）
    """
    # 构建子节点映射
    children_map: Dict[str, List[Message]] = {}
    for msg in messages_by_id.values():
        if msg.parent_id:
            if msg.parent_id not in children_map:
                children_map[msg.parent_id] = []
            children_map[msg.parent_id].append(msg)

    # DFS 遍历所有分支
    branches = []

    def dfs(current: Message, path: List[Message]):
        path = path + [current]
        children = children_map.get(current.id, [])

        if not children:
            # 叶子节点，保存分支
            branches.append(path)
        else:
            # 递归遍历子节点
            for child in children:
                dfs(child, path)

    dfs(message, [])
    return branches


# ===== 导出 =====


__all__ = [
    # Content Types
    "ContentType",
    "ContentPart",
    "TextContent",
    "ImageURLContent",
    "ImageFileContent",
    "FileContent",

    # Tool Calls
    "ToolCall",
    "FunctionCall",

    # Message
    "Message",

    # Factory Functions
    "create_user_message",
    "create_assistant_message",
    "create_system_message",
    "create_tool_message",

    # History Utilities (v0.1.9)
    "get_message_history",
    "build_history_chain",

    # Tree Utilities
    "trace_message_chain",
    "build_message_tree",
    "get_conversation_branches",
]
