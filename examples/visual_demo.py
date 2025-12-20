"""
Loom Visualization Demo

展示 Loom Studio CLI 版的实时可视化效果。
模拟一个复杂的 Agent 执行流程。
"""

import asyncio
import random
from loom.core.events import (
    AgentEventType, 
    create_agent_start_event,
    create_agent_end_event,
    create_tool_start_event,
    create_tool_end_event,
    create_llm_end_event
)
from loom.visualization.console import RichTraceHandler

async def simulate_execution():
    # 初始化 Visualizer
    visualizer = RichTraceHandler()
    visualizer.start()
    
    try:
        # 1. 主 Agent 开始
        await visualizer.emit(create_agent_start_event(
            "Manager", 
            "分析 2024 年 AI 芯片市场趋势"
        ))
        await asyncio.sleep(1)

        # 2. 调用 LLM
        await visualizer.emit(create_llm_end_event("Manager", {"tokens": 150}))
        
        # 3. 委派给 Researcher
        await visualizer.emit(create_agent_start_event(
            "Researcher",
            "搜索相关报告"
        ))
        await asyncio.sleep(0.5)
        
        # 4. Researcher 调用工具
        await visualizer.emit(create_tool_start_event(
            "google_search",
            {"query": "AI chip market share 2024", "tbs": "qdr:y"},
            "Researcher"
        ))
        await asyncio.sleep(1.5) # 模拟工具耗时
        
        await visualizer.emit(create_tool_end_event(
            "google_search",
            "Nvidia holds 90% market share...",
            "Researcher"
        ))

        # 5. Researcher 再调一次工具
        await visualizer.emit(create_tool_start_event(
            "download_pdf",
            {"url": "https://gartner.com/report.pdf"},
            "Researcher"
        ))
        await asyncio.sleep(2)
        
        await visualizer.emit(create_tool_end_event(
            "download_pdf",
            "[Binary Data...]",
            "Researcher"
        ))
        
        # 6. Researcher 结束
        await visualizer.emit(create_agent_end_event(
            "Researcher",
            "已获取 2 份关键报告"
        ))
        await asyncio.sleep(1)

        # 7. 委派给 Analyst
        await visualizer.emit(create_agent_start_event(
            "Analyst",
            "根据报告撰写可视化分析"
        ))
        
        # 8. Analyst 调用 Python 工具
        await visualizer.emit(create_tool_start_event(
            "python_repl",
            {"code": "import matplotlib.pyplot as plt..."},
            "Analyst"
        ))
        await asyncio.sleep(1)
        await visualizer.emit(create_tool_end_event(
            "python_repl",
            "Chart defined at /tmp/chart.png",
            "Analyst"
        ))
        
        await visualizer.emit(create_agent_end_event(
            "Analyst",
            "分析完成，图表已生成"
        ))
        
        # 9. 主 Agent 结束
        await visualizer.emit(create_agent_end_event(
            "Manager",
            "最终报告：AI 芯片市场持续增长，Nvidia 保持统治地位..."
        ))
        
    finally:
        visualizer.stop()

if __name__ == "__main__":
    asyncio.run(simulate_execution())
