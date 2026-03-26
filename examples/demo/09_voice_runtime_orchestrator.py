"""Demo 09: 语音优先运行时编排器

展示 Loom 作为单 Agent 语音运行时的核心能力：
- 低延迟语音回合响应
- 强约束的上下文编排（按预算取上下文）
- 用户级记忆恢复
- Skill 渐进式加载与动态替换
- Skill 持有工具机制
- 配置驱动的能力组装
"""

import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel

from loom.agent import Agent
from loom.config import AgentConfig
from loom.providers.openai import OpenAIProvider
from loom.types import ToolDefinition, ToolContext, MemoryEntry, UserMessage, Skill
from loom.tools.schema import PydanticSchema


# === 1. Tool 层：确定性执行能力 ===

class SearchParams(BaseModel):
    query: str

async def search_knowledge(params: SearchParams, ctx: ToolContext) -> str:
    """模拟知识库检索"""
    return f"知识库结果：关于 '{params.query}' 的最佳实践文档"

search_tool = ToolDefinition(
    name="search_knowledge",
    description="检索知识库",
    parameters=PydanticSchema(SearchParams),
    execute=search_knowledge
)


class PythonParams(BaseModel):
    code: str

async def run_python(params: PythonParams, ctx: ToolContext) -> str:
    """模拟 Python 沙箱"""
    return f"执行结果: {params.code} -> OK"

python_tool = ToolDefinition(
    name="run_python",
    description="执行 Python 代码",
    parameters=PydanticSchema(PythonParams),
    execute=run_python
)


# === 2. Skill 层：任务语义封装 + 工具持有 ===

def create_mock_skills() -> list[Skill]:
    """创建模拟 skills（Layer 1 元数据 + 工具持有）"""
    return [
        Skill(
            name="python-expert",
            description="Python 编程专家",
            instructions="回答 Python 问题时给出代码示例和最佳实践",
            tools=["run_python"],  # Skill 持有工具
            _instructions_loaded=False,
        ),
        Skill(
            name="code-reviewer",
            description="代码审查专家",
            instructions="审查代码质量，检查命名、类型注解、错误处理",
            tools=["search_knowledge"],  # Skill 持有工具
            _instructions_loaded=False,
        ),
        Skill(
            name="translator",
            description="翻译专家",
            instructions="翻译文本到不同语言",
            _instructions_loaded=False,
        ),
    ]


# === 3. 配置驱动的 Agent 组装 ===

async def main():
    load_dotenv()

    # Agent 配置：人格、系统提示词、能力开关
    config = AgentConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        max_steps=5,
        stream=True  # 语音链路需要流式输出
    )

    provider = OpenAIProvider(config)
    agent = Agent(provider=provider, config=config)

    # 注册工具（Tool 层）
    agent.tools.register(search_tool)
    agent.tools.register(python_tool)

    # 注册 Skills（Layer 1 元数据发现）
    skills = create_mock_skills()
    for skill in skills:
        agent.skill_mgr.registry.register(skill)

    print("=" * 60)
    print("语音优先运行时编排器（完整版）")
    print("=" * 60)

    # === 3. Memory 层：用户偏好 + 近期对话 + 长期事实 ===
    print("\n[1] 用户级记忆恢复")

    # 模拟用户偏好恢复
    await agent.memory.add_message(UserMessage(content="我喜欢简洁的回答"))

    # 存储长期事实到 L2
    fact = MemoryEntry(
        content="用户是 Python 开发者，关注性能优化",
        tokens=15,
        importance=0.9
    )
    await agent.memory.l2.store(fact)

    print(f"✓ L1 对话历史: {len(agent.memory.get_history())} 条")
    print("✓ L2 长期事实已恢复")

    # === 4. 强约束的上下文编排（按预算取上下文）===
    print("\n[2] 上下文预算控制")

    # 设置分区预算
    agent.partition_mgr.partitions["system"].budget = 1000
    agent.partition_mgr.partitions["working"].budget = 2000
    agent.partition_mgr.partitions["memory"].budget = 3000
    agent.partition_mgr.partitions["history"].budget = 5000

    print(f"✓ System 预算: 1000 tokens")
    print(f"✓ Working 预算: 2000 tokens")
    print(f"✓ Memory 预算: 3000 tokens")
    print(f"✓ History 预算: 5000 tokens")

    # === 5. Skill 渐进式加载与动态替换 ===
    print("\n[3] Skill 渐进式加载与动态替换")

    # Layer 1: 显示所有可用 skills
    print(f"✓ Layer 1 发现: {len(skills)} 个 skills")
    for skill in skills:
        tools_info = f" (工具: {skill.tools})" if skill.tools else ""
        print(f"  - {skill.name}: {skill.description}{tools_info}")

    # Layer 2: 根据第一轮对话激活相关 skill
    print("\n✓ Layer 2 激活 (第一轮对话):")
    agent.skill_mgr.activate("python-expert", budget=2000)
    print(f"  激活 python-expert (持有工具: run_python)")
    print(f"  当前激活: {len(agent.skill_mgr.registry.list_active())} 个")

    # === 6. 低延迟语音回合响应 ===
    print("\n[4] 第一轮语音回合（ASR -> Agent Stream -> TTS）")
    print("-" * 60)

    # 模拟 ASR final 输入
    user_voice_input = "帮我查一下 Python 性能优化的最佳实践"

    # Agent 流式响应（语音链路主路径）
    result = await agent.run(user_voice_input)

    print("-" * 60)
    print(f"\nAgent 响应:\n{result.content}")
    print(f"步数: {result.steps} | Tokens: {agent.resource_guard._used_tokens}")

    # === 7. 动态替换 Skill（第二轮对话）===
    print("\n[5] 第二轮对话 - 动态替换 Skill")

    # 卸载旧 skill
    agent.skill_mgr.deactivate("python-expert")
    print("✓ 卸载 python-expert")

    # 激活新 skill
    agent.skill_mgr.activate("translator", budget=2000)
    print("✓ 激活 translator")
    print(f"✓ 当前激活: {len(agent.skill_mgr.registry.list_active())} 个")

    # === 总结 ===
    print("\n" + "=" * 60)
    print("语音运行时编排器核心能力:")
    print("✓ 低延迟流式响应（语音主链路）")
    print("✓ 按预算编排上下文（5 分区独立预算）")
    print("✓ 用户级记忆恢复（L1+L2）")
    print("✓ Skill 渐进式加载（Layer 1 发现 + Layer 2 激活）")
    print("✓ Skill 动态替换（每轮对话重新选择）")
    print("✓ Skill 持有工具（工具与 Skill 生命周期绑定）")
    print("✓ 配置驱动能力组装（Tool 层确定性执行）")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

