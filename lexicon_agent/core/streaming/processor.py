"""
流式处理器

实现流式数据处理和实时响应，类似Claude Code的流式架构
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from ...types import AgentEvent, AgentEventType

T = TypeVar('T')


@dataclass
class StreamChunk(Generic[T]):
    """流式数据块"""
    chunk_id: str
    data: T
    chunk_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 流控制
    is_final: bool = False
    sequence_number: int = 0
    total_chunks: Optional[int] = None


@dataclass
class StreamMetrics:
    """流式指标"""
    stream_id: str
    start_time: datetime
    total_chunks: int = 0
    processed_chunks: int = 0
    bytes_processed: int = 0
    processing_rate: float = 0.0  # chunks/second
    throughput: float = 0.0  # bytes/second
    latency_ms: float = 0.0
    error_count: int = 0


class StreamProcessor(ABC, Generic[T]):
    """流处理器基类"""
    
    @abstractmethod
    async def process_chunk(self, chunk: StreamChunk[T]) -> StreamChunk[T]:
        """处理单个数据块"""
        pass
    
    @abstractmethod
    async def finalize_stream(self, stream_id: str) -> Dict[str, Any]:
        """完成流处理"""
        pass


class TextStreamProcessor(StreamProcessor[str]):
    """文本流处理器"""
    
    def __init__(self):
        self.text_buffers: Dict[str, List[str]] = {}
        self.processing_functions: List[Callable[[str], str]] = []
    
    def add_processing_function(self, func: Callable[[str], str]):
        """添加文本处理函数"""
        self.processing_functions.append(func)
    
    async def process_chunk(self, chunk: StreamChunk[str]) -> StreamChunk[str]:
        """处理文本块"""
        
        processed_text = chunk.data
        
        # 应用所有处理函数
        for func in self.processing_functions:
            try:
                processed_text = func(processed_text)
            except Exception as e:
                chunk.metadata["processing_errors"] = chunk.metadata.get("processing_errors", [])
                chunk.metadata["processing_errors"].append(str(e))
        
        # 缓冲文本用于后续处理
        stream_id = chunk.metadata.get("stream_id", "default")
        if stream_id not in self.text_buffers:
            self.text_buffers[stream_id] = []
        
        self.text_buffers[stream_id].append(processed_text)
        
        return StreamChunk(
            chunk_id=chunk.chunk_id,
            data=processed_text,
            chunk_type="processed_text",
            timestamp=datetime.now(),
            metadata={**chunk.metadata, "processed": True},
            is_final=chunk.is_final,
            sequence_number=chunk.sequence_number,
            total_chunks=chunk.total_chunks
        )
    
    async def finalize_stream(self, stream_id: str) -> Dict[str, Any]:
        """完成文本流处理"""
        
        if stream_id in self.text_buffers:
            full_text = "".join(self.text_buffers[stream_id])
            chunk_count = len(self.text_buffers[stream_id])
            
            # 清理缓冲区
            del self.text_buffers[stream_id]
            
            return {
                "stream_id": stream_id,
                "final_text": full_text,
                "total_chunks": chunk_count,
                "text_length": len(full_text),
                "completion_time": datetime.now().isoformat()
            }
        
        return {"stream_id": stream_id, "status": "not_found"}


class JsonStreamProcessor(StreamProcessor[Dict[str, Any]]):
    """JSON流处理器"""
    
    def __init__(self):
        self.json_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.validation_enabled = True
    
    async def process_chunk(self, chunk: StreamChunk[Dict[str, Any]]) -> StreamChunk[Dict[str, Any]]:
        """处理JSON块"""
        
        processed_data = chunk.data.copy()
        
        # JSON验证和清理
        if self.validation_enabled:
            processed_data = self._validate_and_clean_json(processed_data)
        
        # 添加处理元数据
        processed_data["_processing"] = {
            "chunk_id": chunk.chunk_id,
            "processed_at": datetime.now().isoformat(),
            "original_size": len(json.dumps(chunk.data))
        }
        
        # 缓冲数据
        stream_id = chunk.metadata.get("stream_id", "default")
        if stream_id not in self.json_buffers:
            self.json_buffers[stream_id] = []
        
        self.json_buffers[stream_id].append(processed_data)
        
        return StreamChunk(
            chunk_id=chunk.chunk_id,
            data=processed_data,
            chunk_type="processed_json",
            timestamp=datetime.now(),
            metadata={**chunk.metadata, "processed": True},
            is_final=chunk.is_final,
            sequence_number=chunk.sequence_number,
            total_chunks=chunk.total_chunks
        )
    
    def _validate_and_clean_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理JSON数据"""
        
        cleaned_data = {}
        
        for key, value in data.items():
            # 清理键名
            clean_key = str(key).strip()
            if not clean_key:
                continue
            
            # 处理值
            if isinstance(value, (str, int, float, bool)):
                cleaned_data[clean_key] = value
            elif isinstance(value, dict):
                cleaned_data[clean_key] = self._validate_and_clean_json(value)
            elif isinstance(value, list):
                cleaned_data[clean_key] = [
                    self._validate_and_clean_json(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # 尝试序列化复杂对象
                try:
                    cleaned_data[clean_key] = json.loads(json.dumps(value, default=str))
                except:
                    cleaned_data[clean_key] = str(value)
        
        return cleaned_data
    
    async def finalize_stream(self, stream_id: str) -> Dict[str, Any]:
        """完成JSON流处理"""
        
        if stream_id in self.json_buffers:
            all_data = self.json_buffers[stream_id]
            chunk_count = len(all_data)
            
            # 合并所有JSON对象
            merged_data = {}
            for data in all_data:
                if isinstance(data, dict):
                    merged_data.update(data)
            
            # 清理缓冲区
            del self.json_buffers[stream_id]
            
            return {
                "stream_id": stream_id,
                "final_data": merged_data,
                "total_chunks": chunk_count,
                "data_size": len(json.dumps(merged_data)),
                "completion_time": datetime.now().isoformat()
            }
        
        return {"stream_id": stream_id, "status": "not_found"}


class EventStreamProcessor(StreamProcessor[AgentEvent]):
    """事件流处理器"""
    
    def __init__(self):
        self.event_buffers: Dict[str, List[AgentEvent]] = {}
        self.event_filters: List[Callable[[AgentEvent], bool]] = []
        self.event_transformers: List[Callable[[AgentEvent], AgentEvent]] = []
    
    def add_event_filter(self, filter_func: Callable[[AgentEvent], bool]):
        """添加事件过滤器"""
        self.event_filters.append(filter_func)
    
    def add_event_transformer(self, transformer_func: Callable[[AgentEvent], AgentEvent]):
        """添加事件转换器"""
        self.event_transformers.append(transformer_func)
    
    async def process_chunk(self, chunk: StreamChunk[AgentEvent]) -> StreamChunk[AgentEvent]:
        """处理事件块"""
        
        event = chunk.data
        
        # 应用过滤器
        for filter_func in self.event_filters:
            if not filter_func(event):
                # 事件被过滤掉
                return StreamChunk(
                    chunk_id=chunk.chunk_id,
                    data=event,
                    chunk_type="filtered_event",
                    metadata={**chunk.metadata, "filtered": True},
                    is_final=chunk.is_final,
                    sequence_number=chunk.sequence_number,
                    total_chunks=chunk.total_chunks
                )
        
        # 应用转换器
        processed_event = event
        for transformer in self.event_transformers:
            try:
                processed_event = transformer(processed_event)
            except Exception as e:
                processed_event.metadata["transformation_errors"] = \
                    processed_event.metadata.get("transformation_errors", [])
                processed_event.metadata["transformation_errors"].append(str(e))
        
        # 缓冲事件
        stream_id = chunk.metadata.get("stream_id", "default")
        if stream_id not in self.event_buffers:
            self.event_buffers[stream_id] = []
        
        self.event_buffers[stream_id].append(processed_event)
        
        return StreamChunk(
            chunk_id=chunk.chunk_id,
            data=processed_event,
            chunk_type="processed_event",
            timestamp=datetime.now(),
            metadata={**chunk.metadata, "processed": True},
            is_final=chunk.is_final,
            sequence_number=chunk.sequence_number,
            total_chunks=chunk.total_chunks
        )
    
    async def finalize_stream(self, stream_id: str) -> Dict[str, Any]:
        """完成事件流处理"""
        
        if stream_id in self.event_buffers:
            events = self.event_buffers[stream_id]
            
            # 统计事件类型
            event_stats = {}
            for event in events:
                event_type = event.type.value
                event_stats[event_type] = event_stats.get(event_type, 0) + 1
            
            # 清理缓冲区
            del self.event_buffers[stream_id]
            
            return {
                "stream_id": stream_id,
                "total_events": len(events),
                "event_statistics": event_stats,
                "completion_time": datetime.now().isoformat()
            }
        
        return {"stream_id": stream_id, "status": "not_found"}


class StreamingProcessor:
    """主流式处理器"""
    
    def __init__(self):
        self.processors: Dict[str, StreamProcessor] = {
            "text": TextStreamProcessor(),
            "json": JsonStreamProcessor(),
            "event": EventStreamProcessor()
        }
        
        self.active_streams: Dict[str, StreamMetrics] = {}
        self.stream_buffers: Dict[str, List[StreamChunk]] = {}
        
        # 性能配置
        self.max_concurrent_streams = 10
        self.max_buffer_size = 1000
        self.processing_timeout = 30.0
        
        # 统计信息
        self.processing_stats = {
            "total_streams": 0,
            "completed_streams": 0,
            "failed_streams": 0,
            "total_chunks_processed": 0,
            "average_processing_time": 0.0
        }
    
    def register_processor(self, processor_type: str, processor: StreamProcessor):
        """注册自定义处理器"""
        self.processors[processor_type] = processor
    
    async def create_stream(self, stream_id: str, processor_type: str = "text") -> bool:
        """创建新的数据流"""
        
        if len(self.active_streams) >= self.max_concurrent_streams:
            return False
        
        if stream_id in self.active_streams:
            return False
        
        if processor_type not in self.processors:
            return False
        
        self.active_streams[stream_id] = StreamMetrics(
            stream_id=stream_id,
            start_time=datetime.now()
        )
        
        self.stream_buffers[stream_id] = []
        self.processing_stats["total_streams"] += 1
        
        return True
    
    async def process_stream(self, stream_id: str, 
                           data_iterator: AsyncIterator[Any],
                           processor_type: str = "text") -> AsyncIterator[StreamChunk]:
        """处理数据流"""
        
        if stream_id not in self.active_streams:
            if not await self.create_stream(stream_id, processor_type):
                raise ValueError(f"Failed to create stream {stream_id}")
        
        metrics = self.active_streams[stream_id]
        processor = self.processors[processor_type]
        chunk_counter = 0
        
        try:
            async for data in data_iterator:
                # 创建数据块
                chunk = StreamChunk(
                    chunk_id=f"{stream_id}_chunk_{chunk_counter}",
                    data=data,
                    chunk_type=f"raw_{processor_type}",
                    metadata={"stream_id": stream_id},
                    sequence_number=chunk_counter
                )
                
                # 处理数据块
                start_time = time.time()
                processed_chunk = await processor.process_chunk(chunk)
                processing_time = time.time() - start_time
                
                # 更新指标
                metrics.total_chunks += 1
                metrics.processed_chunks += 1
                metrics.bytes_processed += len(str(data))
                metrics.latency_ms = processing_time * 1000
                
                # 缓冲处理结果
                if len(self.stream_buffers[stream_id]) < self.max_buffer_size:
                    self.stream_buffers[stream_id].append(processed_chunk)
                
                chunk_counter += 1
                self.processing_stats["total_chunks_processed"] += 1
                
                yield processed_chunk
                
        except Exception as e:
            metrics.error_count += 1
            self.processing_stats["failed_streams"] += 1
            
            error_chunk = StreamChunk(
                chunk_id=f"{stream_id}_error_{chunk_counter}",
                data={"error": str(e)},
                chunk_type="error",
                metadata={"stream_id": stream_id, "error": True},
                is_final=True
            )
            
            yield error_chunk
            
        finally:
            # 完成流处理
            await self._finalize_stream(stream_id, processor)
    
    async def _finalize_stream(self, stream_id: str, processor: StreamProcessor):
        """完成流处理"""
        
        try:
            # 调用处理器的完成方法
            finalization_result = await processor.finalize_stream(stream_id)
            
            # 更新指标
            if stream_id in self.active_streams:
                metrics = self.active_streams[stream_id]
                total_time = (datetime.now() - metrics.start_time).total_seconds()
                
                if total_time > 0:
                    metrics.processing_rate = metrics.processed_chunks / total_time
                    metrics.throughput = metrics.bytes_processed / total_time
                
                # 移动到完成状态
                del self.active_streams[stream_id]
                self.processing_stats["completed_streams"] += 1
            
            # 清理缓冲区
            if stream_id in self.stream_buffers:
                del self.stream_buffers[stream_id]
                
        except Exception as e:
            print(f"Error finalizing stream {stream_id}: {e}")
    
    async def batch_process_chunks(self, chunks: List[StreamChunk],
                                 processor_type: str = "text") -> List[StreamChunk]:
        """批量处理数据块"""
        
        if processor_type not in self.processors:
            raise ValueError(f"Unknown processor type: {processor_type}")
        
        processor = self.processors[processor_type]
        processed_chunks = []
        
        for chunk in chunks:
            try:
                processed_chunk = await processor.process_chunk(chunk)
                processed_chunks.append(processed_chunk)
            except Exception as e:
                error_chunk = StreamChunk(
                    chunk_id=chunk.chunk_id,
                    data={"error": str(e)},
                    chunk_type="error",
                    metadata={**chunk.metadata, "error": True}
                )
                processed_chunks.append(error_chunk)
        
        return processed_chunks
    
    async def transform_stream(self, input_stream: AsyncIterator[StreamChunk],
                             transformer_func: Callable[[StreamChunk], StreamChunk]) -> AsyncIterator[StreamChunk]:
        """转换数据流"""
        
        async for chunk in input_stream:
            try:
                transformed_chunk = transformer_func(chunk)
                yield transformed_chunk
            except Exception as e:
                error_chunk = StreamChunk(
                    chunk_id=chunk.chunk_id,
                    data={"error": str(e)},
                    chunk_type="transformation_error",
                    metadata={**chunk.metadata, "transformation_error": True}
                )
                yield error_chunk
    
    async def filter_stream(self, input_stream: AsyncIterator[StreamChunk],
                          filter_func: Callable[[StreamChunk], bool]) -> AsyncIterator[StreamChunk]:
        """过滤数据流"""
        
        async for chunk in input_stream:
            try:
                if filter_func(chunk):
                    yield chunk
            except Exception as e:
                # 过滤函数出错时，保留原数据块但添加错误信息
                chunk.metadata["filter_error"] = str(e)
                yield chunk
    
    async def merge_streams(self, *streams: AsyncIterator[StreamChunk]) -> AsyncIterator[StreamChunk]:
        """合并多个数据流"""
        
        # 创建合并任务
        tasks = [asyncio.create_task(self._stream_to_queue(stream)) for stream in streams]
        
        # 从队列中读取数据
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                try:
                    chunk = await task
                    if chunk is not None:
                        yield chunk
                        # 重新启动任务
                        stream_index = tasks.index(task)
                        tasks[stream_index] = asyncio.create_task(
                            self._stream_to_queue(streams[stream_index])
                        )
                    else:
                        # 流结束
                        tasks.remove(task)
                except Exception as e:
                    tasks.remove(task)
    
    async def _stream_to_queue(self, stream: AsyncIterator[StreamChunk]) -> Optional[StreamChunk]:
        """将流转换为队列项"""
        try:
            return await stream.__anext__()
        except StopAsyncIteration:
            return None
    
    def get_stream_metrics(self, stream_id: str) -> Optional[StreamMetrics]:
        """获取流指标"""
        return self.active_streams.get(stream_id)
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        
        active_streams = len(self.active_streams)
        total_buffer_size = sum(len(buffer) for buffer in self.stream_buffers.values())
        
        # 计算平均处理时间
        if self.processing_stats["completed_streams"] > 0:
            # 这里需要更复杂的计算，简化处理
            avg_processing_time = 1.0  # 示例值
        else:
            avg_processing_time = 0.0
        
        return {
            "processing_stats": self.processing_stats,
            "active_streams": active_streams,
            "total_buffer_size": total_buffer_size,
            "available_processors": list(self.processors.keys()),
            "max_concurrent_streams": self.max_concurrent_streams,
            "average_processing_time": avg_processing_time
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            active_streams = len(self.active_streams)
            total_errors = sum(metrics.error_count for metrics in self.active_streams.values())
            
            # 计算健康分数
            health_score = 1.0
            
            if active_streams > self.max_concurrent_streams * 0.8:
                health_score -= 0.2
            
            if total_errors > 0:
                health_score -= 0.3
            
            error_rate = (
                self.processing_stats["failed_streams"] / 
                max(1, self.processing_stats["total_streams"])
            )
            
            if error_rate > 0.1:
                health_score -= 0.3
            
            health_score = max(0.0, health_score)
            
            return {
                "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "unhealthy",
                "health_score": health_score,
                "active_streams": active_streams,
                "total_errors": total_errors,
                "error_rate": error_rate,
                "processing_stats": self.processing_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "health_score": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }