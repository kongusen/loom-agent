# Phase 2: 公理二约束前置实施方案

## 目标
将场景约束从"可选验证"升级为"强制前置检查"，所有工具调用必须通过约束验证。

---

## 2.1 核心变更：ToolRegistry.execute() 集成约束

### 当前问题
```python
# loom/tools/registry.py
async def execute(self, tool_call: ToolCall, ctx: ToolContext) -> str:
    # 直接执行，无约束检查
    tool = self._tools.get(tool_call.name)
    result = await tool.execute(params, ctx)
    return result
```

**问题：**
- ConstraintValidator 存在但未被调用
- 工具可以绕过场景约束执行

### 新实现
```python
async def execute(
    self,
    tool_call: ToolCall,
    ctx: ToolContext,
    constraint_validator: ConstraintValidator | None = None
) -> str:
    """执行工具（带约束前置验证）"""

    # P0: 约束前置验证
    if constraint_validator:
        is_valid = constraint_validator.validate(tool_call)
        if not is_valid:
            return f"[CONSTRAINT_VIOLATION] Tool '{tool_call.name}' blocked by scene constraints"

    # 执行工具
    tool = self._tools.get(tool_call.name)
    if not tool:
        return f"Tool '{tool_call.name}' not found"

    params = json.loads(tool_call.arguments) if isinstance(tool_call.arguments, str) else tool_call.arguments
    result = await tool.execute(params, ctx)

    return result
```

---

## 2.2 修改：Agent._execute_tool() 传递 validator

```python
async def _execute_tool(self, tc: ToolCall) -> str:
    """执行工具（集成约束验证）"""

    ctx = ToolContext(agent_id=self.id)

    # 传递 constraint_validator
    result = await self.tools.execute(
        tc,
        ctx,
        constraint_validator=self.constraint_validator
    )

    # 记录执行
    self._execution_trace.append(f"{tc.name}({tc.arguments}) → {result[:100]}")

    # 更新 working 分区
    working_content = self._build_working_state()
    self.partition_mgr.update_partition("working", working_content)

    return result
```

---

## 2.3 新增：场景切换自动更新 C_system

### 当前问题
场景切换后，system 分区不会自动更新。

### 新实现
```python
# loom/scene/manager.py

class SceneManager:
    def __init__(self):
        self._scenes: dict[str, Scene] = {}
        self.current_scene: Scene | None = None
        self._on_scene_change: list[Callable[[Scene], None]] = []

    def on_scene_change(self, callback: Callable[[Scene], None]) -> None:
        """注册场景切换回调"""
        self._on_scene_change.append(callback)

    def activate_scene(self, scene_id: str) -> bool:
        """激活场景并触发回调"""
        scene = self._scenes.get(scene_id)
        if not scene:
            return False

        self.current_scene = scene

        # 触发回调（通知 Agent 更新 C_system）
        for callback in self._on_scene_change:
            callback(scene)

        return True
```

### Agent 集成
```python
# loom/agent/core.py

def __init__(self, ...):
    # ...
    self.scene_mgr = SceneManager()

    # 注册场景切换回调
    self.scene_mgr.on_scene_change(self._on_scene_changed)

def _on_scene_changed(self, scene: Scene) -> None:
    """场景切换时自动更新 C_system"""
    system_content = self.config.system_prompt
    if scene:
        system_content += "\n\n" + scene.system_prompt_additions

    self.partition_mgr.update_partition("system", system_content)
    self._history_dirty = True  # 标记需要重建
```

---

## 2.4 增强：ConstraintValidator 支持动态约束

### 当前实现
```python
# loom/agent/constraint_validator.py
def validate(self, tool_call: ToolCall) -> bool:
    # 只检查静态约束
    constraints = self.scene_mgr.current_scene.constraints if self.scene_mgr.current_scene else {}
    # ...
```

### 增强实现
```python
def validate(self, tool_call: ToolCall, context: dict | None = None) -> bool:
    """验证工具调用（支持动态约束）"""

    if not self.scene_mgr.current_scene:
        return True

    constraints = self.scene_mgr.current_scene.constraints

    # 静态约束：网络
    if constraints.get("network") is False and tool_call.name in ["web_search", "web_fetch", "http_request"]:
        return False

    # 静态约束：文件系统
    if constraints.get("filesystem") is False and tool_call.name in ["read_file", "write_file", "list_dir"]:
        return False

    # 动态约束：基于上下文
    if context:
        # 例如：检查 token 预算
        if "token_budget" in constraints:
            used_tokens = context.get("used_tokens", 0)
            if used_tokens > constraints["token_budget"]:
                return False

        # 例如：检查时间限制
        if "max_duration_sec" in constraints:
            elapsed = context.get("elapsed_sec", 0)
            if elapsed > constraints["max_duration_sec"]:
                return False

    return True
```

---

## 2.5 新增：ResourceGuard 集成到主循环

### 当前问题
ResourceGuard 存在但未在主循环中调用。

### 新实现
```python
# loom/agent/core.py

async def run(self, user_input: str, goal: str = "") -> AsyncGenerator[AgentEvent, None]:
    """主执行循环（集成 ResourceGuard）"""

    # P0: 启动资源守卫
    self.resource_guard.start()

    try:
        # ... 主循环逻辑

        for turn in range(self.config.max_turns):
            # P0: 检查资源配额
            if not self.resource_guard.check():
                yield ErrorEvent(
                    error="Resource limit exceeded (tokens or time)",
                    recoverable=False
                )
                break

            # 构建消息
            messages = await self._build_messages()

            # 更新已用 token
            total_tokens = self.partition_mgr.get_total_tokens()
            self.resource_guard.consume_tokens(total_tokens)

            # LLM 调用
            # ...

    finally:
        # P0: 停止资源守卫
        self.resource_guard.stop()
```

---

## 2.6 测试验证

```python
# tests/unit/test_constraint_integration.py

async def test_tool_blocked_by_scene_constraint():
    """验证场景约束阻止工具执行"""
    agent = Agent(provider=MockProvider())

    # 激活禁止网络的场景
    scene = Scene(
        id="offline",
        constraints={"network": False}
    )
    agent.scene_mgr.register_scene(scene)
    agent.scene_mgr.activate_scene("offline")

    # 尝试调用网络工具
    result = await agent._execute_tool(
        ToolCall(name="web_search", arguments='{"query": "test"}')
    )

    assert "CONSTRAINT_VIOLATION" in result

async def test_scene_change_updates_system_partition():
    """验证场景切换自动更新 C_system"""
    agent = Agent(provider=MockProvider())

    scene = Scene(
        id="test",
        system_prompt_additions="You are in test mode."
    )
    agent.scene_mgr.register_scene(scene)

    # 切换场景
    agent.scene_mgr.activate_scene("test")

    # 验证 C_system 已更新
    system_content = agent.partition_mgr.partitions["system"].content
    assert "test mode" in system_content

async def test_resource_guard_stops_execution():
    """验证 ResourceGuard 阻止超预算执行"""
    agent = Agent(provider=MockProvider())
    agent.resource_guard = ResourceGuard(max_tokens=100, max_time_sec=1)

    # 模拟超预算
    agent.partition_mgr.partitions["history"].tokens = 150

    events = []
    async for event in agent.run("test"):
        events.append(event)

    # 验证有错误事件
    assert any(isinstance(e, ErrorEvent) for e in events)
```

---

## 2.7 实施检查清单

- [ ] 修改 ToolRegistry.execute() 集成 constraint_validator
- [ ] 修改 Agent._execute_tool() 传递 validator
- [ ] SceneManager 添加 on_scene_change 回调机制
- [ ] Agent 注册场景切换回调更新 C_system
- [ ] 增强 ConstraintValidator 支持动态约束
- [ ] ResourceGuard 集成到 Agent.run() 主循环
- [ ] 编写约束集成测试
- [ ] 验证所有场景约束生效

---

**下一步：Phase 3 公理三门控方案**
