"""Agent 构建工厂。

基于 Loom 0.0.3 重构模式，使用统一协调机制和简化的 API 接口。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from loom.core.agent_executor import AgentExecutor
from loom.core.unified_coordination import UnifiedExecutionContext
from loom.builtin.memory.in_memory import InMemoryMemory
from loom.builtin.tools.task import TaskTool

from .config import DEFAULT_SQL_CONFIG, SQLTemplateConfig
from .llms import create_llm
from .metadata import DorisSchemaExplorer
from .tools import DorisSelectTool, SchemaLookupTool


COORDINATOR_SYSTEM_PROMPT = (
    "你是旅游业务分析 SQL 专家。你必须严格按照以下步骤工作：\n\n"
    "阶段1：数据源探索\n"
    "- 使用 schema_lookup 工具查找与占位符相关的表\n"
    "- 使用 doris_select 工具获取表的样例数据，了解字段含义\n"
    "- 确保基于真实的数据库结构和数据\n\n"
    "阶段2：SQL 生成\n"
    "- 在收集到足够的数据源信息后，立即生成 SQL\n"
    "- 不要无限循环调用工具\n"
    "- 基于工具返回的真实数据生成准确的 SQL\n"
    "- 使用 ```sql 代码块包裹最终的 SQL\n\n"
    "重要规则：\n"
    "1. 每个占位符最多调用 1-2 次工具\n"
    "2. 在工具调用完成后，必须生成 SQL\n"
    "3. 不要重复调用相同的工具\n"
    "4. 如果已经了解了表结构，就直接生成 SQL\n\n"
    "当前任务：分析模板占位符，使用工具获取数据源信息，然后生成 SQL。"
)

PLACEHOLDER_SYSTEM_PROMPT = (
    "你是一名占位符分析专家，请针对提供的占位符调用工具确认字段，"
    "给出表、字段、聚合表达式以及可复用的 SELECT 片段。"
)


def build_sql_template_agent(
    explorer: DorisSchemaExplorer,
    config: Optional[SQLTemplateConfig] = None,
    execution_id: Optional[str] = None,
) -> AgentExecutor:
    """构建基于 Loom 0.0.3 统一协调的 SQL 模板代理。
    
    Args:
        explorer: Doris 模式探索器
        config: SQL 模板专用配置，默认使用 DEFAULT_SQL_CONFIG
        execution_id: 执行 ID，用于跟踪和调试
        
    Returns:
        配置好的 AgentExecutor 实例
    """
    if config is None:
        config = DEFAULT_SQL_CONFIG
    
    # 创建统一协调上下文
    unified_context = UnifiedExecutionContext(
        execution_id=execution_id or "sql_template_analysis",
        config=config
    )
    
    # 创建工具实例
    tools = {
        "schema_lookup": SchemaLookupTool(explorer),
        "doris_select": DorisSelectTool(explorer),
        "task": TaskTool(),  # 添加任务工具支持
    }
    
    # 创建 LLM 实例
    llm = create_llm(model="gpt-4o-mini")
    
    # 创建内存实例
    memory = InMemoryMemory()
    
    # 使用新的简化 API 创建 AgentExecutor
    return AgentExecutor(
        llm=llm,
        tools=tools,
        memory=memory,
        unified_context=unified_context,
        max_iterations=config.max_iterations,
        system_instructions=COORDINATOR_SYSTEM_PROMPT,
    )


def build_placeholder_agent(
    explorer: DorisSchemaExplorer,
    config: Optional[SQLTemplateConfig] = None,
    execution_id: Optional[str] = None,
) -> AgentExecutor:
    """构建占位符分析子代理。
    
    Args:
        explorer: Doris 模式探索器
        config: SQL 模板专用配置
        execution_id: 执行 ID
        
    Returns:
        配置好的占位符分析 AgentExecutor 实例
    """
    if config is None:
        config = DEFAULT_SQL_CONFIG
    
    # 创建统一协调上下文
    unified_context = UnifiedExecutionContext(
        execution_id=execution_id or "placeholder_analysis",
        config=config
    )
    
    # 创建工具实例
    tools = {
        "schema_lookup": SchemaLookupTool(explorer),
        "doris_select": DorisSelectTool(explorer),
    }
    
    # 创建 LLM 实例
    llm = create_llm(model="gpt-4o-mini")
    
    # 使用新的简化 API 创建 AgentExecutor
    return AgentExecutor(
        llm=llm,
        tools=tools,
        memory=None,  # 占位符分析不需要持久化内存
        unified_context=unified_context,
        max_iterations=6,  # 占位符分析迭代次数较少
        system_instructions=PLACEHOLDER_SYSTEM_PROMPT,
    )

