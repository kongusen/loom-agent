"""
自定义LLM API提供者

用于连接用户提供的LLM API服务
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, AsyncIterator

from .base import BaseLLMProvider, LLMResponse, LLMStreamChunk


class CustomLLMProvider(BaseLLMProvider):
    """自定义LLM API提供者"""
    
    def __init__(self, 
                 api_base: str,
                 api_key: Optional[str] = None,
                 model: str = "custom-model",
                 timeout: int = 60,
                 max_retries: int = 3,
                 **kwargs):
        """
        初始化自定义LLM提供者
        
        Args:
            api_base: API基础URL
            api_key: API密钥（如果需要）
            model: 模型名称
            timeout: 请求超时时间
            max_retries: 最大重试次数
        """
        super().__init__(api_key=api_key, api_base=api_base, model=model, **kwargs)
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.CustomLLMProvider")
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _make_request(self, 
                          endpoint: str,
                          data: Dict[str, Any],
                          stream: bool = False) -> aiohttp.ClientResponse:
        """发起HTTP请求"""
        await self._ensure_session()
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        url = f"{self.api_base.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making request to {url}, attempt {attempt + 1}")
                
                response = await self.session.post(
                    url,
                    headers=headers,
                    json=data
                )
                
                if response.status == 200:
                    return response
                else:
                    error_text = await response.text()
                    self.logger.warning(f"Request failed with status {response.status}: {error_text}")
                    
                    if attempt == self.max_retries - 1:
                        raise aiohttp.ClientError(f"Request failed with status {response.status}")
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"Request timeout, attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise
                    
            except Exception as e:
                self.logger.warning(f"Request error: {e}, attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise
                    
            # 等待后重试
            await asyncio.sleep(1 * (attempt + 1))
        
        raise aiohttp.ClientError("Max retries exceeded")
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息为API兼容格式"""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        return formatted
    
    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """格式化工具为API兼容格式"""
        if not tools:
            return None
            
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                }
            })
        return formatted
    
    async def generate_response(self, 
                              messages: List[Dict[str, str]],
                              tools: Optional[List[Dict[str, Any]]] = None,
                              stream: bool = False,
                              **kwargs) -> LLMResponse:
        """生成完整响应"""
        
        # 构建请求数据
        request_data = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "stream": False,
            **kwargs
        }
        
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            request_data["tools"] = formatted_tools
            request_data["tool_choice"] = "auto"
        
        self.logger.info(f"Generating response with model {self.model}")
        
        try:
            response = await self._make_request("chat/completions", request_data)
            response_data = await response.json()
            
            # 解析响应
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("No choices in response")
            
            choice = choices[0]
            message = choice.get("message", {})
            
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                usage=response_data.get("usage"),
                model=response_data.get("model"),
                finish_reason=choice.get("finish_reason"),
                metadata={
                    "response_id": response_data.get("id"),
                    "created": response_data.get("created")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise
    
    async def generate_stream(self,
                            messages: List[Dict[str, str]], 
                            tools: Optional[List[Dict[str, Any]]] = None,
                            **kwargs) -> AsyncIterator[LLMStreamChunk]:
        """生成流式响应"""
        
        # 构建请求数据
        request_data = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "stream": True,
            **kwargs
        }
        
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            request_data["tools"] = formatted_tools
            request_data["tool_choice"] = "auto"
        
        self.logger.info(f"Generating stream with model {self.model}")
        
        try:
            await self._ensure_session()
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/plain"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            
            async with self.session.post(url, headers=headers, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"Stream request failed: {error_text}")
                
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # 保留最后一行未完成的数据
                    
                    for line in lines[:-1]:
                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            continue
                            
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # 移除 "data: " 前缀
                                
                                choices = data.get("choices", [])
                                if not choices:
                                    continue  # 跳过没有choices的数据块
                                
                                choice = choices[0]
                                delta = choice.get("delta", {})
                                
                                # 处理内容块
                                if "content" in delta and delta["content"]:
                                    yield LLMStreamChunk(
                                        content=delta["content"],
                                        chunk_type="text",
                                        metadata={"choice_index": choice.get("index", 0)}
                                    )
                                
                                # 处理工具调用
                                if "tool_calls" in delta:
                                    for tool_call in delta["tool_calls"]:
                                        yield LLMStreamChunk(
                                            content=json.dumps(tool_call),
                                            chunk_type="tool_call",
                                            metadata={
                                                "tool_call_id": tool_call.get("id"),
                                                "function_name": tool_call.get("function", {}).get("name")
                                            }
                                        )
                                
                                # 检查是否结束
                                if choice.get("finish_reason"):
                                    yield LLMStreamChunk(
                                        content="",
                                        chunk_type="finish",
                                        metadata={"finish_reason": choice["finish_reason"]},
                                        is_final=True
                                    )
                                    break
                                    
                            except json.JSONDecodeError as e:
                                self.logger.warning(f"Failed to parse stream chunk: {line}, error: {e}")
                                continue
                
        except Exception as e:
            self.logger.error(f"Error in stream generation: {e}")
            # 发送错误块
            yield LLMStreamChunk(
                content=f"Error: {str(e)}",
                chunk_type="error",
                metadata={"error_type": type(e).__name__},
                is_final=True
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 发送简单的健康检查请求
            test_messages = [{"role": "user", "content": "ping"}]
            
            start_time = asyncio.get_event_loop().time()
            response = await self.generate_response(test_messages)
            end_time = asyncio.get_event_loop().time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            return {
                "status": "healthy",
                "health_score": 1.0,
                "response_time_ms": response_time,
                "model": self.model,
                "api_base": self.api_base,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy", 
                "health_score": 0.0,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()