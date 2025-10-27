"""上下文组装逻辑。

基于 Loom 0.0.3 重构模式，优化上下文管理和配置。
"""

from __future__ import annotations

import json
import textwrap
from typing import Dict, Iterable, List, Optional

from loom.core.context_assembly import ComponentPriority, ContextAssembler

from .config import ACCEPTANCE_CRITERIA, TASK_INSTRUCTION, SQLTemplateConfig
from .metadata import TableInfo


def parse_placeholders(template_text: str) -> List[Dict[str, str]]:
    """从模板中解析出占位符与描述。

    支持形如 ``{{统计：总销售额}}`` 或 ``{{统计:总销售额}}`` 的格式。
    """
    import re

    pattern = re.compile(
        r"{{\s*(?P<category>[^：:{}]+)\s*[：:]\s*(?P<description>[^{}]+?)\s*}}"
    )
    placeholders = []
    for match in pattern.finditer(template_text):
        category = match.group("category").strip()
        description = match.group("description").strip()
        placeholders.append(
            {
                "category": category,
                "description": description,
                "placeholder": f"{category}:{description}",
            }
        )
    return placeholders


def _format_schema_snapshot(
    schema: Dict[str, TableInfo], 
    config: Optional[SQLTemplateConfig] = None
) -> str:
    """将 Doris 表结构格式化成紧凑文本，以便写入上下文。
    
    基于 Loom 0.0.3 重构模式，使用配置管理显示数量。
    """
    if config is None:
        config = SQLTemplateConfig()
    
    lines: List[str] = []
    max_tables = config.max_schema_tables
    max_columns = config.max_table_columns
    
    for index, (table_name, table_info) in enumerate(schema.items()):
        if index >= max_tables:
            remaining = len(schema) - max_tables
            lines.append(f"...（剩余 {remaining} 张表已省略）")
            break

        comment = table_info.comment or "（无备注）"
        lines.append(f"表：{table_name} -- {comment}")
        for column in table_info.columns[:max_columns]:
            col_comment = column.comment or ""
            lines.append(
                f"  - {column.name} ({column.data_type}) {col_comment}"
            )
        if len(table_info.columns) > max_columns:
            lines.append(f"  ...（该表共 {len(table_info.columns)} 个字段）")
    return "\n".join(lines)


def build_coordinator_prompt(
    *,
    template_text: str,
    placeholders: Iterable[Dict[str, str]],
    schema_snapshot: Dict[str, TableInfo],
    data_source_summary: Dict[str, str],
    config: Optional[SQLTemplateConfig] = None,
) -> str:
    """组装发送给主 Agent 的用户消息。
    
    基于 Loom 0.0.3 重构模式，使用配置管理上下文大小。
    """
    if config is None:
        config = SQLTemplateConfig()
    
    assembler = ContextAssembler(max_tokens=16000)

    assembler.add_component(
        name="task_instruction",
        content=TASK_INSTRUCTION,
        priority=ComponentPriority.CRITICAL,
        truncatable=False,
    )

    assembler.add_component(
        name="template_text",
        content=textwrap.dedent(
            f"""\
            旅游业务分析模板如下（请识别所有占位符）：

            <<REPORT_TEMPLATE>>
            {template_text.strip()}
            <<END_TEMPLATE>>
            """
        ),
        priority=ComponentPriority.CRITICAL,
        truncatable=False,
    )

    assembler.add_component(
        name="placeholder_list",
        content=json.dumps(list(placeholders), ensure_ascii=False, indent=2),
        priority=ComponentPriority.HIGH,
        truncatable=False,
    )

    assembler.add_component(
        name="data_source",
        content=json.dumps(data_source_summary, ensure_ascii=False, indent=2),
        priority=ComponentPriority.HIGH,
        truncatable=False,
    )

    assembler.add_component(
        name="schema_snapshot",
        content=_format_schema_snapshot(schema_snapshot, config),
        priority=ComponentPriority.MEDIUM,
        truncatable=True,
    )

    assembler.add_component(
        name="acceptance_criteria",
        content="\n".join(f"- {item}" for item in ACCEPTANCE_CRITERIA),
        priority=ComponentPriority.MEDIUM,
        truncatable=False,
    )

    assembler.add_component(
        name="response_guidance",
        content=(
            "请输出最终 SQL（使用 ```sql 代码块包裹），并附上字段与占位符之间的映射说明。"
            "建议在 SQL 生成前先使用 schema_lookup 了解表结构，必要时通过 doris_select "
            f"执行验证查询（限制 {config.max_query_limit} 行以内）。"
        ),
        priority=ComponentPriority.OPTIONAL,
        truncatable=True,
    )

    return assembler.assemble()


def build_placeholder_agent_prompt(
    *,
    placeholder: Dict[str, str],
    template_text: str,
) -> str:
    """生成传递给占位符子代理的提示语。"""
    return textwrap.dedent(
        f"""\
        你负责分析单个占位符，并输出推荐的数据来源与 SQL 片段。

        当前占位符：
        {json.dumps(placeholder, ensure_ascii=False, indent=2)}

        模板全文：
        {template_text.strip()}

        输出请使用 JSON，包含字段：
          - placeholder: 占位符名称
          - table: 推荐的主表
          - columns: 涉及的字段列表
          - expressions: 计算表达式（若需要聚合）
          - sql_snippet: 可组合进最终查询的 SELECT 片段
          - notes: 决策说明
        """
    )

