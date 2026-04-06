# Loom Framework Implementation Gaps Analysis

**分析日期**: 2026-04-03
**分析范围**: loom/ 框架代码
**目标**: 识别未实现、部分实现、最小化实现的方法和机制

---

## 概述

本文档记录了 Loom 框架中所有需要完善的实现。问题按优先级分为三类：

- **P0**: 阻止运行时实际运行的核心问题
- **P1**: 使框架在实际集成中可用的问题
- **P2**: 高级能力和差异化特性的问题

---

## P0: 核心运行时问题

### 1. Gemini Provider 完全是 Mock 实现

**文件**: `loom/providers/gemini.py`

**问题**:
```python
async def complete(self, messages: list, params: CompletionParams | None = None) -> str:
    return "Mock Gemini response"

async def stream(self, messages: list, params: CompletionParams | None = None) -> AsyncIterator[str]:
    yield "Mock Gemini stream"
```

**影响**:
- Gemini provider 无法进行真实的模型调用
- 与 OpenAI 和 Anthropic 的实现完整度不一致

**对比**: OpenAI 和 Anthropic providers 已经实现了完整的 API 调用逻辑

**建议**:
- 实现真实的 Google Gemini API 集成
- 或者明确标记为 experimental/unsupported

---

### 2. RunHandle.resume() 缺少实际逻辑

**文件**: `loom/api/handles.py:215`

**问题**:
```python
async def resume(self) -> None:
    """Resume execution"""
    if self.run.state != RunState.PAUSED:
        raise ValueError(f"Cannot resume from state {self.run.state.value}")

    self.run.state = RunState.RUNNING
    # TODO: Implement actual resume logic
```

**影响**:
- 暂停/恢复功能不完整
- 状态改变了但没有实际恢复执行流程

**建议**:
- 实现真正的执行恢复逻辑
- 或者如果不支持 resume，应该抛出 NotImplementedError

---

### 3. transcript() 返回简单字典而非结构化输出

**文件**: `loom/api/handles.py:229-238`

**问题**:
```python
async def transcript(self) -> dict:
    """Get transcript"""
    return {
        "run_id": self.run.id,
        "task_id": self.task.id,
        "state": self.run.state.value,
        "summary": self.run.summary,
        "events": [e.__dict__ for e in self._events],
        "artifacts": [a.__dict__ for a in self._artifacts]
    }
```

**影响**:
- 使用 `__dict__` 直接序列化对象，可能暴露内部状态
- 缺少格式化、时间线重建等高级功能
- TODO.md 中标记为 "real structured output"

**建议**:
- 定义 TranscriptFormat 类型
- 实现结构化的 transcript 构建逻辑
- 支持不同的输出格式（JSON, Markdown, etc.）

---

### 4. SessionHandle.close() 资源清理不完整

**文件**: `loom/api/handles.py:57-60`

**问题**:
```python
async def close(self) -> None:
    """Close session"""
    self.session._closed = True
    self._tasks.clear()
```

**影响**:
- 只清理了 tasks，没有清理其他资源
- 没有关闭 provider 连接
- 没有清理 event bus 订阅
- 没有持久化 session 状态

**建议**:
- 实现完整的资源清理流程
- 关闭所有相关的连接和订阅
- 可选的 session 状态持久化

---

## P1: 框架可用性问题

### 5. Web 工具完全是 Mock 实现

**文件**: `loom/tools/builtin/web.py:6-15`

**问题**:
```python
async def web_fetch(url: str) -> str:
    """Fetch web content"""
    # TODO: Implement actual web fetch
    return f"Mock fetch from {url}"

async def web_search(query: str) -> str:
    """Search the web"""
    # TODO: Implement actual web search
    return f"Mock search results for: {query}"
```

**影响**:
- 工具声称有能力但实际不工作
- 用户无法使用 web 相关功能

**建议**:
- 实现 web_fetch: 使用 httpx/aiohttp
- 实现 web_search: 集成搜索 API (Google, Bing, DuckDuckGo)
- 或者从 builtin tools 中移除，标记为 optional

---

### 6. 知识检索使用词法相似度而非真正的嵌入

**文件**: `loom/tools/knowledge.py:130-147`

**问题**:
```python
def _similarity(self, left: str, right: str) -> float:
    """Compute lexical similarity by token overlap."""
    left_tokens = self._tokenize(left)
    right_tokens = self._tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union if union else 0.0
```

**影响**:
- 检索质量低，无法理解语义
- 与 "RAG as Evidence" 的定位不符
- TODO.md 标记为 "not just structural"

**建议**:
- 集成真实的 embedding 模型（OpenAI, Sentence Transformers）
- 实现向量相似度搜索
- 保留词法相似度作为 fallback

---

### 7. Context Compression 的 micro_compact 未实现

**文件**: `loom/context/compression.py:50-53`

**问题**:
```python
def micro_compact(self, messages: list[Message]) -> list[Message]:
    """Micro Compact: 基于 tool_use_id 缓存编辑结果"""
    # TODO: Implement tool result caching
    return messages
```

**影响**:
- 四层压缩机制中的一层缺失
- 无法缓存工具结果，导致重复内容占用 token

**建议**:
- 实现基于 tool_use_id 的结果缓存
- 识别重复的工具调用结果并压缩

---

### 8. 工具治理的权限检查实现基础但不够细粒度

**文件**: `loom/tools/governance.py:28-54`

**当前实现**:
```python
def check_permission(
    self,
    tool_name: str,
    tool_definition: ToolDefinition | None = None,
) -> tuple[bool, str]:
    """Check if tool execution is allowed"""
    if not self.config.enable_permission_check:
        return True, ""

    if tool_name in self.config.deny_tools:
        return False, f"{tool_name} is explicitly denied"

    # ... 基础检查
```

**问题**:
- 只有简单的 allow/deny 逻辑
- 缺少基于参数的细粒度控制
- 缺少基于上下文的动态决策
- TODO.md 标记需要 "enrich policy rules beyond simple allow/deny"

**建议**:
- 支持参数级别的权限控制
- 支持条件性权限（基于上下文、时间、频率）
- 集成 hook 系统进行动态决策

---

### 9. 语义内存搜索实现了但只有基础功能

**文件**: `loom/memory/semantic.py:25-44`

**当前实现**:
```python
def search(
    self,
    query: str,
    top_k: int = 5,
    query_embedding: list[float] | None = None,
) -> list[MemoryEntry]:
    """Search similar memories using embeddings or lexical fallback."""
    if top_k <= 0 or not self.entries:
        return []

    scored = [
        (
            self._score_entry(query, entry, query_embedding=query_embedding),
            index,
            entry,
        )
        for index, entry in enumerate(self.entries)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [entry for _, _, entry in scored[:top_k]]
```

**问题**:
- 实现了基础搜索，但缺少高级功能
- 没有向量索引（线性搜索，O(n)）
- 没有持久化
- 没有过期/清理机制
- TODO.md 标记为 "placeholder"

**建议**:
- 添加向量索引（FAISS, Annoy）
- 实现持久化存储
- 添加 TTL 和容量限制
- 支持元数据过滤

---

### 10. Planner 只是最小依赖门控

**文件**: `loom/orchestration/planner.py:26-43`

**当前实现**:
```python
def create_plan(self, goal: str, max_tasks: int = 5) -> list[Task]:
    """Create a simple sequential task plan from a goal string."""
    steps = self._split_goal(goal)[:max_tasks]
    if not steps:
        steps = [goal.strip() or "Complete task"]

    planned: list[Task] = []
    previous_id: str | None = None
    for step in steps:
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        dependencies = [previous_id] if previous_id else []
        task = Task(id=task_id, goal=step, dependencies=dependencies)
        self.add_task(task)
        planned.append(task)
        previous_id = task_id

    return planned
```

**问题**:
- 只是简单的字符串分割，没有智能规划
- 所有任务都是顺序依赖，无法并行
- 没有使用 LLM 进行任务分解
- TODO.md 标记为 "partial - only a minimal dependency gate"

**建议**:
- 使用 LLM 进行智能任务分解
- 识别可并行的任务
- 支持复杂的依赖关系图
- 集成 sub-agent 生成逻辑

---


## P2: 高级能力问题

### 11. MCP 集成有两个重复实现

**文件**:
- `loom/ecosystem/mcp.py` (完整实现)
- `loom/capabilities/mcp.py` (不存在，但 TODO.md 中提到)

**问题**:
- TODO.md 提到有两个 MCP 实现
- 实际只找到 `loom/ecosystem/mcp.py`
- 可能是文档过期，或者代码已经合并

**当前状态**:
- `loom/ecosystem/mcp.py` 实现了基础的 MCP bridge
- 支持 stdio/sse/http/ws 传输
- 但实际连接和工具执行仍使用 mock 数据

**建议**:
- 确认是否真的有重复实现
- 实现真实的 MCP 协议通信
- 完成 stdio 进程管理
- 实现 SSE/HTTP/WS 客户端

---

### 12. Evolution Strategies 完全是占位符

**文件**: `loom/evolution/strategies.py:14-27`

**问题**:
```python
class ToolLearningStrategy(EvolutionStrategy):
    """E1: Tool learning"""

    def apply(self, agent):
        # TODO: Implement tool learning
        pass


class PolicyOptimizationStrategy(EvolutionStrategy):
    """E2: Policy optimization"""

    def apply(self, agent):
        # TODO: Implement policy optimization
        pass
```

**影响**:
- Evolution 系统结构存在但无行为
- 无法进行工具学习和策略优化

**建议**:
- 实现 E1: 基于成功/失败反馈的工具选择优化
- 实现 E2: 基于奖励信号的策略调整
- 定义 evolution 的触发条件和存储机制

---

### 13. Heartbeat 监控集成不完整

**文件**: `loom/runtime/monitors.py:139-179`

**问题**:
```python
class MFEventsMonitor:
    """M_f 事件总线监控"""

    def __init__(self, topics: list[str], event_bus: Any | None = None):
        self.topics = topics
        self.event_bus = event_bus
        self.cursor = 0

    def check(self, timestamp: str) -> dict | None:
        """检查 M_f 事件总线"""
        if self.event_bus is None:
            return None
        # ... 实现存在但未完全集成
```

**影响**:
- MFEventsMonitor 实现了但需要手动设置 event_bus
- Heartbeat 和 Dashboard 的集成不够深入
- TODO.md 标记为 "partial - sensing is not deeply integrated into loop control"

**建议**:
- 自动连接 event_bus 到 monitors
- 将 heartbeat 事件深度集成到运行循环
- 实现基于 heartbeat 的中断和决策机制

---

### 14. Context Renewal 保留了状态但未完全恢复语义

**文件**: `loom/context/renewal.py:29-77`

**当前实现**:
```python
def renew(self, partitions: ContextPartitions, goal: str) -> ContextPartitions:
    """Renew context by compressing and rebuilding"""
    # 1. Snapshot dashboard
    self.persistent.save('working_state', {...})

    # 2. Snapshot plan
    self.persistent.save('plan_state', {...})

    # ... 保存了状态

    # 6. Rebuild new context
    new_partitions = ContextPartitions()
    new_partitions.system = partitions.system  # 永不压缩
    new_partitions.working = partitions.working  # 永不压缩（语义不丢失）
    # ...
```

**问题**:
- 保存了状态到 persistent memory
- 但没有实现从 persistent memory 恢复的逻辑
- 新的 context 如何消费这些保存的状态？
- TODO.md 标记为 "partial - ensure renewed context is actually consumed"

**建议**:
- 实现 restore() 方法从 persistent memory 恢复
- 定义 renewed context 的消费路径
- 确保 goal、plan、events 在 renew 后仍然可用

---

### 15. Dashboard 状态存储但未用于决策

**文件**: `loom/context/dashboard.py`

**当前实现**:
```python
class DashboardManager:
    """Manage Dashboard state"""

    def update_rho(self, rho: float):
        """Update context pressure"""
        self.dashboard.rho = rho

    def update_progress(self, progress: str):
        """Update goal progress"""
        self.dashboard.goal_progress = progress

    # ... 更多更新方法
```

**问题**:
- Dashboard 收集了大量状态信息
- 但这些信息没有被用于驱动决策
- 只是存储，没有"读取并决策"的路径
- TODO.md 标记为 "define how dashboard state feeds decisions instead of only storing values"

**建议**:
- 实现基于 dashboard 的决策逻辑
- 例如：rho > 0.9 触发压缩
- 例如：error_count > 3 触发策略调整
- 例如：interrupt_requested 触发执行暂停

---

### 16. Plugin 生态系统加载但未完全连接

**文件**: `loom/ecosystem/integration.py:72-120`

**当前实现**:
```python
def _load_plugin_components(self, plugin: Plugin):
    """Load skills, MCP servers from plugin"""
    if not plugin.enabled:
        return

    # Load skills
    if plugin.manifest.skills:
        for skill_path in plugin.manifest.skills:
            # ... 加载 skills

    # Load MCP servers
    if plugin.manifest.mcp_servers:
        for server_name, server_config in plugin.manifest.mcp_servers.items():
            # ... 注册 MCP servers
```

**问题**:
- Plugin 可以加载 skills 和 MCP servers
- 但 hooks 没有实现
- commands 没有实现
- 与 runtime 的集成不完整
- TODO.md 标记为 "partial - connect loaded plugins to tools, hooks, skills, and MCP servers"

**建议**:
- 实现 plugin hooks 加载和注册
- 实现 plugin commands 系统
- 将 plugin 的 MCP tools 自动注册到 tool registry
- 实现 plugin 的 enable/disable 生命周期影响 runtime

---

### 17. Safety Hooks 实现基础但缺少丰富的上下文

**文件**: `loom/safety/hooks.py:32-40`

**当前实现**:
```python
def trigger(self, event: str, context: dict) -> tuple[HookDecision, str]:
    """Trigger hooks, return decision"""
    for hook in self.hooks.get(event, []):
        decision = hook(context)
        if decision == HookDecision.DENY:
            return HookDecision.DENY, "Hook denied"
        elif decision == HookDecision.ASK:
            return HookDecision.ASK, "Hook requests confirmation"
    return HookDecision.ALLOW, ""
```

**问题**:
- Hook 机制存在但 context 是简单的 dict
- 缺少结构化的 veto context
- 缺少审计语义
- TODO.md 标记为 "define structured veto context and richer audit semantics"

**建议**:
- 定义 HookContext 类型
- 包含：tool_name, arguments, risk_level, user_context
- 实现审计日志记录
- 支持 hook 链和优先级

---

### 18. Permission 系统有重复的类定义

**文件**: `loom/safety/permissions.py:29-50` 和 `52-81`

**问题**:
```python
class PermissionManager:
    """Manage tool permissions"""

    def __init__(self):
        self.permissions: dict[str, Permission] = {}
    # ... 第一个实现

class PermissionManager:  # 重复定义！
    """Manage tool permissions with three-layer defense"""

    def __init__(self, mode: PermissionMode = PermissionMode.DEFAULT):
        self.permissions: dict[str, Permission] = {}
        self.mode = mode
    # ... 第二个实现
```

**影响**:
- 同一个文件中有两个 PermissionManager 类
- 第二个会覆盖第一个
- 代码混乱，可能是重构遗留

**建议**:
- 删除第一个简单版本
- 保留第二个带 mode 的版本
- 或者重命名为不同的类

---

### 19. Capability Loader 实现简单

**文件**: `loom/capabilities/loader.py:15-29`

**当前实现**:
```python
def load(self, capability_name: str):
    """Load a capability"""
    capability = self.capability_registry.get(capability_name)
    if not capability:
        return

    # Load associated tools
    for tool_name in capability.tools:
        tool = self.tool_registry.get(tool_name)
        if tool:
            self.loaded.add(capability_name)

def unload(self, capability_name: str):
    """Unload a capability"""
    self.loaded.discard(capability_name)
```

**问题**:
- load() 只是标记为 loaded，没有实际激活
- 没有将 tools 注册到 runtime
- 没有处理依赖关系
- unload() 没有清理 tools

**建议**:
- 实现真正的 tool 激活/停用
- 处理 capability 依赖
- 集成到 runtime 的 tool 可用性检查

---

### 20. VetoAuthority 实现过于简单

**文件**: `loom/safety/veto.py:4-20`

**当前实现**:
```python
class VetoAuthority:
    """Ψ's veto power (safety valve)"""

    def __init__(self):
        self.enabled = True
        self.veto_log: list[str] = []

    def veto(self, reason: str) -> bool:
        """Exercise veto power"""
        if self.enabled:
            self.veto_log.append(reason)
            return True
        return False
```

**问题**:
- 只记录 reason 字符串
- 没有时间戳
- 没有上下文信息
- 没有与 runtime 的集成
- 没有 veto 后的恢复机制

**建议**:
- 定义 VetoRecord 类型
- 包含：timestamp, reason, context, severity
- 实现 veto 后的清理和恢复逻辑
- 集成到 runtime 的错误处理流程

---


## 其他发现的问题

### 21. 多个 Base 类只有 pass 实现

**文件**: `loom/providers/base.py:33-38`, `loom/tools/base.py:28-33`, `loom/capabilities/plugin.py:12-17`

**问题**:
```python
# loom/providers/base.py
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list, params: CompletionParams | None = None) -> str:
        pass

    @abstractmethod
    async def stream(self, messages: list, params: CompletionParams | None = None) -> AsyncIterator[str]:
        pass

# loom/tools/base.py
class ToolExecutor(ABC):
    @abstractmethod
    async def execute(self, tool_name: str, **kwargs):
        pass

    @abstractmethod
    def list_tools(self) -> list:
        pass

# loom/capabilities/plugin.py
class PluginInterface(ABC):
    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def unload(self):
        pass
```

**影响**:
- 这些是正常的抽象基类定义
- 但需要确保所有子类都实现了这些方法

**建议**:
- 检查所有子类是否完整实现
- 添加类型注解和文档

---

### 22. Error 类只是空的占位符

**文件**: `loom/utils/errors.py:6-26`

**问题**:
```python
class LoomError(Exception):
    pass


class ConfigError(LoomError):
    pass


class ProviderError(LoomError):
    pass


class ToolError(LoomError):
    pass


class MemoryError(LoomError):
    pass
```

**影响**:
- 错误类没有额外的属性或方法
- 无法携带结构化的错误信息
- 无法区分错误的严重程度

**建议**:
- 添加 error_code, context, severity 等属性
- 实现 __str__ 和 __repr__ 方法
- 支持错误链和堆栈跟踪

---

### 23. Memory Store 接口过于简单

**文件**: `loom/memory/store.py:11-15`

**问题**:
```python
class MemoryStore(ABC):
    @abstractmethod
    def save(self, key: str, value: Any):
        pass

    @abstractmethod
    def load(self, key: str) -> Any:
        pass
```

**影响**:
- 没有 delete, list, exists 等基础操作
- 没有过期时间支持
- 没有批量操作
- 没有事务支持

**建议**:
- 扩展接口：delete(), list_keys(), exists(), clear()
- 添加 TTL 支持
- 添加批量操作：save_many(), load_many()
- 考虑添加事务支持

---

### 24. Tool Pipeline 的 execute 方法未实现

**文件**: `loom/tools/pipeline.py:96`

**问题**:
```python
class ToolPipeline:
    # ... 其他方法

    async def execute(self, tool_name: str, **kwargs):
        """Execute tool through pipeline"""
        pass  # 未实现
```

**影响**:
- Pipeline 定义了流程但无法执行
- 治理、权限检查等机制无法生效

**建议**:
- 实现完整的执行流程：
  1. 权限检查
  2. 治理检查
  3. Hook 触发
  4. 工具执行
  5. 结果处理
  6. 审计日志

---

### 25. AgentProfile.from_yaml() 实现了但未测试

**文件**: `loom/api/profile.py:40-60`

**当前实现**:
```python
@classmethod
def from_yaml(cls, path: str) -> "AgentProfile":
    """Load from YAML file"""
    data = _parse_yaml_file(path)

    config_data = data.get("config", {})
    config = AgentConfig(
        name=config_data.get("name", data.get("id", "default")),
        llm=LLMConfig(**config_data.get("llm", {})),
        tools=ToolConfig(**config_data.get("tools", {})),
        policy=PolicyConfig(**config_data.get("policy", {})),
        system_prompt=config_data.get("system_prompt", ""),
    )

    return cls(
        id=data["id"],
        name=data.get("name", data["id"]),
        config=config,
        skills=data.get("skills", []),
        knowledge_sources=data.get("knowledge_sources", []),
    )
```

**问题**:
- 实现了自定义的 YAML 解析器（_parse_yaml_file）
- 但 TODO.md 标记为 "not implemented"
- 可能是文档过期

**建议**:
- 更新 TODO.md
- 添加测试用例
- 考虑使用标准的 YAML 库（pyyaml）而非自定义解析器

---

### 26. 两个 Heartbeat 实现

**文件**:
- `loom/execution/heartbeat.py` (简单版本)
- `loom/runtime/heartbeat.py` (完整版本)

**问题**:
```python
# loom/execution/heartbeat.py - 简单版本
class Heartbeat:
    def __init__(self, config: HeartbeatConfig | None = None):
        self.config = config or HeartbeatConfig()
        self.monitors: list = []

    def tick(self) -> list[HeartbeatEvent]:
        """Execute heartbeat check"""
        # ...

# loom/runtime/heartbeat.py - 完整版本
class Heartbeat:
    def __init__(self, config: HeartbeatConfig):
        self.config = config
        self.running = False
        self.thread = None
        # ...

    def start(self, event_callback: Callable):
        """启动心跳线程"""
        # ...
```

**影响**:
- 两个不同的 Heartbeat 实现
- 功能重叠但接口不同
- 可能导致混淆

**建议**:
- 合并为一个实现
- 或者明确区分用途（同步 vs 异步）
- 统一接口

---

### 27. SubAgent 深度限制但没有更智能的终止条件

**文件**: `loom/orchestration/subagent.py:15-23`

**当前实现**:
```python
async def spawn(self, goal: str, depth: int, inherit_context: bool = True) -> SubAgentResult:
    """Spawn a sub-agent with recursion check."""
    if depth >= self.max_depth:
        return SubAgentResult(
            success=False,
            output="Max depth reached - 能力边界已穷尽",
            depth=depth,
            error="MAX_DEPTH_EXCEEDED",
        )
```

**问题**:
- 只有简单的深度限制
- 没有基于成本、时间、资源的限制
- 没有检测循环依赖
- 没有检测重复任务

**建议**:
- 添加成本预算限制
- 添加时间限制
- 检测任务相似度，避免重复
- 检测循环依赖

---

### 28. Coordinator 的结果聚合过于简单

**文件**: `loom/orchestration/coordinator.py:65-71`

**当前实现**:
```python
def aggregate_results(self, results: dict[str, SubAgentResult]) -> str:
    """Aggregate sub-agent outputs into one summary string."""
    ordered = []
    for task_id, result in results.items():
        status = "ok" if result.success else "error"
        ordered.append(f"[{task_id}:{status}] {result.output}")
    return "\n".join(ordered)
```

**问题**:
- 只是简单的字符串拼接
- 没有智能摘要
- 没有冲突检测
- 没有依赖关系处理

**建议**:
- 使用 LLM 进行智能摘要
- 检测结果之间的冲突
- 按依赖关系排序
- 提取关键信息

---

## 代码质量问题

### 29. 缺少类型注解的地方

多个文件中存在缺少类型注解的情况：

- `loom/runtime/monitors.py:19` - `self.monitors: list` 应该是 `list[Monitor]`
- `loom/execution/heartbeat.py:19` - 同样的问题
- 多个 `Any` 类型可以更具体

**建议**:
- 添加完整的类型注解
- 使用 mypy 进行类型检查
- 定义具体的类型而非 Any

---

### 30. 缺少文档字符串

部分方法缺少详细的文档字符串：

- 参数说明
- 返回值说明
- 异常说明
- 使用示例

**建议**:
- 为所有公共 API 添加完整的文档字符串
- 使用 Google 或 NumPy 风格
- 添加使用示例

---

## 总结

### 按优先级统计

- **P0 问题**: 4 个（核心运行时）
- **P1 问题**: 6 个（框架可用性）
- **P2 问题**: 10 个（高级能力）
- **其他问题**: 10 个（代码质量、重复实现等）

**总计**: 30 个需要改进的问题

---

### 关键发现

1. **Provider 实现不一致**: OpenAI 和 Anthropic 完整，Gemini 是 mock
2. **工具系统不完整**: web tools 是 mock，知识检索使用词法而非语义
3. **高级特性未实现**: Evolution, MCP 真实连接, Plugin hooks
4. **状态管理不完整**: Dashboard 只存储不决策，Renewal 只保存不恢复
5. **代码重复**: 两个 Heartbeat, 两个 PermissionManager
6. **接口过于简单**: MemoryStore, ToolPipeline, VetoAuthority

---

### 建议的实施顺序

#### 第一阶段：修复 P0 问题（1-2 周）
1. 实现 Gemini provider 或移除
2. 实现 RunHandle.resume() 逻辑
3. 完善 transcript() 结构化输出
4. 完善 SessionHandle.close() 资源清理

#### 第二阶段：完善 P1 问题（2-3 周）
5. 实现 web_fetch 和 web_search
6. 集成真实的 embedding 到知识检索
7. 实现 micro_compact 工具结果缓存
8. 增强工具治理的细粒度控制
9. 完善语义内存的索引和持久化
10. 增强 Planner 的智能任务分解

#### 第三阶段：完成 P2 问题（3-4 周）
11. 实现真实的 MCP 协议通信
12. 实现 Evolution strategies
13. 深度集成 Heartbeat 到运行循环
14. 实现 Context Renewal 的恢复逻辑
15. 实现 Dashboard 驱动的决策
16. 完善 Plugin 生态系统集成
17-20. 完善 Safety 系统

#### 第四阶段：代码质量提升（1-2 周）
21-30. 修复重复实现、添加类型注解、完善文档

---

### 成功标准

框架应该被认为是生产就绪的，当：

1. ✅ 所有 P0 问题已解决
2. ✅ 至少一个 provider 可以进行真实的模型调用
3. ✅ 核心工具（web, knowledge）可以实际工作
4. ✅ Run 生命周期完整且可靠
5. ✅ 没有明显的代码重复或冲突
6. ✅ 关键路径有完整的类型注解和文档
7. ✅ Wiki 中标记为"部分实现"的功能要么完成，要么明确标记为实验性

---

**文档生成时间**: 2026-04-03
**下次审查建议**: 每完成一个阶段后更新此文档

