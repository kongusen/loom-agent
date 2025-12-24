#!/usr/bin/env python3
"""
测试 Loom Studio 的脚本 - 分形结构版本
运行这个脚本会产生事件，可以在 Studio 中观察到完整的分形自组织过程
"""

import asyncio
import os
import sys
from typing import List, Dict, Any, AsyncIterator, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.crew import CrewNode
from loom.interfaces.llm import LLMProvider, LLMResponse
from loom.infra.llm import MockLLMProvider

# 创建一个更智能的 Mock Provider，能根据角色返回不同的响应
class SmartMockProvider(MockLLMProvider):
    """根据角色返回不同响应的 Mock Provider"""
    
    def __init__(self, role: str = "generic"):
        super().__init__()
        self.role = role
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        last_msg = messages[-1]["content"].lower()
        
        # 根据角色返回不同的响应
        if "collector" in self.role or "收集" in self.role:
            content = f"""我已经收集了以下信息：

1. **技术概念**：
   - AI Agent 自组织分型架构是一种递归的系统设计模式
   - 每个节点都可以包含其他节点，形成分形结构
   - 节点之间通过事件总线进行通信

2. **关键案例**：
   - Loom 框架实现了这种架构
   - Crew 可以包含 Agent，Agent 可以包含 Tool
   - 支持无限递归嵌套

3. **技术特点**：
   - 事件驱动架构
   - 新陈代谢记忆系统
   - 上下文自动净化

这些信息已经整理完成，可以传递给下一个节点进行分析。"""
        
        elif "analyzer" in self.role or "分析" in self.role:
            content = f"""基于收集的信息，我进行了深度分析：

**核心发现**：
1. 分形架构的优势在于可扩展性和模块化
2. 自组织能力使得系统能够动态适应
3. 事件驱动模式确保了松耦合

**模式识别**：
- 递归结构：每个层级都遵循相同的模式
- 上下文传递：信息在层级间流动和净化
- 状态管理：每个节点维护自己的状态

**建议**：
应该继续深入探索这种架构在实际应用中的表现。"""
        
        elif "planner" in self.role or "规划" in self.role:
            content = f"""我制定了以下行动计划：

**阶段一：准备**
1. 整理技术概念和案例
2. 准备演示材料
3. 设计互动环节

**阶段二：执行**
1. 介绍分形架构概念（15分钟）
2. 演示 Loom 框架（20分钟）
3. Q&A 环节（10分钟）

**阶段三：总结**
1. 总结关键要点
2. 提供学习资源
3. 收集反馈

这个计划已经准备好执行。"""
        
        elif "executor" in self.role or "执行" in self.role:
            content = f"""执行结果报告：

**已完成的工作**：
1. ✅ 技术分享会材料已准备
2. ✅ 演示环境已搭建
3. ✅ 互动环节已设计

**执行细节**：
- 演示代码：已创建完整的示例
- 可视化工具：Loom Studio 已配置
- 文档：技术文档已更新

**遇到的问题**：
- 无重大问题
- 所有任务按计划完成

**下一步建议**：
可以开始进行技术分享会了。"""
        
        else:
            content = f"Mock response from {self.role}: {last_msg[:50]}..."
        
        return LLMResponse(content=content)

async def main():
    print("=" * 80)
    print("🧪 Loom Studio 测试脚本 - 分形结构版本")
    print("=" * 80)
    print("\n这个脚本会创建一个完整的分形 Agent 系统")
    print("系统结构：")
    print("  master-crew (主 Crew)")
    print("    ├─ research-crew (研究 Crew)")
    print("    │   ├─ collector (信息收集 Agent)")
    print("    │   └─ analyzer (分析 Agent)")
    print("    └─ creative-crew (创作 Crew)")
    print("        ├─ planner (规划 Agent)")
    print("        └─ executor (执行 Agent)")
    print("\n所有事件都会被发送到 Loom Studio (http://localhost:5173)")
    print("请在浏览器中打开 http://localhost:5173/topology 观察事件流\n")
    
    # 启用 Studio 拦截器
    app = LoomApp(control_config={
        "studio": {
            "enabled": True,
            "url": "ws://localhost:8765"
        }
    })
    
    print("✅ Studio 拦截器已启用")
    
    # ========== 第一层：基础 Agent ==========
    
    # 信息收集 Agent
    collector = AgentNode(
        node_id="agent/collector",
        dispatcher=app.dispatcher,
        role="信息收集专家",
        system_prompt="""你是一个专业的信息收集专家。
你的任务是：
1. 理解用户的需求
2. 收集和整理相关信息
3. 以结构化的方式输出关键信息点

输出格式：使用清晰的列表和分类。""",
        provider=SmartMockProvider("collector")
    )
    
    # 分析 Agent
    analyzer = AgentNode(
        node_id="agent/analyzer",
        dispatcher=app.dispatcher,
        role="数据分析师",
        system_prompt="""你是一个数据分析师。
你的任务是：
1. 接收信息收集的结果
2. 进行深度分析和模式识别
3. 提取关键洞察和结论

输出格式：提供结构化的分析报告，包含主要发现和建议。""",
        provider=SmartMockProvider("analyzer")
    )
    
    # 规划 Agent
    planner = AgentNode(
        node_id="agent/planner",
        dispatcher=app.dispatcher,
        role="战略规划师",
        system_prompt="""你是一个战略规划师。
你的任务是：
1. 基于分析结果制定行动计划
2. 将任务分解为可执行的步骤
3. 考虑优先级和依赖关系

输出格式：提供清晰的行动计划，包含步骤和预期结果。""",
        provider=SmartMockProvider("planner")
    )
    
    # 执行 Agent
    executor = AgentNode(
        node_id="agent/executor",
        dispatcher=app.dispatcher,
        role="执行专家",
        system_prompt="""你是一个执行专家。
你的任务是：
1. 接收详细的行动计划
2. 执行具体的任务
3. 提供执行结果和反馈

输出格式：提供详细的执行报告，包含结果、遇到的问题和解决方案。""",
        provider=SmartMockProvider("executor")
    )
    
    # 注册所有 Agent
    app.add_node(collector)
    app.add_node(analyzer)
    app.add_node(planner)
    app.add_node(executor)
    
    print("✅ 基础 Agent 已创建")
    print("  - agent/collector (信息收集)")
    print("  - agent/analyzer (数据分析)")
    print("  - agent/planner (战略规划)")
    print("  - agent/executor (执行专家)")
    
    # ========== 第二层：Crew（包含 Agent）==========
    
    # 研究 Crew：收集 → 分析
    research_crew = CrewNode(
        node_id="crew/research",
        dispatcher=app.dispatcher,
        agents=[collector, analyzer],
        pattern="sequential"
    )
    
    # 创作 Crew：规划 → 执行
    creative_crew = CrewNode(
        node_id="crew/creative",
        dispatcher=app.dispatcher,
        agents=[planner, executor],
        pattern="sequential"
    )
    
    app.add_node(research_crew)
    app.add_node(creative_crew)
    
    print("✅ Crew 已创建")
    print("  - crew/research (研究 Crew: collector → analyzer)")
    print("  - crew/creative (创作 Crew: planner → executor)")
    
    # ========== 第三层：主 Crew（包含 Crew）==========
    # 创建一个包装器 Agent，它内部调用 Crew
    class CrewWrapperAgent(AgentNode):
        """包装 CrewNode 使其可以作为 AgentNode 使用"""
        def __init__(self, crew_node: CrewNode, role_name: str):
            super().__init__(
                node_id=f"{crew_node.node_id}-wrapper",
                dispatcher=crew_node.dispatcher,
                role=role_name,
                system_prompt=f"你是一个包装器，负责调用 {crew_node.node_id} 并传递结果。",
                provider=SmartMockProvider(role_name)
            )
            self.crew_node = crew_node
            
        async def process(self, event):
            """直接调用被包装的 CrewNode"""
            return await self.crew_node.process(event)
    
    # 创建包装器
    research_wrapper = CrewWrapperAgent(research_crew, "研究包装器")
    creative_wrapper = CrewWrapperAgent(creative_crew, "创作包装器")
    app.add_node(research_wrapper)
    app.add_node(creative_wrapper)
    
    # 主 Crew 使用包装器
    master_crew = CrewNode(
        node_id="crew/master",
        dispatcher=app.dispatcher,
        agents=[research_wrapper, creative_wrapper],
        pattern="sequential"
    )
    
    app.add_node(master_crew)
    
    print("✅ 主 Crew 已创建")
    print("  - crew/master (主 Crew: research-crew → creative-crew)")
    
    # 等待一下，让 WebSocket 连接建立
    print("\n⏳ 等待 Studio 连接建立...")
    await asyncio.sleep(3)
    
    # 运行几个任务来产生事件
    print("\n🚀 开始运行任务...")
    print("-" * 80)
    
    tasks = [
        """请帮我研究并规划一个关于"AI Agent 自组织分型架构"的技术分享会。
需要包括：
1. 收集相关的技术概念和案例
2. 分析这些概念之间的关系和模式
3. 制定一个清晰的分享计划
4. 准备具体的执行方案""",
        
        """研究一下分形架构在实际项目中的应用，并制定实施计划。""",
        
        """分析多 Agent 系统的协作模式，并规划一个演示项目。"""
    ]
    
    for i, task in enumerate(tasks, 1):
        print(f"\n📋 任务 {i}: {task[:60]}...")
        try:
            result = await app.run(task, target="node/crew/master")
            print(f"✅ 任务 {i} 完成")
            if isinstance(result, dict) and "final_output" in result:
                output_preview = result['final_output'][:150]
                print(f"   输出预览: {output_preview}...")
            
            # 显示执行轨迹
            if isinstance(result, dict) and "trace" in result:
                print(f"   执行步骤: {len(result['trace'])} 个节点")
                for step in result['trace']:
                    print(f"     - {step.get('agent', 'unknown')}")
        except Exception as e:
            print(f"❌ 任务 {i} 出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 等待一下，让事件有时间发送到 Studio
        await asyncio.sleep(2)
    
    print("\n" + "=" * 80)
    print("✨ 测试完成！")
    print("=" * 80)
    print("\n现在可以在 Loom Studio 中查看:")
    print("  - Topology 视图: http://localhost:5173/topology")
    print("  - Timeline 视图: http://localhost:5173/timeline")
    print("  - Memory 视图: http://localhost:5173/memory")
    print("\n系统包含以下节点:")
    print("  - crew/master (主 Crew)")
    print("  - crew/research (研究 Crew)")
    print("  - crew/creative (创作 Crew)")
    print("  - agent/collector (信息收集)")
    print("  - agent/analyzer (数据分析)")
    print("  - agent/planner (战略规划)")
    print("  - agent/executor (执行专家)")
    print("\n脚本将继续运行，你可以继续在 Studio 中观察...")
    print("按 Ctrl+C 停止\n")
    
    # 保持运行，让用户有时间观察
    try:
        await asyncio.sleep(3600)  # 运行1小时
    except KeyboardInterrupt:
        print("\n\n👋 再见！")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 脚本已停止")
