# Phase 4: 公理四自我进化闭环实施方案

## 目标
将 E1/E2 工具从"占位实现"升级为"完全可用的自我进化机制"。

---

## 4.1 核心变更：实现 E1 工具 handler

### 当前问题
```python
# loom/tools/agent_tools.py
async def _not_implemented(_params: Any, _ctx: Any) -> str:
    return "Tool factory created a definition, but no executor is wired for this runtime."
```

### 新实现：write_memory handler
```python
# loom/agent/evolution_handlers.py

async def write_memory_handler(params: dict, ctx: ToolContext, agent: Agent) -> str:
    """E1: 写入长期记忆"""
    content = params.get("content", "")
    importance = params.get("importance", 0.7)

    if not content:
        return "Error: content is required"

    # 创建记忆条目
    entry = MemoryEntry(
        content=content,
        importance=importance,
        tokens=agent.tokenizer.count(content),
        metadata={"source": "agent_tool", "timestamp": time.time()}
    )

    # 写入 L2（长期记忆）
    await agent.memory.l2.store(entry)

    # 如果重要度很高，同时写入 L3
    if importance >= 0.9:
        await agent.memory.l3.store(entry)

    return f"Memory stored (importance={importance:.2f})"
```

---

## 4.2 实现 E2 工具 handler

### activate_skill handler
```python
async def activate_skill_handler(params: dict, ctx: ToolContext, agent: Agent) -> str:
    """E2: 激活技能"""
    skill_name = params.get("skill_name", "")

    if not skill_name:
        return "Error: skill_name is required"

    # 检查技能是否存在
    skill = agent.skill_mgr.registry.get(skill_name)
    if not skill:
        available = [s.name for s in agent.skill_mgr.registry.all()]
        return f"Skill '{skill_name}' not found. Available: {', '.join(available)}"

    # 检查预算
    budget = agent.partition_mgr.get_available_budget("skill")
    skill_tokens = agent.tokenizer.count(skill.instructions)

    if skill_tokens > budget:
        return f"Insufficient budget: skill needs {skill_tokens} tokens, only {budget} available"

    # 激活技能
    activated = agent.skill_mgr.activate(skill_name)
    if not activated:
        return f"Failed to activate skill '{skill_name}'"

    # 更新 C_skill 分区
    skill_context = agent.skill_mgr.get_context(budget)
    agent.partition_mgr.update_partition("skill", skill_context)

    return f"Skill '{skill_name}' activated ({skill_tokens} tokens)"
```

### deactivate_skill handler
```python
async def deactivate_skill_handler(params: dict, ctx: ToolContext, agent: Agent) -> str:
    """E2: 停用技能"""
    skill_name = params.get("skill_name", "")

    if not skill_name:
        return "Error: skill_name is required"

    # 停用技能
    deactivated = agent.skill_mgr.deactivate(skill_name)
    if not deactivated:
        return f"Skill '{skill_name}' was not active"

    # 更新 C_skill 分区
    budget = agent.partition_mgr.get_available_budget("skill")
    skill_context = agent.skill_mgr.get_context(budget)
    agent.partition_mgr.update_partition("skill", skill_context)

    return f"Skill '{skill_name}' deactivated"
```

---

## 4.3 自动注册 E1/E2 工具

### 修改 agent_tools.py
```python
# loom/tools/agent_tools.py

def create_memory_tools(agent: Agent) -> list[ToolDefinition]:
    """创建记忆管理工具（绑定到 Agent）"""
    from ..agent.evolution_handlers import write_memory_handler

    return [
        ToolDefinition(
            name="write_memory",
            description="Write important information to long-term memory",
            parameters=DictSchema({
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to remember"},
                    "importance": {"type": "number", "description": "Importance score (0-1)", "default": 0.7},
                },
                "required": ["content"],
            }),
            execute=lambda params, ctx: write_memory_handler(params, ctx, agent),
        )
    ]

def create_skill_tools(agent: Agent) -> list[ToolDefinition]:
    """创建技能管理工具（绑定到 Agent）"""
    from ..agent.evolution_handlers import activate_skill_handler, deactivate_skill_handler

    return [
        ToolDefinition(
            name="activate_skill",
            description="Activate a skill to use its capabilities",
            parameters=DictSchema({
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of skill to activate"},
                },
                "required": ["skill_name"],
            }),
            execute=lambda params, ctx: activate_skill_handler(params, ctx, agent),
        ),
        ToolDefinition(
            name="deactivate_skill",
            description="Deactivate a skill to free up context budget",
            parameters=DictSchema({
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of skill to deactivate"},
                },
                "required": ["skill_name"],
            }),
            execute=lambda params, ctx: deactivate_skill_handler(params, ctx, agent),
        ),
    ]
```

---

## 4.4 Agent 自动注册工具

```python
# loom/agent/core.py

def __init__(self, ...):
    # ... 现有初始化

    # 公理四：自动注册 E1/E2 工具
    self._register_evolution_tools()

def _register_evolution_tools(self) -> None:
    """自动注册进化工具"""
    from ..tools.agent_tools import create_memory_tools, create_skill_tools

    # E1: 记忆工具
    for tool in create_memory_tools(self):
        self.tools.register(tool)

    # E2: 技能工具
    for tool in create_skill_tools(self):
        self.tools.register(tool)
```

---

## 4.5 集成 RewardBus 评估

### 在任务结束时评估
```python
async def run(self, user_input: str, goal: str = "") -> AsyncGenerator[AgentEvent, None]:
    """主循环（集成 reward 评估）"""

    start_time = time.time()
    success = False
    token_cost = 0
    error_count = 0

    try:
        # ... 主循环逻辑

        # 标记成功
        success = True

    except Exception as e:
        error_count += 1
        yield ErrorEvent(error=str(e), recoverable=False)

    finally:
        # 计算 token 消耗
        token_cost = self.partition_mgr.get_total_tokens()

        # 公理四：评估并更新能力
        if hasattr(self, '_agent_node'):
            # 创建任务广告（用于评估）
            task_ad = TaskAd(
                task_id=uuid.uuid4().hex[:8],
                domain="general",
                estimated_complexity=1.0,
                token_budget=self.config.max_tokens or 100000,
            )

            # 评估
            reward = self.reward_bus.evaluate(
                self._agent_node,
                task_ad,
                success=success,
                token_cost=token_cost,
                error_count=error_count,
            )

            # 触发进化（如果 reward 低于阈值）
            await self._maybe_trigger_evolution(reward)
```

---

## 4.6 实现进化触发逻辑

```python
async def _maybe_trigger_evolution(self, reward: float) -> None:
    """根据 reward 触发进化"""

    # 检查是否需要进化
    if not hasattr(self, '_agent_node'):
        return

    node = self._agent_node
    recent_rewards = [r.reward for r in node.reward_history[-5:]]

    if len(recent_rewards) < 5:
        return

    avg_reward = sum(recent_rewards) / len(recent_rewards)

    # 低于阈值：触发 E1 结晶化
    if avg_reward < 0.35:
        await self._trigger_e1_crystallization()

    # 连续低分：触发 E2 结晶化
    if node.consecutive_losses >= 3:
        await self._trigger_e2_crystallization()

async def _trigger_e1_crystallization(self) -> None:
    """E1: 记忆结晶化"""
    # 从 L1 提取高价值记忆
    history = self.memory.get_history()
    important_msgs = [m for m in history if self._is_important_message(m)]

    # 结晶化为长期记忆
    for msg in important_msgs:
        entry = MemoryEntry(
            content=str(msg.content),
            importance=0.8,
            tokens=self.tokenizer.count(str(msg.content)),
            metadata={"source": "e1_crystallization"}
        )
        await self.memory.l2.store(entry)

async def _trigger_e2_crystallization(self) -> None:
    """E2: 技能结晶化"""
    # 分析执行轨迹，提取模式
    patterns = self._extract_patterns_from_trace()

    # 如果发现新模式，创建新技能（简化实现）
    if patterns:
        # 这里可以调用 BlueprintForge 生成新技能
        pass

def _is_important_message(self, msg: Message) -> bool:
    """判断消息是否重要"""
    content = str(msg.content)
    # 简单启发式：包含工具调用或长内容
    return len(content) > 100 or "tool_call" in content.lower()
```

---

## 4.7 测试验证

```python
# tests/unit/test_evolution_integration.py

async def test_write_memory_tool():
    """验证 write_memory 工具可用"""
    agent = Agent(provider=MockProvider())

    # 调用工具
    result = await agent._execute_tool(
        ToolCall(
            name="write_memory",
            arguments='{"content": "Important fact", "importance": 0.9}'
        )
    )

    assert "Memory stored" in result

    # 验证记忆已写入 L2
    entries = await agent.memory.l2.retrieve("Important", limit=10)
    assert any("Important fact" in e.content for e in entries)

async def test_activate_skill_tool():
    """验证 activate_skill 工具可用"""
    agent = Agent(provider=MockProvider())

    # 注册测试技能
    skill = Skill(name="test_skill", description="Test", instructions="Do test")
    agent.skill_mgr.registry.register(skill)

    # 激活技能
    result = await agent._execute_tool(
        ToolCall(name="activate_skill", arguments='{"skill_name": "test_skill"}')
    )

    assert "activated" in result

    # 验证 C_skill 分区已更新
    skill_content = agent.partition_mgr.partitions["skill"].content
    assert "test_skill" in skill_content

async def test_evolution_triggered_on_low_reward():
    """验证低 reward 触发进化"""
    agent = Agent(provider=MockProvider())
    agent._agent_node = AgentNode(
        id="test",
        capabilities=CapabilityProfile(),
        reward_history=[],
    )

    # 模拟连续低分
    for _ in range(5):
        agent._agent_node.reward_history.append(
            RewardRecord(task_id="t", reward=0.2, domain="test", token_cost=100)
        )

    # 触发进化检查
    await agent._maybe_trigger_evolution(0.2)

    # 验证 E1 被触发（检查 L2 是否有新记忆）
    # 这里需要 mock 或检查日志
```

---

## 4.8 实施检查清单

- [ ] 创建 evolution_handlers.py 文件
- [ ] 实现 write_memory_handler
- [ ] 实现 activate_skill_handler
- [ ] 实现 deactivate_skill_handler
- [ ] 修改 agent_tools.py 绑定 handler
- [ ] Agent 自动注册 E1/E2 工具
- [ ] 集成 RewardBus 到 run() 方法
- [ ] 实现 _maybe_trigger_evolution
- [ ] 实现 E1/E2 结晶化逻辑
- [ ] 编写进化集成测试
- [ ] 验证工具完全可用

---

**下一步：Phase 5 清理向后兼容代码**
