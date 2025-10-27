# Loom 框架统一协调机制设计

## 🎯 设计目标

实现四大核心能力的深度集成，让它们能够：
1. **智能上下文在 TT 递归中组织复杂任务**
2. **动态调整策略和资源分配**
3. **统一的状态管理和性能优化**
4. **跨组件的协调和通信**

## 🏗️ 架构设计

### 1. 统一执行上下文 (UnifiedExecutionContext)

```python
@dataclass
class UnifiedExecutionContext:
    """统一的执行上下文，协调四大核心能力"""
    
    # 基础信息
    execution_id: str
    correlation_id: Optional[str] = None
    working_dir: Optional[Path] = None
    
    # 四大核心能力实例
    context_assembler: Optional[ContextAssembler] = None
    task_tool: Optional[TaskTool] = None
    event_processor: Optional[EventProcessor] = None
    task_handlers: List[TaskHandler] = field(default_factory=list)
    
    # 统一状态管理
    execution_state: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # 协调配置
    enable_cross_component_optimization: bool = True
    enable_dynamic_strategy_adjustment: bool = True
    enable_unified_monitoring: bool = True
```

### 2. 智能协调器 (IntelligentCoordinator)

```python
class IntelligentCoordinator:
    """智能协调器 - 统一管理四大核心能力"""
    
    def __init__(self, config: UnifiedExecutionContext):
        self.config = config
        self._setup_cross_component_integration()
    
    def _setup_cross_component_integration(self):
        """设置跨组件集成"""
        # ContextAssembler 与 TT 递归集成
        if self.config.context_assembler:
            self.config.context_assembler.set_coordinator(self)
        
        # TaskTool 与上下文组装集成
        if self.config.task_tool:
            self.config.task_tool.set_context_assembler(self.config.context_assembler)
        
        # EventProcessor 与所有组件集成
        if self.config.event_processor:
            self.config.event_processor.set_coordinator(self)
    
    def coordinate_tt_recursion(self, 
                               messages: List[Message],
                               turn_state: TurnState,
                               context: ExecutionContext) -> AsyncGenerator[AgentEvent, None]:
        """协调 TT 递归执行"""
        
        # 1. 智能上下文组装
        assembled_context = self._intelligent_context_assembly(messages, turn_state)
        
        # 2. 动态任务处理策略
        task_strategy = self._determine_task_strategy(messages, turn_state)
        
        # 3. 协调执行
        async for event in self._coordinated_execution(assembled_context, task_strategy):
            # 4. 统一事件处理
            processed_events = self._process_events([event])
            for processed_event in processed_events:
                yield processed_event
    
    def _intelligent_context_assembly(self, 
                                    messages: List[Message],
                                    turn_state: TurnState) -> str:
        """智能上下文组装"""
        if not self.config.context_assembler:
            return ""
        
        # 基于 TT 递归状态动态调整上下文策略
        recursion_depth = turn_state.turn_counter
        
        # 根据递归深度调整优先级
        if recursion_depth > 3:
            # 深度递归时，优先保留核心指令和工具定义
            self.config.context_assembler.adjust_priority(
                "base_instructions", ComponentPriority.CRITICAL
            )
            self.config.context_assembler.adjust_priority(
                "tool_definitions", ComponentPriority.HIGH
            )
        
        # 基于任务类型调整上下文
        task_type = self._analyze_task_type(messages)
        if task_type == "complex_analysis":
            # 复杂分析任务需要更多示例和指导
            self.config.context_assembler.adjust_priority(
                "examples", ComponentPriority.MEDIUM
            )
        
        return self.config.context_assembler.assemble()
    
    def _determine_task_strategy(self, 
                               messages: List[Message],
                               turn_state: TurnState) -> Dict[str, Any]:
        """确定任务处理策略"""
        strategy = {
            "use_sub_agents": False,
            "parallel_execution": False,
            "context_priority": "balanced",
            "event_batching": True
        }
        
        # 基于任务复杂度决定是否使用子代理
        task_complexity = self._assess_task_complexity(messages)
        if task_complexity > 0.7:
            strategy["use_sub_agents"] = True
            strategy["parallel_execution"] = True
        
        # 基于递归深度调整策略
        if turn_state.turn_counter > 5:
            strategy["context_priority"] = "minimal"
            strategy["event_batching"] = True
        
        return strategy
```

### 3. 增强的 AgentExecutor

```python
class EnhancedAgentExecutor(AgentExecutor):
    """增强的 AgentExecutor，集成统一协调机制"""
    
    def __init__(self, 
                 llm: BaseLLM,
                 tools: Dict[str, BaseTool] | None = None,
                 unified_context: Optional[UnifiedExecutionContext] = None,
                 **kwargs):
        
        super().__init__(llm, tools, **kwargs)
        
        # 设置统一执行上下文
        self.unified_context = unified_context or UnifiedExecutionContext(
            execution_id=str(uuid4())
        )
        
        # 创建智能协调器
        self.coordinator = IntelligentCoordinator(self.unified_context)
        
        # 集成四大核心能力
        self._integrate_core_capabilities()
    
    def _integrate_core_capabilities(self):
        """集成四大核心能力"""
        
        # 1. 集成 ContextAssembler
        if not self.unified_context.context_assembler:
            self.unified_context.context_assembler = ContextAssembler(
                max_tokens=self.max_context_tokens,
                enable_caching=True
            )
        
        # 2. 集成 TaskTool
        if "task" in self.tools and not self.unified_context.task_tool:
            self.unified_context.task_tool = self.tools["task"]
        
        # 3. 集成 EventProcessor
        if not self.unified_context.event_processor:
            # 创建智能事件过滤器
            llm_filter = EventFilter(
                allowed_types=[
                    AgentEventType.LLM_DELTA,
                    AgentEventType.TOOL_RESULT,
                    AgentEventType.AGENT_FINISH
                ],
                enable_batching=True,
                batch_size=5
            )
            
            self.unified_context.event_processor = EventProcessor(
                filters=[llm_filter],
                enable_stats=True
            )
        
        # 4. 集成 TaskHandlers
        if not self.unified_context.task_handlers:
            self.unified_context.task_handlers = self.task_handlers or []
    
    async def tt(self,
                messages: List[Message],
                turn_state: TurnState,
                context: ExecutionContext) -> AsyncGenerator[AgentEvent, None]:
        """增强的 TT 递归，集成统一协调"""
        
        # 使用智能协调器协调执行
        async for event in self.coordinator.coordinate_tt_recursion(
            messages, turn_state, context
        ):
            yield event
    
    def get_unified_metrics(self) -> Dict[str, Any]:
        """获取统一的性能指标"""
        metrics = {
            "execution_id": self.unified_context.execution_id,
            "timestamp": time.time()
        }
        
        # 收集各组件指标
        if self.unified_context.context_assembler:
            metrics["context_assembler"] = self.unified_context.context_assembler.get_component_stats()
        
        if self.unified_context.task_tool:
            metrics["task_tool"] = self.unified_context.task_tool.get_pool_stats()
        
        if self.unified_context.event_processor:
            metrics["event_processor"] = self.unified_context.event_processor.get_stats()
        
        return metrics
```

## 🔄 统一协调流程

### 1. 智能上下文组织复杂任务

```python
async def intelligent_task_coordination():
    """智能任务协调示例"""
    
    # 创建统一执行上下文
    unified_context = UnifiedExecutionContext(
        execution_id="task_001",
        enable_cross_component_optimization=True,
        enable_dynamic_strategy_adjustment=True
    )
    
    # 创建增强的执行器
    executor = EnhancedAgentExecutor(
        llm=llm,
        tools=tools,
        unified_context=unified_context
    )
    
    # 执行复杂任务
    messages = [Message(role="user", content="分析项目代码质量并生成报告")]
    turn_state = TurnState.initial(max_iterations=20)
    context = ExecutionContext.create()
    
    async for event in executor.tt(messages, turn_state, context):
        # 事件会被智能协调器处理
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✓ 任务完成: {event.content}")
            
            # 获取统一性能指标
            metrics = executor.get_unified_metrics()
            print(f"\n📊 性能指标: {metrics}")
```

### 2. 动态策略调整

```python
class DynamicStrategyAdjuster:
    """动态策略调整器"""
    
    def __init__(self, coordinator: IntelligentCoordinator):
        self.coordinator = coordinator
        self.strategy_history = []
    
    def adjust_strategy_based_on_performance(self, 
                                           current_metrics: Dict[str, Any],
                                           target_performance: Dict[str, Any]):
        """基于性能指标动态调整策略"""
        
        # 分析性能瓶颈
        bottlenecks = self._identify_bottlenecks(current_metrics)
        
        for bottleneck in bottlenecks:
            if bottleneck == "context_assembly_slow":
                # 调整上下文组装策略
                self.coordinator.config.context_assembler.enable_caching = True
                self.coordinator.config.context_assembler.cache_size = 200
            
            elif bottleneck == "sub_agent_creation_overhead":
                # 调整子代理池策略
                self.coordinator.config.task_tool.pool_size = 10
                self.coordinator.config.task_tool.enable_pooling = True
            
            elif bottleneck == "event_processing_latency":
                # 调整事件处理策略
                for filter_obj in self.coordinator.config.event_processor.filters:
                    filter_obj.batch_size = 20
                    filter_obj.batch_timeout = 0.05
```

## 🎯 实现效果

### 1. **智能上下文组织**
- ContextAssembler 根据 TT 递归状态动态调整优先级
- 基于任务复杂度智能选择上下文策略
- 跨组件共享上下文信息

### 2. **统一协调执行**
- 四大能力协同工作，而非独立运行
- 统一的性能监控和优化
- 智能的资源分配和负载均衡

### 3. **动态策略调整**
- 基于实时性能指标调整策略
- 自适应优化执行参数
- 智能的故障恢复和降级

这样的统一协调机制将让 Loom 框架真正成为一个强大、完整、统一的 AI Agent 开发平台！
