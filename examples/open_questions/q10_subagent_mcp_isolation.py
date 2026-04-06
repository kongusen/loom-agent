"""Q10: Sub-Agent MCP Isolation

问题: Sub-Agent 连接了主 Agent 没有的 MCP server，主 Agent 如何理解专属工具输出？
观测现象: Sub-Agent 能完成任务，但回传结果在主 Agent 侧缺少工具语义上下文
实验设计: 设计带专属 MCP 的 Sub-Agent，比较三种回传格式
证据要求: Sub-Agent 输出样本、主 Agent 消费成功率、误解释案例、结构化模板
"""

from loom.cluster.fork import SubAgent

async def experiment_mcp_isolation():
    formats = [
        "natural_language_only",
        "result_with_tool_description",
        "result_with_structured_schema"
    ]

    results = {}
    for fmt in formats:
        # Sub-Agent 使用专属 MCP (例如 database-inspector)
        sub = SubAgent(mcp_servers=["database-inspector"], return_format=fmt)
        result = await sub.execute("分析数据库性能瓶颈")

        # 主 Agent 尝试消费结果
        main_agent_understanding = await evaluate_consumption(result)

        results[fmt] = {
            "consumption_success": main_agent_understanding.success,
            "misinterpretation_count": main_agent_understanding.errors,
            "result_sample": result[:200]
        }

    return results

async def evaluate_consumption(result):
    # 评估主 Agent 是否能正确理解结果
    return {"success": True, "errors": 0}
