"""配置与常量定义。

该模块集中管理 SQL 模板路径、数据源信息以及任务说明，便于示例在
不同环境下快速调整。基于 Loom 0.0.3 重构模式，使用 CoordinationConfig
进行统一配置管理。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, List

from loom.core.unified_coordination import CoordinationConfig


BASE_DIR: Final[Path] = Path(__file__).resolve().parent
TEMPLATE_PATH: Final[Path] = BASE_DIR.parent / "模板.md"


@dataclass(frozen=True)
class DorisConnectionConfig:
    """Doris 数据源连接信息。"""

    hosts: List[str]
    http_port: int
    mysql_port: int
    database: str
    user: str
    password: str
    connect_timeout: int = 10

    @property
    def primary_host(self) -> str:
        return self.hosts[0]


@dataclass(frozen=True)
class SQLTemplateConfig:
    """SQL 模板代理专用配置类，基于 Loom 0.0.3 CoordinationConfig 模式。"""
    
    # 基础协调配置
    deep_recursion_threshold: int = 5
    """深度递归阈值 - SQL 分析可能需要更深的递归"""
    
    high_complexity_threshold: float = 0.8
    """高复杂度阈值 - SQL 模板分析复杂度较高"""
    
    context_cache_size: int = 200
    """上下文组件缓存大小 - SQL 分析需要更多上下文"""
    
    event_batch_size: int = 15
    """事件批处理大小 - SQL 分析产生更多事件"""
    
    event_batch_timeout: float = 0.03
    """事件批处理超时 - 降低延迟到 30ms"""
    
    subagent_pool_size: int = 8
    """子代理池大小 - SQL 分析可能需要多个子代理"""
    
    # SQL 模板专用配置
    max_schema_tables: int = 12
    """最大显示表数量 - 控制上下文大小"""
    
    max_table_columns: int = 12
    """最大显示字段数量 - 控制上下文大小"""
    
    max_query_limit: int = 200
    """最大查询行数限制 - 防止大结果集"""
    
    max_iterations: int = 15
    """最大迭代次数 - SQL 分析需要更多迭代"""
    
    schema_cache_ttl: int = 300
    """模式缓存 TTL（秒）- 5分钟缓存"""
    
    query_timeout: int = 30
    """查询超时时间（秒）"""
    
    max_execution_time: int = 300
    """最大执行时间（秒）- 5分钟"""
    
    max_token_usage: int = 50000
    """最大 token 使用量"""
    
    min_cache_hit_rate: float = 0.8
    """最小缓存命中率"""
    
    max_subagent_count: int = 5
    """最大子代理数量"""
    
    # 自主分析配置
    enable_autonomous_analysis: bool = True
    """启用自主分析模式"""
    
    max_table_discovery_attempts: int = 3
    """最大表发现尝试次数"""
    
    max_sample_queries: int = 5
    """最大数据采样查询次数"""
    
    sample_data_limit: int = 10
    """数据采样限制"""
    
    enable_data_observation: bool = True
    """启用数据观察功能"""
    
    enable_sql_validation: bool = True
    """启用 SQL 验证功能"""
    
    analysis_timeout: int = 300
    """分析超时时间（秒）"""


# 默认配置实例
DEFAULT_SQL_CONFIG = SQLTemplateConfig()

# 自主分析专用配置
AUTONOMOUS_ANALYSIS_CONFIG = SQLTemplateConfig(
    max_iterations=20,
    max_table_discovery_attempts=5,
    max_sample_queries=8,
    sample_data_limit=15,
    enable_data_observation=True,
    enable_sql_validation=True,
    analysis_timeout=600,
)

DATA_SOURCE = DorisConnectionConfig(
    hosts=["192.168.61.30"],
    http_port=8030,
    mysql_port=9030,
    database="yjg",
    user="root",
    password="yjg@123456",
)

REPORT_TABLE = "ods_itinerary"
REPORT_TABLE_ALIAS = "itinerary"


TASK_INSTRUCTION = (
    "请基于旅游业务分析模板生成一份可以直接运行的 SQL。SQL 需要返回每个占位符"
    "所需的数据字段，字段命名应与占位符语义一致（例如 total_itinerary_count）。"
    "如果为无法直接计算的图表占位符，可以输出用于绘制图表的数据列。"
)

ACCEPTANCE_CRITERIA = [
    "只允许执行只读 SQL（SELECT）；禁止修改或删除数据。",
    "优先使用 yjg 库中现有的旅游相关表，例如 ods_itinerary、ods_guide、ods_complain 等。",
    "结果列应覆盖模板中的所有占位符，并提供必要的别名便于后续替换。",
]
