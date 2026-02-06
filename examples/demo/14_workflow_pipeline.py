"""
14_workflow_pipeline.py - 工作流管道

演示：
- 顺序执行的工作流管道
- 步骤间数据传递
- EventBus 事件监听（显示内部循环）
- ResultSynthesizer 结果合成
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.events import EventBus
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.fractal import ResultSynthesizer
from loom.protocol import Task

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class WorkflowPipeline:
    """简单的工作流管道"""

    def __init__(self, llm, event_bus: EventBus):
        self.llm = llm
        self.event_bus = event_bus
        self.steps = []
        self.results = []

    def add_step(self, name: str, system_prompt: str):
        """添加管道步骤"""
        self.steps.append({"name": name, "system_prompt": system_prompt})
        return self

    async def execute(self, initial_input: str) -> list[dict]:
        """执行管道"""
        current_input = initial_input
        self.results = []

        for i, step in enumerate(self.steps):
            print(f"\n[Step {i+1}] {step['name']}...")

            agent = Agent.create(
                llm=self.llm,
                node_id=f"pipeline-step-{i}",
                system_prompt=step["system_prompt"],
                event_bus=self.event_bus,
                max_iterations=3,
            )

            result = await agent.run(current_input)
            self.results.append({
                "step": step["name"],
                "result": result,
                "success": True,
            })

            # 下一步的输入是当前步骤的输出
            current_input = result
            print(f"    [完成] {result[:60]}...")

        return self.results


async def main():
    # 1. 创建 LLM Provider
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 2. 创建 EventBus 并注册事件处理器（显示内部循环）
    event_bus = EventBus()

    async def on_thinking(task: Task) -> Task:
        """监听思考过程"""
        content = task.parameters.get("content", "")[:80]
        node_id = task.parameters.get("node_id", "")
        print(f"    💭 [{node_id}] 思考: {content}...")
        return task

    async def on_tool_call(task: Task) -> Task:
        """监听工具调用"""
        tool_name = task.parameters.get("tool_name", "")
        tool_args = task.parameters.get("tool_args", {})
        node_id = task.parameters.get("node_id", "")
        print(f"    🔧 [{node_id}] 调用工具: {tool_name}({tool_args})")
        return task

    async def on_tool_result(task: Task) -> Task:
        """监听工具结果"""
        tool_name = task.parameters.get("tool_name", "")
        result = str(task.parameters.get("result", ""))[:60]
        node_id = task.parameters.get("node_id", "")
        print(f"    ✅ [{node_id}] 工具结果: {tool_name} -> {result}...")
        return task

    # 注册事件处理器
    event_bus.register_handler("node.thinking", on_thinking)
    event_bus.register_handler("node.tool_call", on_tool_call)
    event_bus.register_handler("node.tool_result", on_tool_result)

    print("=== 工作流管道演示 ===")
    print("场景：内容创作管道（构思 -> 大纲 -> 摘要）\n")

    # 3. 创建工作流管道
    pipeline = WorkflowPipeline(llm, event_bus)
    pipeline.add_step(
        name="构思",
        system_prompt="你是创意专家。根据主题生成3个创意点子，每个一句话。"
    ).add_step(
        name="大纲",
        system_prompt="你是内容规划师。根据创意点子，选择最好的一个，生成简短大纲（3个要点）。"
    ).add_step(
        name="摘要",
        system_prompt="你是文案专家。根据大纲，写一段50字以内的精炼摘要。"
    )

    # 4. 执行管道
    initial_topic = "人工智能在教育领域的应用"
    print(f"初始输入: {initial_topic}")

    results = await pipeline.execute(initial_topic)

    # 5. 使用 ResultSynthesizer 合成结果
    print("\n--- 结果合成 ---")
    synthesizer = ResultSynthesizer()

    # 结构化合成
    structured = await synthesizer.synthesize(
        task=f"关于'{initial_topic}'的内容创作",
        subtask_results=results,
        strategy="structured",
    )
    print(f"\n结构化输出:\n{structured}")

    # LLM 智能合成
    print("\n--- LLM 智能合成 ---")
    llm_synthesis = await synthesizer.synthesize(
        task=f"关于'{initial_topic}'的内容创作",
        subtask_results=results,
        strategy="llm",
        provider=llm,
    )
    print(f"\n智能合成结果:\n{llm_synthesis}")


if __name__ == "__main__":
    asyncio.run(main())
