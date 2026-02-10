"""
11_streaming_output.py - 分形流式输出

演示：
- FractalStreamAPI 分形流式观测
- 多层级节点事件监听
- OutputStrategy 输出策略
- 节点路径追踪
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.events import EventBus
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.api.stream_api import FractalStreamAPI, OutputStrategy
from loom.runtime import Task

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


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

    # 2. 创建根 EventBus
    root_bus = EventBus()

    # 3. 创建 FractalStreamAPI
    stream_api = FractalStreamAPI(root_bus)

    # 4. 注册节点层级关系（3层结构）
    stream_api.register_node("root-agent", parent_node_id=None)
    stream_api.register_node("coordinator", parent_node_id="root-agent")
    stream_api.register_node("worker-1", parent_node_id="coordinator")
    stream_api.register_node("worker-2", parent_node_id="coordinator")
    stream_api.register_node("sub-worker-1", parent_node_id="worker-1")

    print("=== 分形流式输出演示 ===\n")
    print("节点层级结构:")
    print("  root-agent (depth=0)")
    print("    └── coordinator (depth=1)")
    print("        ├── worker-1 (depth=2)")
    print("        │   └── sub-worker-1 (depth=3)")
    print("        └── worker-2 (depth=2)")
    print()
    print(f"节点路径示例: {stream_api.get_node_path('sub-worker-1')}")
    print(f"节点深度: {stream_api.get_node_depth('sub-worker-1')}\n")

    # 5. 创建流式事件消费者（后台任务）
    events_received = []

    async def consume_stream():
        """消费流式事件"""
        try:
            async for sse_event in stream_api.stream_all_events(OutputStrategy.TREE):
                events_received.append(sse_event)
                # 解析并显示事件
                if "node.thinking" in sse_event:
                    print(f"  📡 收到思考事件")
                elif "node.tool_call" in sse_event:
                    print(f"  📡 收到工具调用事件")
                elif "node.tool_result" in sse_event:
                    print(f"  📡 收到工具结果事件")
        except asyncio.CancelledError:
            pass

    # 启动流式消费者
    consumer_task = asyncio.create_task(consume_stream())
    await asyncio.sleep(0.1)  # 等待消费者启动

    # 6. 创建多层级 Agent 并执行
    print("--- 创建多层级 Agent ---\n")

    # 创建子级 EventBus（事件会冒泡到 root_bus）
    coordinator_bus = root_bus.create_child_bus("coordinator")
    worker1_bus = coordinator_bus.create_child_bus("worker-1")
    worker2_bus = coordinator_bus.create_child_bus("worker-2")
    sub_worker1_bus = worker1_bus.create_child_bus("sub-worker-1")

    # 创建 Worker Agents（不同层级）
    worker1 = Agent.create(
        llm=llm,
        node_id="worker-1",
        event_bus=worker1_bus,
        system_prompt="你是翻译专家，将中文翻译成英文。",
        max_iterations=2,
    )

    worker2 = Agent.create(
        llm=llm,
        node_id="worker-2",
        event_bus=worker2_bus,
        system_prompt="你是摘要专家，用一句话总结内容。",
        max_iterations=2,
    )

    sub_worker1 = Agent.create(
        llm=llm,
        node_id="sub-worker-1",
        event_bus=sub_worker1_bus,
        system_prompt="你是润色专家，优化文本表达。",
        max_iterations=2,
    )

    # 7. 并行执行任务
    print("--- 并行执行任务 ---\n")

    results = await asyncio.gather(
        worker1.run("翻译：人工智能正在改变世界"),
        worker2.run("总结：Python是一种简单易学的编程语言"),
        sub_worker1.run("润色：AI很好用"),
    )

    print(f"\n[Worker-1 depth=2] {results[0][:50]}...")
    print(f"[Worker-2 depth=2] {results[1][:50]}...")
    print(f"[Sub-Worker-1 depth=3] {results[2][:50]}...")

    # 8. 停止流式消费者
    consumer_task.cancel()
    await asyncio.sleep(0.1)

    # 9. 显示统计
    print(f"\n--- 流式统计 ---")
    print(f"共收到 {len(events_received)} 个SSE事件")
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
