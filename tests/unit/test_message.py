"""
测试 Message 类（v0.1.9 更新）

验证：
- Message 创建和验证
- 消息回复和追溯
- 序列化和反序列化
- OpenAI 格式转换
- 工具函数
- v0.1.9: history 字段和安全提取函数
"""

import pytest
import time
from loom.core.message import (
    Message,
    create_user_message,
    create_assistant_message,
    create_system_message,
    trace_message_chain,
    get_message_history,
    build_history_chain,
)


class TestMessageCreation:
    """测试 Message 创建"""

    def test_minimal_creation(self):
        """最小参数创建"""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.metadata == {}
        assert isinstance(msg.id, str)
        assert len(msg.id) > 0
        assert isinstance(msg.timestamp, float)
        assert msg.parent_id is None

    def test_full_creation(self):
        """完整参数创建"""
        msg = Message(
            role="assistant",
            content="Hi there!",
            name="bot",
            metadata={"source": "test"},
            id="test-id",
            timestamp=1234567890.0,
            parent_id="parent-id",
        )

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
        assert msg.name == "bot"
        assert msg.metadata == {"source": "test"}
        assert msg.id == "test-id"
        assert msg.timestamp == 1234567890.0
        assert msg.parent_id == "parent-id"

    def test_invalid_role(self):
        """无效角色应该抛出异常"""
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid", content="test")

    def test_invalid_content_type(self):
        """非字符串或列表内容应该抛出异常"""
        with pytest.raises(TypeError, match="Content must be str or List"):
            Message(role="user", content=123)

    def test_valid_roles(self):
        """测试所有有效角色"""
        valid_roles = ["user", "assistant", "system", "tool"]

        for role in valid_roles:
            msg = Message(role=role, content="test")
            assert msg.role == role


class TestMessageReply:
    """测试消息回复"""

    def test_basic_reply(self):
        """基本回复"""
        msg1 = Message(role="user", content="Hello")
        msg2 = msg1.reply("Hi there!")

        assert msg2.role == "assistant"
        assert msg2.content == "Hi there!"
        assert msg2.parent_id == msg1.id
        assert msg2.name is None

    def test_reply_with_name(self):
        """带名称的回复"""
        msg1 = Message(role="user", content="Hello")
        msg2 = msg1.reply("Hi!", name="bot")

        assert msg2.name == "bot"
        assert msg2.parent_id == msg1.id

    def test_reply_with_custom_role(self):
        """自定义角色的回复"""
        msg1 = Message(role="user", content="Hello")
        msg2 = msg1.reply("System message", role="system")

        assert msg2.role == "system"
        assert msg2.parent_id == msg1.id

    def test_reply_chain(self):
        """回复链"""
        msg1 = Message(role="user", content="First")
        msg2 = msg1.reply("Second")
        msg3 = msg2.reply("Third")

        assert msg3.parent_id == msg2.id
        assert msg2.parent_id == msg1.id
        assert msg1.parent_id is None


class TestMessageSerialization:
    """测试序列化和反序列化"""

    def test_to_dict(self):
        """测试 to_dict()"""
        msg = Message(
            role="user",
            content="Hello",
            name="alice",
            metadata={"key": "value"},
        )

        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["name"] == "alice"
        assert data["metadata"] == {"key": "value"}
        assert "id" in data
        assert "timestamp" in data
        assert "parent_id" in data

    def test_from_dict(self):
        """测试 from_dict()"""
        data = {
            "role": "assistant",
            "content": "Hi",
            "name": "bot",
            "id": "test-id",
            "timestamp": 1234567890.0,
            "parent_id": "parent-id",
            "metadata": {"key": "value"},
        }

        msg = Message.from_dict(data)

        assert msg.role == "assistant"
        assert msg.content == "Hi"
        assert msg.name == "bot"
        assert msg.id == "test-id"
        assert msg.timestamp == 1234567890.0
        assert msg.parent_id == "parent-id"
        assert msg.metadata == {"key": "value"}

    def test_round_trip(self):
        """测试序列化往返"""
        msg1 = Message(
            role="user",
            content="Test message",
            name="tester",
            metadata={"test": True},
        )

        data = msg1.to_dict()
        msg2 = Message.from_dict(data)

        assert msg1.role == msg2.role
        assert msg1.content == msg2.content
        assert msg1.name == msg2.name
        assert msg1.id == msg2.id
        assert msg1.timestamp == msg2.timestamp
        assert msg1.parent_id == msg2.parent_id
        assert msg1.metadata == msg2.metadata


class TestOpenAIFormat:
    """测试 OpenAI 格式转换"""

    def test_basic_format(self):
        """基本格式"""
        msg = Message(role="user", content="Hello")
        openai_msg = msg.to_openai_format()

        assert openai_msg == {"role": "user", "content": "Hello"}

    def test_format_with_name(self):
        """带名称的格式"""
        msg = Message(role="assistant", content="Hi", name="bot")
        openai_msg = msg.to_openai_format()

        assert openai_msg == {
            "role": "assistant",
            "content": "Hi",
            "name": "bot",
        }

    def test_format_excludes_metadata(self):
        """格式不包含元数据"""
        msg = Message(
            role="user",
            content="Hello",
            metadata={"should": "not appear"},
        )
        openai_msg = msg.to_openai_format()

        assert "metadata" not in openai_msg
        assert "id" not in openai_msg
        assert "timestamp" not in openai_msg


class TestStringRepresentation:
    """测试字符串表示"""

    def test_str(self):
        """测试 __str__()"""
        msg = Message(role="user", content="Short message")
        s = str(msg)

        assert "Message[user]" in s
        assert "Short message" in s

    def test_str_with_name(self):
        """带名称的字符串表示"""
        msg = Message(role="assistant", content="Test", name="bot")
        s = str(msg)

        assert "assistant" in s
        assert "bot" in s

    def test_str_truncates_long_content(self):
        """长内容应该被截断"""
        long_content = "a" * 100
        msg = Message(role="user", content=long_content)
        s = str(msg)

        assert len(s) < len(long_content) + 50
        assert "..." in s

    def test_repr(self):
        """测试 __repr__()"""
        msg = Message(role="user", content="Test message")
        r = repr(msg)

        assert "Message(" in r
        assert "role=" in r
        assert "user" in r


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_user_message(self):
        """测试 create_user_message()"""
        msg = create_user_message("Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_create_user_message_with_name(self):
        """带名称创建用户消息"""
        msg = create_user_message("Hello", name="alice")

        assert msg.role == "user"
        assert msg.name == "alice"

    def test_create_assistant_message(self):
        """测试 create_assistant_message()"""
        msg = create_assistant_message("Hi there!")

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_create_assistant_message_with_name(self):
        """带名称创建助手消息"""
        msg = create_assistant_message("Hi", name="bot")

        assert msg.role == "assistant"
        assert msg.name == "bot"

    def test_create_system_message(self):
        """测试 create_system_message()"""
        msg = create_system_message("You are helpful")

        assert msg.role == "system"
        assert msg.content == "You are helpful"


class TestMessageTracing:
    """测试消息追溯"""

    def test_trace_single_message(self):
        """单个消息的追溯"""
        msg = Message(role="user", content="Hello")
        messages = {msg.id: msg}

        chain = trace_message_chain(msg, messages)

        assert len(chain) == 1
        assert chain[0] == msg

    def test_trace_chain(self):
        """追溯消息链"""
        msg1 = Message(role="user", content="First")
        msg2 = msg1.reply("Second")
        msg3 = msg2.reply("Third")

        messages = {msg1.id: msg1, msg2.id: msg2, msg3.id: msg3}

        chain = trace_message_chain(msg3, messages)

        assert len(chain) == 3
        assert chain[0] == msg1
        assert chain[1] == msg2
        assert chain[2] == msg3

    def test_trace_missing_parent(self):
        """缺少父消息时停止追溯"""
        msg1 = Message(role="user", content="First")
        msg2 = msg1.reply("Second")
        msg3 = msg2.reply("Third")

        # 只包含 msg2 和 msg3
        messages = {msg2.id: msg2, msg3.id: msg3}

        chain = trace_message_chain(msg3, messages)

        assert len(chain) == 2
        assert chain[0] == msg2
        assert chain[1] == msg3


class TestMessageImmutability:
    """测试消息不可变性"""

    def test_cannot_modify_fields(self):
        """不能修改字段（dataclass frozen=True）"""
        msg = Message(role="user", content="Hello")

        with pytest.raises(Exception):  # FrozenInstanceError
            msg.content = "Modified"

        with pytest.raises(Exception):
            msg.role = "assistant"

    def test_metadata_is_mutable(self):
        """元数据字典本身是可变的（但不推荐修改）"""
        msg = Message(role="user", content="Hello", metadata={"key": "value"})

        # 技术上可以修改（但违反不可变性原则）
        msg.metadata["new_key"] = "new_value"
        assert msg.metadata["new_key"] == "new_value"


# ===== v0.1.9 New Tests =====


class TestMessageHistoryField:
    """测试 v0.1.9 history 字段功能"""

    def test_history_field_declaration(self):
        """history 应该是正式的 dataclass 字段"""
        msg = Message(role="user", content="Hello")

        # history 字段存在且默认为 None
        assert hasattr(msg, "history")
        assert msg.history is None

    def test_history_with_constructor(self):
        """通过构造函数传递 history"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")

        msg3 = Message(
            role="user",
            content="Third",
            history=[msg1, msg2]
        )

        assert msg3.history is not None
        assert len(msg3.history) == 2
        assert msg3.history[0] == msg1
        assert msg3.history[1] == msg2

    def test_with_history_immutable_update(self):
        """with_history() 应该返回新实例而非修改原实例"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")

        history = [msg1]
        msg_with_history = msg2.with_history(history)

        # 返回新实例
        assert msg_with_history is not msg2
        assert msg_with_history.content == msg2.content
        assert msg_with_history.history == history

        # 原实例未修改
        assert msg2.history is None

    def test_with_history_empty_list(self):
        """with_history() 接受空列表"""
        msg = Message(role="user", content="Test")
        msg_with_history = msg.with_history([])

        assert msg_with_history.history == []


class TestGetMessageHistory:
    """测试 v0.1.9 get_message_history() 安全提取函数"""

    def test_get_history_none(self):
        """history 为 None 时返回只包含自己的列表"""
        msg = Message(role="user", content="Hello")

        history = get_message_history(msg)

        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0] == msg

    def test_get_history_with_history(self):
        """history 存在时返回完整历史"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")
        msg3 = Message(role="user", content="Third", history=[msg1, msg2])

        history = get_message_history(msg3)

        assert len(history) == 2
        assert history[0] == msg1
        assert history[1] == msg2

    def test_get_history_defensive_copy(self):
        """返回的历史应该是防御性复制"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second", history=[msg1])

        history = get_message_history(msg2)

        # 修改返回的列表不应影响原消息
        history.append(Message(role="user", content="Extra"))

        # 再次获取应该仍是原始的
        history2 = get_message_history(msg2)
        assert len(history2) == 1
        assert history2[0] == msg1

    def test_get_history_type_validation(self):
        """应该验证 history 是列表类型"""
        msg = Message(role="user", content="Test")

        # 手动设置非法类型（绕过构造函数）
        object.__setattr__(msg, "history", "invalid")

        with pytest.raises(ValueError, match="Invalid history type"):
            get_message_history(msg)

    def test_get_history_element_validation(self):
        """应该验证 history 中所有元素都是 Message"""
        msg1 = Message(role="user", content="Valid")
        msg = Message(role="assistant", content="Test", history=[msg1, "invalid"])

        with pytest.raises(ValueError, match="non-Message objects"):
            get_message_history(msg)


class TestBuildHistoryChain:
    """测试 v0.1.9 build_history_chain() 不可变链条构建"""

    def test_build_empty_chain(self):
        """从空历史开始构建"""
        msg = Message(role="user", content="New")

        chain = build_history_chain([], msg)

        assert len(chain) == 1
        assert chain[0] == msg

    def test_build_chain_append(self):
        """追加到现有历史"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")
        msg3 = Message(role="user", content="Third")

        base = [msg1, msg2]
        chain = build_history_chain(base, msg3)

        assert len(chain) == 3
        assert chain[0] == msg1
        assert chain[1] == msg2
        assert chain[2] == msg3

    def test_build_chain_immutable(self):
        """构建链条不应修改原列表"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")

        base = [msg1]
        chain = build_history_chain(base, msg2)

        # 原列表未修改
        assert len(base) == 1
        assert base[0] == msg1

        # 新链条包含两个消息
        assert len(chain) == 2
        assert chain[0] == msg1
        assert chain[1] == msg2


class TestHistorySerialization:
    """测试 v0.1.9 history 序列化/反序列化"""

    def test_to_dict_with_history(self):
        """to_dict() 应该序列化 history"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")
        msg3 = Message(role="user", content="Third", history=[msg1, msg2])

        data = msg3.to_dict(include_history=True)

        assert "history" in data
        assert isinstance(data["history"], list)
        assert len(data["history"]) == 2
        assert data["history"][0]["content"] == "First"
        assert data["history"][1]["content"] == "Second"

    def test_to_dict_without_history(self):
        """to_dict(include_history=False) 不应序列化 history"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second", history=[msg1])

        data = msg2.to_dict(include_history=False)

        assert "history" not in data

    def test_to_dict_no_recursive_history(self):
        """history 序列化只保留一层，不递归"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second", history=[msg1])
        msg3 = Message(role="user", content="Third", history=[msg1, msg2])

        data = msg3.to_dict(include_history=True)

        # msg3 的 history 包含 msg1 和 msg2
        assert len(data["history"]) == 2

        # 但 msg2 的 history 不应再包含嵌套的 history
        assert "history" not in data["history"][1]

    def test_from_dict_with_history(self):
        """from_dict() 应该恢复 history"""
        data = {
            "role": "user",
            "content": "Third",
            "id": "msg3",
            "timestamp": 1234567890.0,
            "history": [
                {
                    "role": "user",
                    "content": "First",
                    "id": "msg1",
                    "timestamp": 1234567880.0,
                },
                {
                    "role": "assistant",
                    "content": "Second",
                    "id": "msg2",
                    "timestamp": 1234567885.0,
                },
            ],
        }

        msg = Message.from_dict(data)

        assert msg.content == "Third"
        assert msg.history is not None
        assert len(msg.history) == 2
        assert msg.history[0].content == "First"
        assert msg.history[1].content == "Second"

    def test_from_dict_without_history(self):
        """from_dict() 处理没有 history 的数据"""
        data = {
            "role": "user",
            "content": "Test",
            "id": "msg1",
            "timestamp": 1234567890.0,
        }

        msg = Message.from_dict(data)

        assert msg.content == "Test"
        assert msg.history is None

    def test_history_serialization_round_trip(self):
        """history 序列化往返应保持一致"""
        msg1 = Message(role="user", content="First")
        msg2 = Message(role="assistant", content="Second")
        msg3 = Message(role="user", content="Third", history=[msg1, msg2])

        # 序列化
        data = msg3.to_dict(include_history=True)

        # 反序列化
        restored = Message.from_dict(data)

        # 验证
        assert restored.content == msg3.content
        assert len(restored.history) == 2
        assert restored.history[0].content == msg1.content
        assert restored.history[1].content == msg2.content
