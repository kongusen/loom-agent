"""
LLM 提供者基础接口

定义所有LLM提供者需要实现的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMStreamChunk:
    """LLM流式响应块"""
    content: str
    chunk_type: str = "text"  # text, tool_call, function_call, etc.
    metadata: Optional[Dict[str, Any]] = None
    is_final: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass 
class LLMResponse:
    """LLM完整响应"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """LLM提供者基础类"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 api_base: Optional[str] = None,
                 model: str = "default",
                 **kwargs):
        self.api_key = api_key
        self.api_base = api_base  
        self.model = model
        self.config = kwargs
        
    @abstractmethod
    async def generate_response(self, 
                              messages: List[Dict[str, str]],
                              tools: Optional[List[Dict[str, Any]]] = None,
                              stream: bool = False,
                              **kwargs) -> LLMResponse:
        """生成响应"""
        pass
        
    @abstractmethod
    async def generate_stream(self,
                            messages: List[Dict[str, str]], 
                            tools: Optional[List[Dict[str, Any]]] = None,
                            **kwargs) -> AsyncIterator[LLMStreamChunk]:
        """生成流式响应"""
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
        
    async def count_tokens(self, text: str) -> int:
        """计算token数量（可选实现）"""
        # 简单估算，实际实现应该使用具体的tokenizer
        return len(text.split()) * 1.3  # 粗略估算
        
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model": self.model,
            "provider": self.__class__.__name__,
            "api_base": self.api_base
        }