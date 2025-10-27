"""自主 SQL 模板代理 - 基于 Loom 0.0.3 重构

实现完整的自主分析流程：
1. 表发现和结构分析
2. 数据采样和观察
3. SQL 生成和验证
4. 结果返回和报告
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import asyncio
import json
import time

from loom.core.agent_executor import AgentExecutor
from loom.core.unified_coordination import UnifiedExecutionContext
from loom.core.events import AgentEventType
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message
from loom.builtin.memory.in_memory import InMemoryMemory
from loom.builtin.tools.task import TaskTool

from .config import DEFAULT_SQL_CONFIG, SQLTemplateConfig
from .llms import create_llm
from .metadata import DorisSchemaExplorer
from .tools import DorisSelectTool, SchemaLookupTool


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    placeholder: str
    target_table: Optional[str] = None
    table_structure: Optional[Dict[str, Any]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    generated_sql: Optional[str] = None
    query_result: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class AutonomousAnalysisConfig:
    """自主分析配置"""
    max_table_discovery_attempts: int = 3
    max_sample_queries: int = 5
    sample_data_limit: int = 10
    enable_data_observation: bool = True
    enable_sql_validation: bool = True
    analysis_timeout: int = 300  # 5分钟


class AutonomousSQLTemplateAgent:
    """自主 SQL 模板代理
    
    实现完整的自主分析流程：
    1. 根据占位符自动发现相关表
    2. 分析表结构和字段含义
    3. 采样数据观察实际内容
    4. 生成符合占位符的 SQL
    5. 验证 SQL 并返回结果
    """
    
    def __init__(
        self,
        explorer: DorisSchemaExplorer,
        config: Optional[SQLTemplateConfig] = None,
        analysis_config: Optional[AutonomousAnalysisConfig] = None,
    ):
        self.explorer = explorer
        self.config = config or DEFAULT_SQL_CONFIG
        self.analysis_config = analysis_config or AutonomousAnalysisConfig()
        
        # 创建核心代理
        self._setup_agents()
        
        # 分析状态
        self.analysis_history: List[AnalysisResult] = []
        
    def _setup_agents(self):
        """设置核心代理"""
        # 主分析代理
        self.main_agent = self._build_main_agent()
        
        # 表发现代理
        self.table_discovery_agent = self._build_table_discovery_agent()
        
        # SQL 生成代理
        self.sql_generation_agent = self._build_sql_generation_agent()
        
    def _build_main_agent(self) -> AgentExecutor:
        """构建主分析代理"""
        unified_context = UnifiedExecutionContext(
            execution_id=f"autonomous_analysis_{int(time.time())}",
            config=self.config
        )
        
        tools = {
            "schema_lookup": SchemaLookupTool(self.explorer),
            "doris_select": DorisSelectTool(self.explorer),
            "task": TaskTool(),
        }
        
        llm = create_llm(model="gpt-4o-mini")
        memory = InMemoryMemory()
        
        system_prompt = """
你是自主 SQL 分析专家，能够根据占位符自动完成以下任务：

1. 表发现：使用 schema_lookup 工具查找与占位符相关的表
2. 结构分析：分析表结构和字段含义
3. 数据采样：使用 doris_select 工具获取样例数据
4. SQL 生成：基于分析结果生成准确的 SQL
5. 结果验证：执行 SQL 并验证结果

工作流程：
- 首先调用 schema_lookup 查找相关表
- 然后调用 doris_select 获取样例数据
- 基于真实数据生成 SQL
- 最后验证 SQL 结果

重要规则：
- 每个占位符最多调用 3-5 次工具
- 必须基于真实数据生成 SQL
- 生成的 SQL 必须用 ```sql 代码块包裹
- 如果发现错误，要及时调整策略
"""
        
        return AgentExecutor(
            llm=llm,
            tools=tools,
            memory=memory,
            unified_context=unified_context,
            max_iterations=self.config.max_iterations,
            system_instructions=system_prompt,
        )
    
    def _build_table_discovery_agent(self) -> AgentExecutor:
        """构建表发现代理"""
        unified_context = UnifiedExecutionContext(
            execution_id=f"table_discovery_{int(time.time())}",
            config=self.config
        )
        
        tools = {
            "schema_lookup": SchemaLookupTool(self.explorer),
        }
        
        llm = create_llm(model="gpt-4o-mini")
        
        system_prompt = """
你是表发现专家，专门负责根据占位符查找相关的数据表。

任务：
1. 分析占位符中的关键词
2. 使用 schema_lookup 工具查找相关表
3. 评估表的匹配度
4. 返回最相关的表信息

规则：
- 仔细分析占位符中的业务关键词
- 查找包含相关字段的表
- 优先选择匹配度高的表
- 如果找不到直接匹配的表，查找相关表
"""
        
        return AgentExecutor(
            llm=llm,
            tools=tools,
            memory=None,
            unified_context=unified_context,
            max_iterations=3,
            system_instructions=system_prompt,
        )
    
    def _build_sql_generation_agent(self) -> AgentExecutor:
        """构建 SQL 生成代理"""
        unified_context = UnifiedExecutionContext(
            execution_id=f"sql_generation_{int(time.time())}",
            config=self.config
        )
        
        tools = {
            "doris_select": DorisSelectTool(self.explorer),
        }
        
        llm = create_llm(model="gpt-4o-mini")
        
        system_prompt = """
你是 SQL 生成专家，专门负责基于表结构和数据生成准确的 SQL。

任务：
1. 分析表结构和字段含义
2. 基于样例数据理解业务逻辑
3. 生成符合占位符要求的 SQL
4. 验证 SQL 的正确性

规则：
- 必须基于真实的表结构和数据
- 生成的 SQL 必须用 ```sql 代码块包裹
- 确保 SQL 语法正确
- 如果发现错误，要及时调整
"""
        
        return AgentExecutor(
            llm=llm,
            tools=tools,
            memory=None,
            unified_context=unified_context,
            max_iterations=5,
            system_instructions=system_prompt,
        )
    
    async def analyze_placeholder(self, placeholder: str) -> AnalysisResult:
        """分析单个占位符
        
        Args:
            placeholder: 占位符文本，如 "统计:退货渠道为App语音退货的退货单数量"
            
        Returns:
            AnalysisResult: 完整的分析结果
        """
        print(f"🔍 开始分析占位符: {placeholder}")
        
        result = AnalysisResult(placeholder=placeholder)
        
        try:
            # 阶段1: 表发现
            print("📊 阶段1: 表发现和结构分析")
            table_info = await self._discover_tables(placeholder)
            if not table_info:
                result.error_message = "未找到相关表"
                return result
            
            result.target_table = table_info.get("table")
            result.table_structure = table_info
            
            # 阶段2: 数据采样
            if self.analysis_config.enable_data_observation:
                print("🔍 阶段2: 数据采样和观察")
                sample_data = await self._sample_data(result.target_table, placeholder)
                result.sample_data = sample_data
            
            # 阶段3: SQL 生成
            print("🚀 阶段3: SQL 生成")
            sql = await self._generate_sql(placeholder, result.target_table, result.sample_data)
            result.generated_sql = sql
            
            # 阶段4: SQL 验证
            if self.analysis_config.enable_sql_validation and sql:
                print("✅ 阶段4: SQL 验证")
                query_result = await self._validate_sql(sql)
                result.query_result = query_result
            
            # 阶段5: 生成分析摘要
            result.analysis_summary = self._generate_analysis_summary(result)
            result.success = True
            
            print(f"🎉 占位符分析完成: {placeholder}")
            
        except Exception as e:
            result.error_message = str(e)
            result.success = False
            print(f"❌ 分析失败: {e}")
        
        # 记录分析历史
        self.analysis_history.append(result)
        
        return result
    
    async def _discover_tables(self, placeholder: str) -> Optional[Dict[str, Any]]:
        """发现相关表"""
        print(f"🔍 查找与占位符相关的表: {placeholder}")
        
        # 提取关键词
        keywords = self._extract_keywords(placeholder)
        print(f"📝 提取的关键词: {keywords}")
        
        # 使用表发现代理
        prompt = f"""
请查找与以下占位符相关的表：

占位符: {placeholder}
关键词: {', '.join(keywords)}

请使用 schema_lookup 工具查找相关表，并返回最匹配的表信息。
"""
        
        try:
            turn_state = TurnState.initial(max_iterations=3)
            context = ExecutionContext.create(correlation_id=f"table_discovery_{int(time.time())}")
            messages = [Message(role="user", content=prompt)]
            
            table_info = None
            
            async for event in self.table_discovery_agent.tt(messages, turn_state, context):
                if event.type == AgentEventType.TOOL_RESULT and event.tool_result:
                    if event.tool_result.tool_name == "schema_lookup":
                        try:
                            result_data = json.loads(event.tool_result.content)
                            candidates = result_data.get("candidates", [])
                            if candidates:
                                # 选择第一个候选表
                                table_info = candidates[0]
                                print(f"✅ 找到相关表: {table_info.get('table')}")
                                break
                        except json.JSONDecodeError:
                            continue
                
                elif event.type == AgentEventType.AGENT_FINISH:
                    break
                    
                elif event.type == AgentEventType.ERROR:
                    print(f"❌ 表发现错误: {event.error}")
                    break
            
            return table_info
            
        except Exception as e:
            print(f"❌ 表发现失败: {e}")
            return None
    
    async def _sample_data(self, table_name: str, placeholder: str) -> List[Dict[str, Any]]:
        """采样数据"""
        if not table_name:
            return []
        
        print(f"🔍 采样表 {table_name} 的数据")
        
        try:
            # 直接使用工具采样数据
            select_tool = DorisSelectTool(self.explorer)
            
            # 采样查询
            sample_queries = [
                f"SELECT * FROM {table_name} LIMIT {self.analysis_config.sample_data_limit}",
                f"SELECT COUNT(*) as total_count FROM {table_name}",
            ]
            
            sample_data = []
            
            for query in sample_queries:
                try:
                    result = await select_tool.run(sql=query, limit=self.analysis_config.sample_data_limit)
                    result_data = json.loads(result)
                    
                    if result_data.get("status") == "success":
                        rows = result_data.get("rows", [])
                        sample_data.extend(rows)
                        print(f"✅ 采样成功，获得 {len(rows)} 条记录")
                    else:
                        print(f"⚠️ 采样查询失败: {result_data.get('error')}")
                        
                except Exception as e:
                    print(f"❌ 采样查询异常: {e}")
                    continue
            
            return sample_data
            
        except Exception as e:
            print(f"❌ 数据采样失败: {e}")
            return []
    
    async def _generate_sql(self, placeholder: str, table_name: str, sample_data: List[Dict[str, Any]]) -> Optional[str]:
        """生成 SQL"""
        if not table_name:
            return None
        
        print(f"🚀 为占位符生成 SQL: {placeholder}")
        
        # 构建 SQL 生成提示
        sample_data_str = json.dumps(sample_data[:3], ensure_ascii=False, indent=2) if sample_data else "无样例数据"
        
        prompt = f"""
请为以下占位符生成 SQL：

占位符: {placeholder}
目标表: {table_name}
样例数据: {sample_data_str}

要求：
1. 基于真实的表结构和数据生成 SQL
2. 确保 SQL 语法正确
3. 使用 ```sql 代码块包裹最终 SQL
4. 返回字段名为 return_count

请生成准确的 SQL 查询。
"""
        
        try:
            turn_state = TurnState.initial(max_iterations=5)
            context = ExecutionContext.create(correlation_id=f"sql_generation_{int(time.time())}")
            messages = [Message(role="user", content=prompt)]
            
            generated_sql = None
            
            async for event in self.sql_generation_agent.tt(messages, turn_state, context):
                if event.type == AgentEventType.LLM_DELTA:
                    content = event.content or ""
                    if "```sql" in content.lower():
                        # 提取 SQL 代码块
                        lines = content.split('\n')
                        sql_lines = []
                        in_sql_block = False
                        
                        for line in lines:
                            if '```sql' in line.lower():
                                in_sql_block = True
                                continue
                            elif '```' in line and in_sql_block:
                                break
                            elif in_sql_block:
                                sql_lines.append(line)
                        
                        if sql_lines:
                            generated_sql = '\n'.join(sql_lines).strip()
                            print(f"✅ SQL 生成成功")
                            break
                
                elif event.type == AgentEventType.AGENT_FINISH:
                    break
                    
                elif event.type == AgentEventType.ERROR:
                    print(f"❌ SQL 生成错误: {event.error}")
                    break
            
            return generated_sql
            
        except Exception as e:
            print(f"❌ SQL 生成失败: {e}")
            return None
    
    async def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证 SQL"""
        if not sql:
            return {"error": "SQL 为空"}
        
        print(f"✅ 验证 SQL: {sql}")
        
        try:
            select_tool = DorisSelectTool(self.explorer)
            result = await select_tool.run(sql=sql, limit=10)
            
            result_data = json.loads(result)
            
            if result_data.get("status") == "success":
                print(f"✅ SQL 验证成功")
                return result_data
            else:
                print(f"❌ SQL 验证失败: {result_data.get('error')}")
                return result_data
                
        except Exception as e:
            print(f"❌ SQL 验证异常: {e}")
            return {"error": str(e)}
    
    def _extract_keywords(self, placeholder: str) -> List[str]:
        """提取占位符中的关键词"""
        # 移除占位符标记
        text = placeholder.replace("{{", "").replace("}}", "")
        
        # 分割并提取关键词
        keywords = []
        
        # 按冒号分割
        if ":" in text:
            parts = text.split(":")
            keywords.extend([part.strip() for part in parts])
        
        # 按空格分割
        words = text.split()
        keywords.extend([word.strip() for word in words if len(word.strip()) > 1])
        
        # 去重并过滤
        keywords = list(set([kw for kw in keywords if len(kw) > 1]))
        
        return keywords
    
    def _generate_analysis_summary(self, result: AnalysisResult) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        summary_parts.append(f"占位符: {result.placeholder}")
        
        if result.target_table:
            summary_parts.append(f"目标表: {result.target_table}")
        
        if result.generated_sql:
            summary_parts.append(f"生成 SQL: {result.generated_sql}")
        
        if result.query_result and result.query_result.get("status") == "success":
            rows = result.query_result.get("rows", [])
            if rows:
                summary_parts.append(f"查询结果: {rows[0]}")
        
        if result.success:
            summary_parts.append("状态: 分析成功")
        else:
            summary_parts.append(f"状态: 分析失败 - {result.error_message}")
        
        return "\n".join(summary_parts)
    
    async def analyze_template(self, template_path: Path) -> List[AnalysisResult]:
        """分析整个模板文件"""
        print(f"📄 分析模板文件: {template_path}")
        
        # 读取模板文件
        template_text = template_path.read_text(encoding="utf-8")
        
        # 解析占位符
        placeholders = self._parse_placeholders(template_text)
        
        print(f"🔍 发现 {len(placeholders)} 个占位符")
        
        # 分析每个占位符
        results = []
        for i, placeholder in enumerate(placeholders, 1):
            print(f"\n📊 分析占位符 {i}/{len(placeholders)}: {placeholder}")
            result = await self.analyze_placeholder(placeholder)
            results.append(result)
        
        return results
    
    def _parse_placeholders(self, template_text: str) -> List[str]:
        """解析模板中的占位符"""
        import re
        
        # 查找所有 {{...}} 格式的占位符
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_text)
        
        return [match.strip() for match in matches]


# 便捷函数
def create_autonomous_agent(
    explorer: DorisSchemaExplorer,
    config: Optional[SQLTemplateConfig] = None,
    analysis_config: Optional[AutonomousAnalysisConfig] = None,
) -> AutonomousSQLTemplateAgent:
    """创建自主 SQL 模板代理"""
    return AutonomousSQLTemplateAgent(
        explorer=explorer,
        config=config,
        analysis_config=analysis_config,
    )
