"""
工具注册表

管理可用工具的注册、发现和元数据
"""

import json
import time
import hashlib
import tempfile
import subprocess
import asyncio
import os
import signal
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import aiofiles
except ImportError:
    aiofiles = None

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
        
        if aiofiles is None:
            return {
                "action": action,
                "error": "aiofiles module not available",
                "success": False
            }
        path = input_data.get("path", ".")
        
        try:
            # 路径安全检查 - 在解析之前先检查原始路径
            if not self._is_safe_path_input(path):
                return {
                    "action": action,
                    "error": "Path not allowed for security reasons", 
                    "success": False
                }
            
            safe_path = Path(path).resolve()
            if not self._is_safe_path(safe_path):
                return {
                    "action": action,
                    "error": "Path not allowed for security reasons",
                    "success": False
                }
            
            if action == "list":
                # 真实的文件列表
                files = []
                directories = []
                
                if safe_path.exists() and safe_path.is_dir():
                    for item in safe_path.iterdir():
                        if item.is_file():
                            files.append({
                                "name": item.name,
                                "size": item.stat().st_size,
                                "modified": item.stat().st_mtime
                            })
                        elif item.is_dir():
                            directories.append({
                                "name": item.name,
                                "modified": item.stat().st_mtime
                            })
                
                return {
                    "action": "list",
                    "path": str(safe_path),
                    "files": files,
                    "directories": directories,
                    "success": True
                }
            
            elif action == "read":
                # 真实的文件读取
                if not safe_path.exists():
                    return {
                        "action": "read",
                        "path": str(safe_path),
                        "error": "File not found",
                        "success": False
                    }
                
                if not safe_path.is_file():
                    return {
                        "action": "read",
                        "path": str(safe_path),
                        "error": "Path is not a file",
                        "success": False
                    }
                
                try:
                    async with aiofiles.open(safe_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                except UnicodeDecodeError:
                    # 如果不是文本文件，读取为二进制
                    async with aiofiles.open(safe_path, 'rb') as f:
                        content_bytes = await f.read()
                        content = f"[Binary file, {len(content_bytes)} bytes]"
                
                return {
                    "action": "read",
                    "path": str(safe_path),
                    "content": content,
                    "size": safe_path.stat().st_size,
                    "success": True
                }
            
            elif action == "write":
                content = input_data.get("content", "")
                mode = input_data.get("mode", "w")  # w for write, a for append
                
                # 确保目录存在
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(safe_path, mode, encoding='utf-8') as f:
                    await f.write(content)
                
                return {
                    "action": "write",
                    "path": str(safe_path),
                    "bytes_written": len(content.encode('utf-8')),
                    "mode": mode,
                    "success": True
                }
            
            elif action == "delete":
                if not safe_path.exists():
                    return {
                        "action": "delete",
                        "path": str(safe_path),
                        "error": "File or directory not found",
                        "success": False
                    }
                
                if safe_path.is_file():
                    safe_path.unlink()
                elif safe_path.is_dir():
                    safe_path.rmdir()  # Only empty directories
                
                return {
                    "action": "delete",
                    "path": str(safe_path),
                    "success": True
                }
            
            elif action == "mkdir":
                safe_path.mkdir(parents=True, exist_ok=True)
                return {
                    "action": "mkdir",
                    "path": str(safe_path),
                    "success": True
                }
            
            else:
                raise ValueError(f"Unsupported action: {action}")
                
        except Exception as e:
            return {
                "action": action,
                "path": path,
                "error": str(e),
                "success": False
            }
    
    def _is_safe_path_input(self, path_str: str) -> bool:
        """检查原始路径输入是否安全"""
        # 检查路径遍历攻击模式
        if '..' in path_str:
            return False
        
        # 检查绝对路径到敏感目录
        if path_str.startswith('/etc') or path_str.startswith('/root') or path_str.startswith('/sys'):
            return False
        
        # 检查其他危险模式
        dangerous_patterns = ['~', '/dev', '/proc', '/bin', '/sbin']
        for pattern in dangerous_patterns:
            if pattern in path_str:
                return False
        
        return True
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否安全"""
        # 基本安全检查，防止路径遍历攻击
        try:
            # 获取当前工作目录
            cwd = Path.cwd()
            
            # 检查是否包含路径遍历模式
            path_str = str(path)
            if '..' in path_str or '~' in path_str:
                return False
            
            # 检查解析后的绝对路径
            resolved_path = path.resolve()
            resolved_str = str(resolved_path)
            
            # 检查是否包含危险模式
            dangerous_patterns = ['/etc', '/root', '/sys', '/proc', '/dev', '/bin', '/sbin', '/usr/bin', '/usr/sbin']
            for pattern in dangerous_patterns:
                if resolved_str.startswith(pattern):
                    return False
            
            # 检查路径是否在允许的范围内（工作目录或用户目录下）
            try:
                resolved_path.relative_to(cwd)
                return True
            except ValueError:
                # 如果不在工作目录下，检查是否在用户目录下
                try:
                    user_home = Path.home()
                    resolved_path.relative_to(user_home)
                    return True
                except ValueError:
                    # 路径不在允许的目录范围内
                    return False
            
        except (ValueError, OSError):
            # 路径解析失败或其他错误，认为不安全
            return False
    
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
        
        # 知识库存储路径
        kb_dir = Path("knowledge_bases") / kb_name
        
        try:
            if action == "search":
                query = input_data.get("query", "")
                limit = input_data.get("limit", 10)
                
                if not query.strip():
                    return {
                        "action": "search",
                        "kb_name": kb_name,
                        "query": query,
                        "error": "Query cannot be empty",
                        "success": False
                    }
                
                # 真实的文本搜索实现
                results = await self._search_knowledge_base(kb_dir, query, limit)
                
                return {
                    "action": "search",
                    "kb_name": kb_name,
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                    "success": True
                }
            
            elif action == "add":
                text = input_data.get("text", "")
                title = input_data.get("title", "")
                metadata = input_data.get("metadata", {})
                
                if not text.strip():
                    return {
                        "action": "add",
                        "kb_name": kb_name,
                        "error": "Text cannot be empty",
                        "success": False
                    }
                
                # 确保知识库目录存在
                kb_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成文档ID
                doc_id = hashlib.md5(f"{text}{title}{time.time()}".encode()).hexdigest()
                
                # 创建文档
                document = {
                    "id": doc_id,
                    "title": title or f"Document {doc_id[:8]}",
                    "text": text,
                    "metadata": metadata,
                    "created_at": datetime.now().isoformat(),
                    "word_count": len(text.split())
                }
                
                # 保存文档
                doc_file = kb_dir / f"{doc_id}.json"
                async with aiofiles.open(doc_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(document, ensure_ascii=False, indent=2))
                
                # 更新索引
                await self._update_index(kb_dir, document)
                
                return {
                    "action": "add",
                    "kb_name": kb_name,
                    "document_id": doc_id,
                    "title": document["title"],
                    "text_length": len(text),
                    "word_count": document["word_count"],
                    "success": True
                }
            
            elif action == "create":
                description = input_data.get("description", "")
                
                # 创建知识库目录
                kb_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建知识库元数据
                kb_metadata = {
                    "name": kb_name,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "document_count": 0,
                    "last_updated": datetime.now().isoformat()
                }
                
                metadata_file = kb_dir / "metadata.json"
                async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(kb_metadata, ensure_ascii=False, indent=2))
                
                # 创建空索引
                index_file = kb_dir / "index.json"
                if not index_file.exists():
                    async with aiofiles.open(index_file, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps({"documents": [], "terms": {}}, indent=2))
                
                return {
                    "action": "create",
                    "kb_name": kb_name,
                    "description": description,
                    "created": True,
                    "timestamp": kb_metadata["created_at"],
                    "success": True
                }
            
            elif action == "list":
                # 列出知识库中的文档
                if not kb_dir.exists():
                    return {
                        "action": "list",
                        "kb_name": kb_name,
                        "documents": [],
                        "total_count": 0,
                        "success": True
                    }
                
                documents = []
                for doc_file in kb_dir.glob("*.json"):
                    if doc_file.name == "metadata.json" or doc_file.name == "index.json":
                        continue
                    
                    try:
                        async with aiofiles.open(doc_file, 'r', encoding='utf-8') as f:
                            doc_content = await f.read()
                            doc = json.loads(doc_content)
                            documents.append({
                                "id": doc["id"],
                                "title": doc["title"],
                                "word_count": doc.get("word_count", 0),
                                "created_at": doc.get("created_at", ""),
                            })
                    except Exception:
                        continue
                
                return {
                    "action": "list",
                    "kb_name": kb_name,
                    "documents": documents,
                    "total_count": len(documents),
                    "success": True
                }
            
            else:
                raise ValueError(f"Unsupported action: {action}")
                
        except Exception as e:
            return {
                "action": action,
                "kb_name": kb_name,
                "error": str(e),
                "success": False
            }
    
    async def _search_knowledge_base(self, kb_dir: Path, query: str, limit: int) -> List[Dict[str, Any]]:
        """搜索知识库（简单的TF-IDF实现）"""
        if not kb_dir.exists():
            return []
        
        query_terms = set(query.lower().split())
        results = []
        
        # 遍历所有文档
        for doc_file in kb_dir.glob("*.json"):
            if doc_file.name in ["metadata.json", "index.json"]:
                continue
            
            try:
                async with aiofiles.open(doc_file, 'r', encoding='utf-8') as f:
                    doc_content = await f.read()
                    doc = json.loads(doc_content)
                
                # 计算相似度分数
                text = (doc.get("title", "") + " " + doc.get("text", "")).lower()
                text_terms = set(text.split())
                
                # 简单的相似度计算（Jaccard相似度）
                intersection = query_terms.intersection(text_terms)
                union = query_terms.union(text_terms)
                
                if union:
                    score = len(intersection) / len(union)
                    
                    if score > 0:  # 只返回有相关性的结果
                        results.append({
                            "id": doc["id"],
                            "title": doc.get("title", ""),
                            "text": doc.get("text", "")[:200] + "..." if len(doc.get("text", "")) > 200 else doc.get("text", ""),
                            "score": round(score, 3),
                            "created_at": doc.get("created_at", ""),
                            "metadata": doc.get("metadata", {})
                        })
            except Exception:
                continue
        
        # 按分数排序并限制结果数量
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    async def _update_index(self, kb_dir: Path, document: Dict[str, Any]):
        """更新知识库索引"""
        index_file = kb_dir / "index.json"
        
        try:
            if index_file.exists():
                async with aiofiles.open(index_file, 'r', encoding='utf-8') as f:
                    index_content = await f.read()
                    index = json.loads(index_content)
            else:
                index = {"documents": [], "terms": {}}
            
            # 添加文档到索引
            doc_summary = {
                "id": document["id"],
                "title": document["title"],
                "word_count": document["word_count"],
                "created_at": document["created_at"]
            }
            
            # 检查是否已存在
            existing_idx = None
            for i, existing_doc in enumerate(index["documents"]):
                if existing_doc["id"] == document["id"]:
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                index["documents"][existing_idx] = doc_summary
            else:
                index["documents"].append(doc_summary)
            
            # 简单的词汇索引
            text = (document["title"] + " " + document["text"]).lower()
            terms = set(text.split())
            
            for term in terms:
                if term not in index["terms"]:
                    index["terms"][term] = []
                if document["id"] not in index["terms"][term]:
                    index["terms"][term].append(document["id"])
            
            # 保存索引
            async with aiofiles.open(index_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index, ensure_ascii=False, indent=2))
                
        except Exception as e:
            # 索引更新失败不影响文档保存
            pass
    
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
        timeout = input_data.get("timeout", 30)  # 30秒超时
        
        if not code.strip():
            return {
                "language": language,
                "code": code,
                "error": "Code cannot be empty",
                "success": False
            }
        
        start_time = time.time()
        
        try:
            if language == "python":
                result = await self._execute_python(code, timeout)
            elif language == "javascript":
                result = await self._execute_javascript(code, timeout)
            elif language == "bash":
                result = await self._execute_bash(code, timeout)
            else:
                return {
                    "language": language,
                    "code": code,
                    "error": f"Unsupported language: {language}",
                    "success": False
                }
            
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 3)
            result["language"] = language
            result["code"] = code
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "language": language,
                "code": code,
                "error": str(e),
                "execution_time": round(execution_time, 3),
                "success": False
            }
    
    async def _execute_python(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行Python代码"""
        # 安全检查
        if self._contains_dangerous_python_code(code):
            return {
                "error": "Code contains potentially dangerous operations",
                "success": False
            }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 使用subprocess执行代码
            process = await asyncio.create_subprocess_exec(
                'python3', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024  # 1MB limit
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                stdout_text = stdout.decode('utf-8') if stdout else ""
                stderr_text = stderr.decode('utf-8') if stderr else ""
                
                return {
                    "output": stdout_text,
                    "error": stderr_text if stderr_text else None,
                    "return_code": process.returncode,
                    "success": process.returncode == 0
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "error": f"Code execution timed out after {timeout} seconds",
                    "success": False
                }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _execute_javascript(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行JavaScript代码"""
        # 安全检查
        if self._contains_dangerous_js_code(code):
            return {
                "error": "Code contains potentially dangerous operations",
                "success": False
            }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 使用node执行代码
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                stdout_text = stdout.decode('utf-8') if stdout else ""
                stderr_text = stderr.decode('utf-8') if stderr else ""
                
                return {
                    "output": stdout_text,
                    "error": stderr_text if stderr_text else None,
                    "return_code": process.returncode,
                    "success": process.returncode == 0
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "error": f"Code execution timed out after {timeout} seconds",
                    "success": False
                }
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _execute_bash(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行Bash代码"""
        # 安全检查
        if self._contains_dangerous_bash_code(code):
            return {
                "error": "Code contains potentially dangerous operations",
                "success": False
            }
        
        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                stdout_text = stdout.decode('utf-8') if stdout else ""
                stderr_text = stderr.decode('utf-8') if stderr else ""
                
                return {
                    "output": stdout_text,
                    "error": stderr_text if stderr_text else None,
                    "return_code": process.returncode,
                    "success": process.returncode == 0
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "error": f"Code execution timed out after {timeout} seconds",
                    "success": False
                }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def _contains_dangerous_python_code(self, code: str) -> bool:
        """检查Python代码是否包含危险操作"""
        dangerous_patterns = [
            'import os', '__import__', 'exec(', 'eval(',
            'subprocess', 'system(', 'open(', 'file(',
            'input(', 'raw_input(', 'compile(',
            'globals(', 'locals(', 'vars(',
            'delattr', 'setattr', 'getattr',
            'remove', 'rmdir', 'unlink'
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return True
        return False
    
    def _contains_dangerous_js_code(self, code: str) -> bool:
        """检查JavaScript代码是否包含危险操作"""
        dangerous_patterns = [
            'require(', 'process', 'fs.', 'child_process',
            'eval(', 'Function(', 'setTimeout(', 'setInterval(',
            'global.', 'window.', 'document.',
            'XMLHttpRequest', 'fetch('
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return True
        return False
    
    def _contains_dangerous_bash_code(self, code: str) -> bool:
        """检查Bash代码是否包含危险操作"""
        dangerous_patterns = [
            'rm -rf', 'sudo', 'su ', 'chmod',
            'curl', 'wget', 'nc ', 'netcat',
            '/etc/', '/root/', '/sys/', '/proc/',
            '$(', '`', 'dd ', 'mkfs',
            'format', 'fdisk', 'mount', 'umount'
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return True
        return False
    
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