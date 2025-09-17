"""
工具注册表

管理可用工具的注册、发现和元数据
"""

import json
import time
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from ...types import ToolSafetyLevel


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any] = field(default_factory=dict)
    safety_level: ToolSafetyLevel = ToolSafetyLevel.CAUTIOUS
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行相关
    executor_class: Optional[str] = None
    timeout: float = 30.0
    retry_attempts: int = 3
    
    # 性能指标
    average_execution_time: float = 0.0
    success_rate: float = 1.0
    usage_count: int = 0


@dataclass
class ToolUsageMetrics:
    """工具使用指标"""
    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_used: Optional[datetime] = None
    error_types: Dict[str, int] = field(default_factory=dict)


class BaseTool(ABC):
    """基础工具接口"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.usage_metrics = ToolUsageMetrics(tool_name=name)
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """获取输入模式"""
        pass
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出模式"""
        return {"type": "object", "properties": {"result": {"type": "object"}}}
    
    def get_safety_level(self) -> ToolSafetyLevel:
        """获取安全级别"""
        return ToolSafetyLevel.CAUTIOUS
    
    def get_capabilities(self) -> List[str]:
        """获取工具能力"""
        return []
    
    def get_dependencies(self) -> List[str]:
        """获取依赖"""
        return []
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        # 简化验证，实际应该根据schema进行完整验证
        schema = self.get_input_schema()
        required_fields = schema.get("required", [])
        
        for field in required_fields:
            if field not in input_data:
                return False
        
        return True
    
    def update_metrics(self, execution_time: float, success: bool, error_type: str = None):
        """更新使用指标"""
        
        self.usage_metrics.total_calls += 1
        self.usage_metrics.total_execution_time += execution_time
        self.usage_metrics.last_used = datetime.now()
        
        if success:
            self.usage_metrics.successful_calls += 1
        else:
            self.usage_metrics.failed_calls += 1
            if error_type:
                if error_type not in self.usage_metrics.error_types:
                    self.usage_metrics.error_types[error_type] = 0
                self.usage_metrics.error_types[error_type] += 1
        
        # 更新平均执行时间
        if self.usage_metrics.total_calls > 0:
            self.usage_metrics.average_execution_time = (
                self.usage_metrics.total_execution_time / self.usage_metrics.total_calls
            )


class FileSystemTool(BaseTool):
    """文件系统工具"""
    
    def __init__(self):
        super().__init__(
            name="file_system",
            description="文件系统操作工具，支持读取、写入、列表等操作"
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件系统操作"""
        
        action = input_data.get("action")
        path = input_data.get("path", ".")
        
        if action == "list":
            # 模拟文件列表
            return {
                "action": "list",
                "path": path,
                "files": ["example1.txt", "example2.py", "example3.md"],
                "directories": ["subfolder1", "subfolder2"]
            }
        elif action == "read":
            # 模拟文件读取
            return {
                "action": "read", 
                "path": path,
                "content": f"Content of file {path}",
                "size": 1024
            }
        elif action == "write":
            content = input_data.get("content", "")
            return {
                "action": "write",
                "path": path,
                "bytes_written": len(content),
                "success": True
            }
        else:
            raise ValueError(f"Unsupported action: {action}")
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "read", "write", "delete", "mkdir"]
                },
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["action", "path"]
        }
    
    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.CAUTIOUS  # 文件操作需要谨慎
    
    def get_capabilities(self) -> List[str]:
        return ["file_operations", "data_persistence", "content_management"]


class KnowledgeBaseTool(BaseTool):
    """知识库工具"""
    
    def __init__(self):
        super().__init__(
            name="knowledge_base",
            description="知识库操作工具，支持搜索、添加、创建知识库"
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行知识库操作"""
        
        action = input_data.get("action")
        kb_name = input_data.get("kb_name", "default")
        
        if action == "search":
            query = input_data.get("query", "")
            return {
                "action": "search",
                "kb_name": kb_name,
                "query": query,
                "results": [
                    {"id": "doc1", "title": "相关文档1", "score": 0.95},
                    {"id": "doc2", "title": "相关文档2", "score": 0.87}
                ],
                "total_results": 2
            }
        elif action == "add":
            text = input_data.get("text", "")
            return {
                "action": "add",
                "kb_name": kb_name,
                "document_id": f"doc_{int(time.time())}",
                "text_length": len(text),
                "success": True
            }
        elif action == "create":
            return {
                "action": "create",
                "kb_name": kb_name,
                "created": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise ValueError(f"Unsupported action: {action}")
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string", 
                    "enum": ["search", "add", "create", "delete"]
                },
                "kb_name": {"type": "string"},
                "query": {"type": "string"},
                "text": {"type": "string"}
            },
            "required": ["action", "kb_name"]
        }
    
    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE  # 知识库操作相对安全
    
    def get_capabilities(self) -> List[str]:
        return ["knowledge_retrieval", "information_search", "data_storage"]


class CodeInterpreterTool(BaseTool):
    """代码解释器工具"""
    
    def __init__(self):
        super().__init__(
            name="code_interpreter",
            description="代码执行工具，支持Python、JavaScript等语言"
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码"""
        
        language = input_data.get("language", "python")
        code = input_data.get("code", "")
        
        # 模拟代码执行
        if language == "python":
            return {
                "language": "python",
                "code": code,
                "output": "Code execution result",
                "execution_time": 0.5,
                "success": True
            }
        elif language == "javascript":
            return {
                "language": "javascript", 
                "code": code,
                "output": "JS execution result",
                "execution_time": 0.3,
                "success": True
            }
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash", "sql"]
                },
                "code": {"type": "string"},
                "timeout": {"type": "number", "default": 30}
            },
            "required": ["language", "code"]
        }
    
    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.EXCLUSIVE  # 代码执行需要独占
    
    def get_capabilities(self) -> List[str]:
        return ["code_execution", "data_processing", "computation"]


class WebSearchTool(BaseTool):
    """网络搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="网络搜索工具，获取最新信息"
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行网络搜索"""
        
        query = input_data.get("query", "")
        max_results = input_data.get("max_results", 5)
        
        # 模拟搜索结果
        return {
            "query": query,
            "max_results": max_results,
            "results": [
                {
                    "title": f"搜索结果 {i+1}",
                    "url": f"https://example.com/result{i+1}",
                    "snippet": f"关于 {query} 的相关信息 {i+1}"
                }
                for i in range(min(max_results, 3))
            ],
            "total_found": max_results,
            "search_time": 0.8
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                "language": {"type": "string", "default": "zh-CN"}
            },
            "required": ["query"]
        }
    
    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE  # 搜索操作安全
    
    def get_capabilities(self) -> List[str]:
        return ["web_search", "information_retrieval", "real_time_data"]


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self.categories: Dict[str, Set[str]] = {}
        self.capability_index: Dict[str, Set[str]] = {}
        
        # 注册默认工具
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        
        default_tools = [
            FileSystemTool(),
            KnowledgeBaseTool(),
            CodeInterpreterTool(),
            WebSearchTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool, category: str = "general") -> bool:
        """注册工具"""
        
        try:
            # 检查工具名称冲突
            if tool.name in self.tools:
                raise ValueError(f"Tool {tool.name} already registered")
            
            # 注册工具实例
            self.tools[tool.name] = tool
            
            # 创建工具定义
            tool_definition = ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.get_input_schema(),
                output_schema=tool.get_output_schema(),
                safety_level=tool.get_safety_level(),
                capabilities=tool.get_capabilities(),
                dependencies=tool.get_dependencies()
            )
            
            self.tool_definitions[tool.name] = tool_definition
            
            # 更新分类索引
            if category not in self.categories:
                self.categories[category] = set()
            self.categories[category].add(tool.name)
            
            # 更新能力索引
            for capability in tool.get_capabilities():
                if capability not in self.capability_index:
                    self.capability_index[capability] = set()
                self.capability_index[capability].add(tool.name)
            
            return True
            
        except Exception as e:
            print(f"Failed to register tool {tool.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        
        if tool_name not in self.tools:
            return False
        
        # 从所有索引中移除
        tool = self.tools[tool_name]
        
        # 移除能力索引
        for capability in tool.get_capabilities():
            if capability in self.capability_index:
                self.capability_index[capability].discard(tool_name)
                if not self.capability_index[capability]:
                    del self.capability_index[capability]
        
        # 移除分类索引
        for category, tools in self.categories.items():
            tools.discard(tool_name)
        
        # 移除主要注册
        del self.tools[tool_name]
        del self.tool_definitions[tool_name]
        
        return True
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self.tools.get(tool_name)
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self.tool_definitions.get(tool_name)
    
    def list_tools(self, category: str = None, 
                   capability: str = None,
                   safety_level: ToolSafetyLevel = None) -> List[str]:
        """列出工具"""
        
        all_tools = set(self.tools.keys())
        
        # 按分类过滤
        if category:
            category_tools = self.categories.get(category, set())
            all_tools = all_tools.intersection(category_tools)
        
        # 按能力过滤
        if capability:
            capability_tools = self.capability_index.get(capability, set())
            all_tools = all_tools.intersection(capability_tools)
        
        # 按安全级别过滤
        if safety_level:
            safety_tools = {
                name for name, definition in self.tool_definitions.items()
                if definition.safety_level == safety_level
            }
            all_tools = all_tools.intersection(safety_tools)
        
        return list(all_tools)
    
    def find_tools_by_capabilities(self, required_capabilities: List[str]) -> List[str]:
        """根据能力查找工具"""
        
        if not required_capabilities:
            return list(self.tools.keys())
        
        # 找到满足所有能力要求的工具
        matching_tools = None
        
        for capability in required_capabilities:
            capability_tools = self.capability_index.get(capability, set())
            
            if matching_tools is None:
                matching_tools = capability_tools.copy()
            else:
                matching_tools = matching_tools.intersection(capability_tools)
        
        return list(matching_tools) if matching_tools else []
    
    def get_tool_metrics(self, tool_name: str) -> Optional[ToolUsageMetrics]:
        """获取工具使用指标"""
        
        tool = self.tools.get(tool_name)
        return tool.usage_metrics if tool else None
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        
        total_tools = len(self.tools)
        
        # 按安全级别统计
        safety_distribution = {}
        for definition in self.tool_definitions.values():
            level = definition.safety_level.value
            safety_distribution[level] = safety_distribution.get(level, 0) + 1
        
        # 按分类统计
        category_distribution = {
            category: len(tools) 
            for category, tools in self.categories.items()
        }
        
        # 使用统计
        usage_stats = {}
        total_calls = 0
        total_successful_calls = 0
        
        for tool_name, tool in self.tools.items():
            metrics = tool.usage_metrics
            usage_stats[tool_name] = {
                "total_calls": metrics.total_calls,
                "success_rate": (
                    metrics.successful_calls / metrics.total_calls 
                    if metrics.total_calls > 0 else 0
                ),
                "average_execution_time": metrics.average_execution_time
            }
            total_calls += metrics.total_calls
            total_successful_calls += metrics.successful_calls
        
        overall_success_rate = (
            total_successful_calls / total_calls 
            if total_calls > 0 else 0
        )
        
        return {
            "total_tools": total_tools,
            "safety_distribution": safety_distribution,
            "category_distribution": category_distribution,
            "overall_success_rate": overall_success_rate,
            "total_tool_calls": total_calls,
            "usage_stats": usage_stats,
            "available_capabilities": list(self.capability_index.keys())
        }
    
    def export_tool_definitions(self) -> Dict[str, Any]:
        """导出工具定义"""
        
        return {
            "tools": {
                name: {
                    "name": definition.name,
                    "description": definition.description,
                    "input_schema": definition.input_schema,
                    "output_schema": definition.output_schema,
                    "safety_level": definition.safety_level.value,
                    "capabilities": definition.capabilities,
                    "dependencies": definition.dependencies
                }
                for name, definition in self.tool_definitions.items()
            },
            "categories": {
                category: list(tools) 
                for category, tools in self.categories.items()
            },
            "capability_index": {
                capability: list(tools)
                for capability, tools in self.capability_index.items()
            }
        }
    
    async def validate_tool_dependencies(self, tool_name: str) -> Dict[str, Any]:
        """验证工具依赖"""
        
        definition = self.tool_definitions.get(tool_name)
        if not definition:
            return {"valid": False, "error": "Tool not found"}
        
        missing_dependencies = []
        for dependency in definition.dependencies:
            if dependency not in self.tools:
                missing_dependencies.append(dependency)
        
        return {
            "valid": len(missing_dependencies) == 0,
            "dependencies": definition.dependencies,
            "missing_dependencies": missing_dependencies,
            "tool_name": tool_name
        }