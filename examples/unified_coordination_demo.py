#!/usr/bin/env python3
"""
Loom Agent 0.0.3 统一协调机制演示

展示四大核心能力如何协同工作，实现智能上下文在 TT 递归中组织复杂任务
"""

import asyncio
import time
from typing import Dict, Any, List

from loom.core.agent_executor import AgentExecutor, TaskHandler
from loom.core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator,
    CoordinationConfig
)
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message
from loom.core.events import AgentEventType
from loom.llm.factory import LLMFactory
from loom.builtin.tools import TaskTool, ReadFileTool, WriteTool, GrepTool


class ComplexAnalysisTaskHandler(TaskHandler):
    """复杂分析任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        analysis_keywords = ["analyze", "analysis", "examine", "review", "评估", "分析", "检查"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in analysis_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["suggests_completion"] or result_analysis["completeness_score"] >= 0.8:
            return f"""信息收集基本完成。请基于已收集的信息完成分析任务：{original_task}

请提供：
1. 关键发现和洞察
2. 数据支持的分析结论  
3. 建议或推荐行动
4. 任何需要注意的限制或风险"""
        
        elif result_analysis["has_errors"]:
            return f"""分析过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查数据源是否可用
- 尝试不同的分析方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续分析任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多数据或使用分析工具处理已获得的信息"""


class CodeGenerationTaskHandler(TaskHandler):
    """代码生成任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        generation_keywords = ["generate", "create", "build", "make", "生成", "创建", "构建", "开发"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in generation_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["completeness_score"] >= 0.7:
            return f"""信息收集完成。请基于收集到的信息生成代码完成任务：{original_task}

请提供：
- 完整的代码实现
- 必要的注释和文档
- 使用说明或示例"""
        
        elif result_analysis["has_errors"]:
            return f"""代码生成过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查模板或参考代码是否可用
- 尝试不同的生成方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续代码生成任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多参考信息或使用代码分析工具"""


class UnifiedCoordinationDemo:
    """统一协调机制演示"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = LLMFactory.create_openai(api_key=api_key, model="gpt-4")
    
    def create_agent_factory(self, max_iterations=20, **kwargs):
        """Agent 工厂函数"""
        return AgentExecutor(
            llm=self.llm,
            max_iterations=max_iterations,
            **kwargs
        )
    
    async def demo_unified_coordination(self, task_description: str):
        """演示统一协调机制"""
        
        print(f"\n{'='*80}")
        print(f"🎯 统一协调机制演示")
        print(f"📝 任务: {task_description}")
        print(f"{'='*80}\n")
        
        # 1. 创建统一执行上下文（使用自定义配置）
        config = CoordinationConfig(
            deep_recursion_threshold=3,
            high_complexity_threshold=0.7,
            context_cache_size=100,
            event_batch_size=10,
            event_batch_timeout=0.05  # 降低延迟
        )

        unified_context = UnifiedExecutionContext(
            execution_id=f"demo_{int(time.time())}",
            config=config
        )
        
        # 2. 创建任务处理器
        task_handlers = [
            ComplexAnalysisTaskHandler(),
            CodeGenerationTaskHandler()
        ]
        
        # 3. 创建工具
        tools = {
            "task": TaskTool(agent_factory=self.create_agent_factory),
            "read_file": ReadFileTool(),
            "write_file": WriteTool(),
            "grep": GrepTool()
        }
        
        # 4. 创建执行器（统一协调自动启用）
        executor = AgentExecutor(
            llm=self.llm,
            tools=tools,
            unified_context=unified_context,
            task_handlers=task_handlers
        )
        
        # 5. 执行任务
        turn_state = TurnState.initial(max_iterations=15)
        context = ExecutionContext.create()
        messages = [Message(role="user", content=task_description)]
        
        print("🚀 开始执行任务...")
        print("-" * 60)
        
        start_time = time.time()
        event_count = 0
        
        async for event in executor.tt(messages, turn_state, context):
            event_count += 1
            
            # 显示 LLM 输出
            if event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)
            
            # 显示工具执行
            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                print(f"\n🔧 执行工具: {event.tool_call.name}")
                if hasattr(event.tool_call, 'arguments'):
                    print(f"   参数: {event.tool_call.arguments}")
            
            # 显示工具结果
            elif event.type == AgentEventType.TOOL_RESULT:
                result = event.tool_result
                print(f"   ✓ 完成 ({result.execution_time_ms:.0f}ms)")
            
            # 显示错误
            elif event.type == AgentEventType.ERROR:
                print(f"\n❌ 错误: {event.error}")
            
            # 任务完成
            elif event.type == AgentEventType.AGENT_FINISH:
                execution_time = time.time() - start_time
                print(f"\n\n✅ 任务完成!")
                print(f"⏱️  执行时间: {execution_time:.2f}秒")
                print(f"📊 事件总数: {event_count}")
                
                # 获取统一性能指标
                await self._display_unified_metrics(executor)
                break
        
        print(f"\n{'-'*60}")
        print("🎉 统一协调机制演示完成!")
    
    async def _display_unified_metrics(self, executor: AgentExecutor):
        """显示统一性能指标"""
        
        print(f"\n📈 统一性能指标:")
        print(f"{'='*50}")
        
        try:
            metrics = executor.get_unified_metrics()
            
            # 任务分析指标
            if "task_analysis" in metrics:
                task_analysis = metrics["task_analysis"]
                print(f"🎯 任务分析:")
                print(f"   - 任务类型: {task_analysis.get('task_type', 'unknown')}")
                print(f"   - 复杂度评分: {task_analysis.get('complexity_score', 0):.2f}")
                
                recursion_context = task_analysis.get('recursion_context', {})
                print(f"   - 递归深度: {recursion_context.get('turn_counter', 0)}")
                print(f"   - 最大迭代: {recursion_context.get('max_iterations', 0)}")
            
            # ContextAssembler 指标
            if "context_assembler" in metrics:
                ca_metrics = metrics["context_assembler"]
                print(f"\n🧩 ContextAssembler:")
                print(f"   - 组件数量: {ca_metrics.get('component_count', 0)}")
                print(f"   - Token 使用率: {ca_metrics.get('budget_utilization', 0):.1%}")
                print(f"   - 缓存命中率: {ca_metrics.get('cache_hit_rate', 0):.1%}")
            
            # TaskTool 指标
            if "task_tool" in metrics:
                tt_metrics = metrics["task_tool"]
                print(f"\n🔧 TaskTool:")
                print(f"   - 池大小: {tt_metrics.get('pool_size', 0)}")
                print(f"   - 缓存命中率: {tt_metrics.get('cache_hit_rate', 0):.1%}")
                print(f"   - 平均执行时间: {tt_metrics.get('average_execution_time', 0):.2f}秒")
            
            # EventProcessor 指标
            if "event_processor" in metrics:
                ep_metrics = metrics["event_processor"]
                print(f"\n📡 EventProcessor:")
                print(f"   - 处理事件数: {ep_metrics.get('events_processed', 0)}")
                print(f"   - 平均处理时间: {ep_metrics.get('average_processing_time', 0):.3f}秒")
                print(f"   - 批处理次数: {ep_metrics.get('batch_count', 0)}")
            
        except Exception as e:
            print(f"❌ 获取指标失败: {e}")
    
    async def run_comprehensive_demo(self):
        """运行综合演示"""
        
        print("🎪 Loom Agent 0.0.3 统一协调机制综合演示")
        print("=" * 80)
        
        # 演示不同类型的复杂任务
        demo_tasks = [
            "分析这个 Python 项目的代码质量，包括安全性、性能和可维护性",
            "生成一个完整的 REST API 系统，包括用户认证、数据管理和 API 文档",
            "创建一套自动化测试框架，支持单元测试、集成测试和性能测试",
            "开发一个智能数据分析工具，能够处理多种数据格式并生成可视化报告"
        ]
        
        for i, task in enumerate(demo_tasks, 1):
            print(f"\n🎬 演示 {i}/{len(demo_tasks)}")
            await self.demo_unified_coordination(task)
            
            if i < len(demo_tasks):
                print(f"\n⏳ 等待 3 秒后继续下一个演示...")
                await asyncio.sleep(3)
        
        print(f"\n🎊 所有演示完成!")
        print(f"💡 统一协调机制让四大核心能力协同工作，实现智能任务处理!")


async def main():
    """主函数"""
    
    # 设置 API Key（请替换为您的实际 API Key）
    api_key = "sk-your-openai-api-key-here"
    
    if api_key == "sk-your-openai-api-key-here":
        print("❌ 请设置您的 OpenAI API Key")
        print("在 main() 函数中修改 api_key 变量")
        return
    
    # 创建演示实例
    demo = UnifiedCoordinationDemo(api_key)
    
    # 运行综合演示
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    asyncio.run(main())
