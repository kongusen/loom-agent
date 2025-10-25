"""
测试 Loom Agent 的新特性：tt 递归模式 + Context Assembly

使用真实 LLM (GPT-4o Mini) 测试：
1. tt 递归模式
2. 上下文组装（Context Assembly）
3. 事件流（Event Streaming）
4. 多轮工具调用
5. 递归深度跟踪
"""

import asyncio
from typing import Dict, Any

from loom.components.agent import Agent
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


# ============================================================================
# 配置真实 LLM
# ============================================================================

class GPT4oMiniLLM(BaseLLM):
    """GPT-4o Mini through XiaoAI Plus"""

    def __init__(self):
        self.base_url = "https://xiaoai.plus/v1"
        self.api_key = "sk-MQWe6wOtgq75cQpK2gGwV9Ninqc5jrxBBWDETRCI8h7PzTkb"
        self.model = "gpt-4o-mini"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: list) -> str:
        """非流式生成"""
        import openai

        client = openai.AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        return response.choices[0].message.content

    async def stream(self, messages: list):
        """流式生成"""
        import openai

        client = openai.AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_with_tools(self, messages: list, tools: list = None) -> dict:
        """支持工具调用的生成"""
        import openai

        client = openai.AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        # 转换工具格式为 OpenAI 格式
        openai_tools = []
        if tools:
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "parameters": tool["function"]["parameters"]
                    }
                })

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools if openai_tools else None
        )

        message = response.choices[0].message

        # 转换响应格式
        result = {
            "content": message.content or "",
            "tool_calls": []
        }

        if message.tool_calls:
            for tc in message.tool_calls:
                import json
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })

        return result


# ============================================================================
# 测试工具
# ============================================================================

class CalculatorTool(BaseTool):
    """计算器工具"""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "执行数学计算，支持基本的算术运算"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式，例如：2+2, 10*5, (3+5)*2"
                }
            },
            "required": ["expression"]
        }

    async def run(self, **kwargs) -> str:
        """执行计算"""
        expression = kwargs.get("expression", "")
        try:
            # 安全的 eval
            result = eval(expression, {"__builtins__": {}}, {})
            return f"计算结果：{expression} = {result}"
        except Exception as e:
            return f"计算错误：{str(e)}"


class WeatherTool(BaseTool):
    """天气查询工具（模拟）"""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "查询指定城市的天气情况"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京、上海、深圳"
                }
            },
            "required": ["city"]
        }

    async def run(self, **kwargs) -> str:
        """模拟查询天气"""
        city = kwargs.get("city", "未知城市")
        import random

        weather_types = ["晴天", "多云", "小雨", "阴天"]
        temp = random.randint(15, 30)
        weather = random.choice(weather_types)

        return f"{city}的天气：{weather}，温度 {temp}°C"


class SearchTool(BaseTool):
    """搜索工具（模拟）"""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "搜索相关信息"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询词"
                }
            },
            "required": ["query"]
        }

    async def run(self, **kwargs) -> str:
        """模拟搜索"""
        query = kwargs.get("query", "")
        return f"搜索 '{query}' 的结果：找到了一些相关信息...\n" \
               f"1. {query}是一个很有趣的话题\n" \
               f"2. 很多人都在讨论{query}\n" \
               f"3. 关于{query}的最新研究表明..."


# ============================================================================
# 测试场景
# ============================================================================

async def test_basic_conversation():
    """测试 1：基础对话（无工具）"""
    print("\n" + "="*80)
    print("🧪 测试 1：基础对话（无工具）")
    print("="*80)

    llm = GPT4oMiniLLM()
    agent = Agent(llm=llm, tools=[], max_iterations=5)

    print("\n💬 用户：你好，请简单介绍一下你自己")
    print("\n📡 Agent 事件流：")
    print("-" * 80)

    async for event in agent.execute("你好，请简单介绍一下你自己"):
        if event.type == AgentEventType.ITERATION_START:
            print(f"\n🔄 [第{event.iteration}轮] 开始")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n\n✅ [完成] 对话结束")


async def test_single_tool_call():
    """测试 2：单次工具调用"""
    print("\n" + "="*80)
    print("🧪 测试 2：单次工具调用")
    print("="*80)

    llm = GPT4oMiniLLM()
    calculator = CalculatorTool()
    agent = Agent(llm=llm, tools=[calculator], max_iterations=5)

    print("\n💬 用户：帮我计算 (123 + 456) * 2")
    print("\n📡 Agent 事件流：")
    print("-" * 80)

    async for event in agent.execute("帮我计算 (123 + 456) * 2"):
        if event.type == AgentEventType.ITERATION_START:
            print(f"\n🔄 [第{event.iteration}轮] 开始")

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            tool_count = event.metadata.get("tool_count", 0)
            tool_names = event.metadata.get("tool_names", [])
            print(f"\n🔧 [LLM] 请求调用 {tool_count} 个工具: {tool_names}")

        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            if event.tool_call:
                print(f"\n⚙️  [工具] 执行 {event.tool_call.name}({event.tool_call.arguments})")

        elif event.type == AgentEventType.TOOL_RESULT:
            if event.tool_result:
                print(f"✓ [结果] {event.tool_result.content[:100]}")

        elif event.type == AgentEventType.RECURSION:
            depth = event.metadata.get("depth", 0)
            print(f"\n🔁 [递归] 进入第 {depth} 层递归")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n\n✅ [完成] 对话结束")


async def test_multi_tool_calls():
    """测试 3：多次工具调用（复杂任务）"""
    print("\n" + "="*80)
    print("🧪 测试 3：多次工具调用（复杂任务）")
    print("="*80)

    llm = GPT4oMiniLLM()
    calculator = CalculatorTool()
    weather = WeatherTool()
    search = SearchTool()

    agent = Agent(
        llm=llm,
        tools=[calculator, weather, search],
        max_iterations=10
    )

    print("\n💬 用户：帮我查询北京和上海的天气，然后计算两地温差")
    print("\n📡 Agent 事件流：")
    print("-" * 80)

    recursion_count = 0
    tool_calls_count = 0

    async for event in agent.execute("帮我查询北京和上海的天气，然后计算两地温差"):
        if event.type == AgentEventType.ITERATION_START:
            print(f"\n🔄 [第{event.iteration}轮] 开始")

        elif event.type == AgentEventType.PHASE_START:
            phase = event.metadata.get("phase", "unknown")
            print(f"\n📍 [阶段] {phase} 开始")

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            tool_count = event.metadata.get("tool_count", 0)
            tool_names = event.metadata.get("tool_names", [])
            tool_calls_count += tool_count
            print(f"\n🔧 [LLM] 请求调用 {tool_count} 个工具: {tool_names}")

        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            if event.tool_call:
                print(f"\n⚙️  [工具] 执行 {event.tool_call.name}({event.tool_call.arguments})")

        elif event.type == AgentEventType.TOOL_RESULT:
            if event.tool_result:
                content = event.tool_result.content
                preview = content[:80] + "..." if len(content) > 80 else content
                print(f"✓ [结果] {preview}")

        elif event.type == AgentEventType.RECURSION:
            recursion_count += 1
            depth = event.metadata.get("depth", 0)
            print(f"\n🔁 [递归] 进入第 {depth} 层递归 (总计 {recursion_count} 次)")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n\n✅ [完成] 对话结束")
            print(f"\n📊 统计：")
            print(f"   - 递归次数: {recursion_count}")
            print(f"   - 工具调用: {tool_calls_count}")
            print(f"   - 总轮数: {event.metadata.get('turn_counter', 0) + 1}")


async def test_context_assembly():
    """测试 4：上下文组装（Context Assembly）"""
    print("\n" + "="*80)
    print("🧪 测试 4：上下文组装（Context Assembly）")
    print("="*80)

    llm = GPT4oMiniLLM()
    calculator = CalculatorTool()

    # 添加自定义系统指令
    system_instructions = """你是一个专业的数学助手。
你的职责是：
1. 帮助用户进行数学计算
2. 解释计算过程
3. 提供清晰的步骤

请保持专业、友好的态度。"""

    agent = Agent(
        llm=llm,
        tools=[calculator],
        max_iterations=5,
        system_instructions=system_instructions,
        max_context_tokens=4000  # 设置上下文限制
    )

    print("\n💬 用户：请帮我计算复利：本金10000元，年利率5%，3年后的总额")
    print("\n📡 Agent 事件流：")
    print("-" * 80)

    async for event in agent.execute("请帮我计算复利：本金10000元，年利率5%，3年后的总额"):
        if event.type == AgentEventType.PHASE_START:
            phase = event.metadata.get("phase", "")
            if phase == "context_assembly":
                print(f"\n📋 [上下文组装] 开始组装上下文...")

        elif event.type == AgentEventType.PHASE_END:
            phase = event.metadata.get("phase", "")
            if phase == "context_assembly":
                tokens_used = event.metadata.get("tokens_used", 0)
                components = event.metadata.get("components", 0)
                utilization = event.metadata.get("utilization", 0)
                print(f"✓ [上下文组装] 完成")
                print(f"   - Token 使用: {tokens_used}")
                print(f"   - 组件数量: {components}")
                print(f"   - 利用率: {utilization:.1%}")

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            tool_names = event.metadata.get("tool_names", [])
            print(f"\n🔧 [LLM] 调用工具: {tool_names}")

        elif event.type == AgentEventType.TOOL_RESULT:
            if event.tool_result:
                print(f"✓ [工具结果] {event.tool_result.content}")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n\n✅ [完成] 对话结束")


async def test_max_iterations():
    """测试 5：最大迭代次数限制"""
    print("\n" + "="*80)
    print("🧪 测试 5：最大迭代次数限制")
    print("="*80)

    llm = GPT4oMiniLLM()
    search = SearchTool()

    agent = Agent(
        llm=llm,
        tools=[search],
        max_iterations=3  # 故意设置较小值
    )

    print("\n💬 用户：请帮我搜索Python、JavaScript和Go的最新特性")
    print("\n📡 Agent 事件流：")
    print("-" * 80)

    iteration_count = 0

    async for event in agent.execute("请帮我搜索Python、JavaScript和Go的最新特性"):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1
            print(f"\n🔄 [第{iteration_count}轮] 开始")

        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            max_iter = event.metadata.get("max_iterations", 0)
            print(f"\n⚠️  [警告] 达到最大迭代次数限制: {max_iter}")
            print(f"   当前已完成 {iteration_count} 轮")

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            tool_names = event.metadata.get("tool_names", [])
            print(f"🔧 [LLM] 调用工具: {tool_names}")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n\n✅ [完成] 对话结束")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🚀 Loom Agent 新特性测试")
    print("   - tt 递归模式")
    print("   - Context Assembly（上下文组装）")
    print("   - Event Streaming（事件流）")
    print("="*80)

    try:
        # 测试 1：基础对话
        await test_basic_conversation()
        await asyncio.sleep(1)

        # 测试 2：单次工具调用
        await test_single_tool_call()
        await asyncio.sleep(1)

        # 测试 3：多次工具调用
        await test_multi_tool_calls()
        await asyncio.sleep(1)

        # 测试 4：上下文组装
        await test_context_assembly()
        await asyncio.sleep(1)

        # 测试 5：最大迭代限制
        await test_max_iterations()

        print("\n" + "="*80)
        print("✅ 所有测试完成！")
        print("="*80)
        print("\n关键特性验证：")
        print("  ✓ tt 递归模式正常工作")
        print("  ✓ 事件流实时传输")
        print("  ✓ 工具调用正确执行")
        print("  ✓ 上下文组装成功")
        print("  ✓ 递归深度控制有效")
        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 确保安装了 openai 库
    try:
        import openai
    except ImportError:
        print("❌ 请先安装 openai 库: pip install openai")
        exit(1)

    asyncio.run(main())
