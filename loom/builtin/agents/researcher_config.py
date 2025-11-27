"""研究员agent配置"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any

from loom.interfaces.agent import AgentConfig
from loom.builtin.tools import ExaSearchTool


class ResearcherAgentConfig(AgentConfig):
    """研究员agent配置"""
    model: str = Field(default="qwen-turbo", description="模型名称")
    exa_api_key: str = Field(default="974916d1-902a", description="Exa API密钥")
    max_search_rounds: int = Field(default=3, description="最大搜索轮数")
    max_results_per_search: int = Field(default=5, description="每次搜索的最大结果数")

    @classmethod
    def create_default(cls) -> "ResearcherAgentConfig":
        """创建默认配置"""
        return cls(
            name="researcher_agent",
            description="研究员子agent，支持搜索-反思循环逻辑，用于深入研究特定主题",
            model="qwen-turbo",
            exa_api_key="974916d1-902a",
            max_search_rounds=3,
            max_results_per_search=5
        )

    def get_tools(self) -> List[Any]:
        """获取工具列表"""
        return [
            ExaSearchTool(api_key=self.exa_api_key)
        ]

    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return {
            "model": self.model,
            "temperature": 0.7,
            "max_tokens": 2048
        }