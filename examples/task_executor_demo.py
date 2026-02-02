"""
任务执行器 Demo - 复杂问题分析与解决方案生成

特性：
- 基于复杂问题的深度分析
- 生成系列解决方案
- 产出可执行代码
- 任务分解和执行追踪

运行：
  OPENAI_API_KEY=... python examples/task_executor_demo.py

示例任务：
  - 设计一个用户认证系统
  - 实现一个简单的任务队列
  - 优化数据库查询性能
"""

import asyncio
import os
from typing import Any

from loom.agent import Agent
from loom.events import EventBus
from loom.protocol import Task
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.llm.openai import OpenAIProvider

# ==================== 技术知识库 ====================


class TechnicalKnowledgeBase(KnowledgeBaseProvider):
    """
    技术知识库 - 用于任务执行的技术参考
    """

    def __init__(self):
        self.knowledge_data = [
            {
                "id": "kb_auth_001",
                "content": "用户认证系统通常包括：用户注册、登录、密码加密（bcrypt/argon2）、"
                "会话管理（JWT/Session）、权限控制（RBAC）。"
                "安全要点：密码哈希、HTTPS传输、防暴力破解、双因素认证。",
                "source": "认证系统设计指南",
                "tags": ["auth", "security", "jwt", "session"],
            },
            {
                "id": "kb_queue_001",
                "content": "任务队列系统核心组件：生产者、消费者、队列存储（Redis/RabbitMQ）、"
                "任务调度器。实现要点：任务持久化、失败重试、优先级队列、并发控制。",
                "source": "任务队列架构",
                "tags": ["queue", "redis", "rabbitmq", "async"],
            },
            {
                "id": "kb_db_001",
                "content": "数据库优化策略：索引优化（B-tree/Hash）、查询优化（EXPLAIN分析）、"
                "连接池管理、缓存策略（Redis）、分库分表、读写分离。",
                "source": "数据库性能优化",
                "tags": ["database", "optimization", "index", "cache"],
            },
        ]

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        """查询技术知识"""
        query_lower = query.lower()
        results = []

        for item in self.knowledge_data:
            content_lower = item["content"].lower()
            tags_lower = [tag.lower() for tag in item["tags"]]

            relevance = 0.0
            if query_lower in content_lower:
                relevance = 0.95
            elif any(query_lower in tag for tag in tags_lower):
                relevance = 0.85
            elif any(word in content_lower for word in query_lower.split()):
                relevance = 0.75

            if relevance > 0:
                results.append(
                    KnowledgeItem(
                        id=item["id"],
                        content=item["content"],
                        source=item["source"],
                        relevance=relevance,
                        metadata={"tags": item["tags"]},
                    )
                )

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]


# ==================== 工具定义 ====================


def create_code_generator_tool():
    """创建代码生成工具"""
    return {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "生成指定语言的代码实现",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "编程语言（如 python, javascript, go）",
                    },
                    "description": {
                        "type": "string",
                        "description": "代码功能描述",
                    },
                },
                "required": ["language", "description"],
            },
        },
    }


def create_architecture_tool():
    """创建架构设计工具"""
    return {
        "type": "function",
        "function": {
            "name": "design_architecture",
            "description": "设计系统架构，包括组件、接口、数据流",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_type": {
                        "type": "string",
                        "description": "系统类型（如 web_api, microservice, data_pipeline）",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "系统需求描述",
                    },
                },
                "required": ["system_type", "requirements"],
            },
        },
    }


# ==================== 任务观察器 ====================


class TaskObserver:
    """任务执行观察器 - 追踪任务分解和执行"""

    def __init__(self):
        self.steps = []
        self.solutions = []
        self.code_blocks = []

    async def on_event(self, task: Task) -> Task:
        """处理事件"""
        action = task.action

        if action == "node.planning":
            # 任务规划
            plan = task.parameters.get("plan", {})
            print("\n📋 任务规划:")
            print(f"  步骤数: {len(plan.get('steps', []))}")

        elif action == "node.tool_call":
            # 工具调用
            tool_name = task.parameters.get("tool_name", "")
            if "code" in tool_name.lower():
                print("\n💻 生成代码...")

        return task


# ==================== 任务执行函数 ====================


async def execute_task(agent: Any, task_description: str, observer: TaskObserver):
    """执行任务并展示结果"""
    print(f"\n{'='*60}")
    print(f"📝 任务: {task_description}")
    print(f"{'='*60}")

    # 创建任务
    task = Task(
        task_id=f"task-{len(observer.steps)}",
        action="execute",
        parameters={"content": task_description},
    )

    print("\n🔄 开始执行...")

    try:
        result = await agent.execute_task(task)

        print("\n\n✅ 任务完成")
        print(f"\n{'='*60}")
        print("📊 执行结果:")
        print(f"{'='*60}")

        # 展示结果
        if isinstance(result.result, dict):
            for key, value in result.result.items():
                print(f"\n{key}:")
                print(f"{value}")
        else:
            print(result.result)

    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")


# ==================== 主函数 ====================


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("任务执行器 Demo")
    print("=" * 60)

    # 1. 配置LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    print("✓ LLM已配置")

    # 2. 配置知识库
    knowledge_base = TechnicalKnowledgeBase()
    print(f"✓ 知识库已配置 ({len(knowledge_base.knowledge_data)} 条技术知识)")

    # 3. 创建EventBus和观察器
    event_bus = EventBus()
    observer = TaskObserver()
    event_bus.register_handler("*", observer.on_event)
    print("✓ 事件观察器已配置")

    # 4. 创建工具
    tools = [
        create_code_generator_tool(),
        create_architecture_tool(),
    ]
    print(f"✓ 工具已配置 ({len(tools)} 个工具)")

    # 5. 使用新的简化API创建Agent
    agent = Agent.create(
        llm,
        system_prompt="""你是一个专业的任务执行器。

你的职责：
- 分析复杂问题
- 制定解决方案
- 生成可执行代码
- 提供详细的实现步骤

请基于技术知识库，产出高质量的解决方案和代码。""",
        tools=tools,
        event_bus=event_bus,
        knowledge_base=knowledge_base,
        knowledge_max_items=3,
        knowledge_relevance_threshold=0.75,
    )
    print(f"✓ Agent已创建: {agent.node_id}")

    # 7. 执行示例任务
    print("\n" + "=" * 60)
    print("开始执行示例任务")
    print("=" * 60)

    # 示例任务1：设计认证系统
    await execute_task(agent, "设计一个简单的用户认证系统，包括注册、登录和JWT token管理", observer)

    # 可以添加更多任务
    # await execute_task(agent, "实现一个基于Redis的任务队列", observer)


if __name__ == "__main__":
    asyncio.run(main())
