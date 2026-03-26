# Loom v0.8.0 优化方案
## 基于 Agent 公理系统 v2.2

---

## 当前状态评估

### Loom 当前能力等级：L1.5

| 能力层 | 要求 | Loom 状态 | 完成度 |
|--------|------|-----------|--------|
| L0 基础 | Context + Memory + Loop | ✅ 完整 | 100% |
| L1 可续存 | 外部持久化 + 状态管理 | ✅ 完整 | 100% |
| L2 受约束 | Scene + 边界 + 约束 | ⚠️ 部分 | 40% |
| L3 可验证 | Verifier + 事件日志 | ❌ 缺失 | 0% |

### 核心问题（基于 v2.2 视角）

**P0 - 热路径旁路**
- `ToolUseStrategy` 直接调用 `ToolRegistry.execute()`
- 绕过了 `Agent._execute_tool()` 的所有控制逻辑
- 导致 L2 的约束检查、边界响应、状态更新都不生效

**P1 - Scene 组合语义错误**
- 使用字典覆盖而非"约束收窄"
- 违反 v2.2 的 I4（边界响应不变量）

**P2 - 缺少 L3 基础设施**
- 无 Verifier 接口
- 无事件日志（共享记忆是可变字典）
- 无完成证据收集

---

## 优化目标

### 短期目标（v0.8.0）
**完成 L2 层能力** - 成为完整的"受约束 Agent"

### 中期目标（v0.9.0）
**实现 L3 基础** - 支持验证和多 Agent 协作

### 长期目标（v1.0.0）
**生产就绪** - 完整的 L3 能力 + 性能优化

---

## v0.8.0 实施方案（L2 完成）

### 阶段 1: 修复热路径（P0）

**目标**: 所有工具调用必须经过统一控制点

#### 1.1 创建 StepExecutor

```python
# loom/agent/step_executor.py

class StepExecutor:
    """统一的步骤执行器 - 所有工具调用的唯一入口"""

    def __init__(
        self,
        agent: "Agent",
        tool_registry: ToolRegistry,
        constraint_validator: ConstraintValidator,
        resource_guard: ResourceGuard,
    ):
        self.agent = agent
        self.tools = tool_registry
        self.validator = constraint_validator
        self.guard = resource_guard

    async def execute_step(
        self, tool_call: ToolCall, ctx: ToolContext
    ) -> StepResult:
        """执行单步 - 集成所有检查和更新"""

        # 1. 资源配额检查
        within_quota, msg = self.guard.check_quota()
        if not within_quota:
            return StepResult(error=msg)

        # 2. 约束验证（L2）
        is_valid, error = self.validator.validate_before_call(tool_call)
        if not is_valid:
            return StepResult(error=error)

        # 3. 执行工具
        result = await self.tools.execute(tool_call, ctx)

        # 4. 记录轨迹
        self.agent._execution_trace.append(
            f"{tool_call.name}({tool_call.arguments[:50]}) → {result[:100]}"
        )

        # 5. 更新 working 分区
        working = self.agent._build_working_state()
        self.agent.partition_mgr.update_partition("working", working)

        # 6. 过滤输出（可选 - 信息增益）
        filtered = await self._filter_output(tool_call.name, result)

        return StepResult(output=filtered)


class StepResult:
    output: Optional[str] = None
    error: Optional[str] = None
```

#### 1.2 修改 ToolUseStrategy

```python
# loom/agent/strategy.py

class ToolUseStrategy(LoopStrategy):
    async def execute(self, ctx: LoopContext) -> AsyncGenerator[AgentEvent, None]:
        # 创建 StepExecutor
        executor = StepExecutor(
            agent=ctx.agent,  # 需要在 LoopContext 中传递
            tool_registry=ctx.tool_registry,
            constraint_validator=ctx.constraint_validator,
            resource_guard=ctx.resource_guard,
        )

        for step in range(ctx.max_steps):
            # ... LLM 调用 ...

            if tool_calls:
                for tc in tool_calls:
                    # 统一入口
                    result = await executor.execute_step(tc, ctx.tool_context)

                    if result.error:
                        yield ToolErrorEvent(...)
                    else:
                        yield ToolResultEvent(...)
```

#### 1.3 修改 Agent

```python
# loom/agent/core.py

class Agent:
    async def stream(self, input_text: str, signal: Any = None):
        # ...

        ctx = LoopContext(
            # ... 现有参数 ...
            agent=self,  # 新增
            constraint_validator=self.constraint_validator,  # 新增
            resource_guard=self.resource_guard,  # 新增
        )

        async for event in self.strategy.execute(ctx):
            yield await self._emit(event)
```

**验收标准**:
- ✅ 所有工具调用经过 StepExecutor
- ✅ 约束检查在热路径生效
- ✅ 执行轨迹正确记录
- ✅ Working 分区正确更新

---

### 阶段 2: 修正 Scene 组合（P1）

**目标**: Scene 组合时约束收窄而非放宽

#### 2.1 修改 ScenePackage.__add__

```python
# loom/scene/scene.py

class ScenePackage:
    def __add__(self, other: "ScenePackage") -> "ScenePackage":
        """组合场景 - 约束取交集（更严格）"""

        # 工具取并集
        combined_tools = list(set(self.tools) | set(other.tools))

        # 约束取交集（更严格的约束）
        combined_constraints = self._merge_constraints(
            self.constraints, other.constraints
        )

        return ScenePackage(
            id=f"{self.id}+{other.id}",
            tools=combined_tools,
            constraints=combined_constraints,
        )

    def _merge_constraints(self, c1: Dict, c2: Dict) -> Dict:
        """合并约束 - 取更严格的值"""
        merged = {}

        all_keys = set(c1.keys()) | set(c2.keys())

        for key in all_keys:
            v1 = c1.get(key)
            v2 = c2.get(key)

            if v1 is None:
                merged[key] = v2
            elif v2 is None:
                merged[key] = v1
            else:
                # 布尔约束：两者都允许才允许
                if isinstance(v1, bool) and isinstance(v2, bool):
                    merged[key] = v1 and v2
                # 数值约束：取更小的限制
                elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    merged[key] = min(v1, v2)
                # 列表约束：取交集
                elif isinstance(v1, list) and isinstance(v2, list):
                    merged[key] = list(set(v1) & set(v2))
                else:
                    # 默认：保留第一个
                    merged[key] = v1

        return merged
```

#### 2.2 添加测试

```python
# tests/unit/test_scene_composition.py

async def test_scene_composition_tightens_constraints():
    """验证场景组合时约束收窄"""
    scene1 = ScenePackage(
        id="s1",
        tools=["read", "write"],
        constraints={"network": True, "max_tokens": 1000}
    )

    scene2 = ScenePackage(
        id="s2",
        tools=["write", "bash"],
        constraints={"network": False, "max_tokens": 500}
    )

    combined = scene1 + scene2

    # 工具取并集
    assert set(combined.tools) == {"read", "write", "bash"}

    # 约束取更严格的
    assert combined.constraints["network"] is False  # False 更严格
    assert combined.constraints["max_tokens"] == 500  # 更小的限制
```

**验收标准**:
- ✅ 布尔约束：AND 逻辑
- ✅ 数值约束：取最小值
- ✅ 列表约束：取交集
- ✅ 测试覆盖所有组合情况

---

### 阶段 3: 边界检测和响应（L2 核心）

**目标**: 实现 v2.2 的 I4（边界响应不变量）

#### 3.1 定义边界类型

```python
# loom/agent/boundary.py

from enum import Enum

class BoundaryType(Enum):
    PHYSICAL = "physical"      # token/memory 耗尽
    PERMISSION = "permission"  # 缺少权限
    CAPABILITY = "capability"  # 超出能力
    TIME = "time"              # 超时

class BoundaryResponse(Enum):
    RENEW = "renew"           # 压缩继续
    WAIT = "wait"             # 等待输入
    HANDOFF = "handoff"       # 转交
    DECOMPOSE = "decompose"   # 拆解
    STOP = "stop"             # 终止

class BoundaryDetector:
    """边界检测器"""

    def __init__(self, partition_mgr, resource_guard, scene_mgr):
        self.partition_mgr = partition_mgr
        self.guard = resource_guard
        self.scene_mgr = scene_mgr

    def detect(self) -> Optional[Tuple[BoundaryType, Dict]]:
        """检测是否触及边界"""

        # 物理边界
        if self.partition_mgr.compute_decay() > 0.9:
            return (BoundaryType.PHYSICAL, {"reason": "context_full"})

        within_quota, msg = self.guard.check_quota()
        if not within_quota:
            return (BoundaryType.PHYSICAL, {"reason": msg})

        # 时间边界
        if self.guard.is_timeout():
            return (BoundaryType.TIME, {"reason": "timeout"})

        return None

class BoundaryHandler:
    """边界响应处理器"""

    def __init__(self, agent: "Agent"):
        self.agent = agent
        self.policy = self._default_policy()

    def _default_policy(self) -> Dict[BoundaryType, List[BoundaryResponse]]:
        """默认响应策略"""
        return {
            BoundaryType.PHYSICAL: [BoundaryResponse.RENEW, BoundaryResponse.STOP],
            BoundaryType.PERMISSION: [BoundaryResponse.WAIT, BoundaryResponse.HANDOFF],
            BoundaryType.CAPABILITY: [BoundaryResponse.DECOMPOSE, BoundaryResponse.HANDOFF],
            BoundaryType.TIME: [BoundaryResponse.STOP, BoundaryResponse.HANDOFF],
        }

    async def handle(
        self, boundary_type: BoundaryType, context: Dict
    ) -> BoundaryResponse:
        """处理边界触发"""

        responses = self.policy.get(boundary_type, [BoundaryResponse.STOP])

        # 简单策略：选择第一个可用响应
        for response in responses:
            if response == BoundaryResponse.RENEW:
                if await self._can_renew():
                    await self._do_renew()
                    return response

            elif response == BoundaryResponse.STOP:
                return response

        return BoundaryResponse.STOP

    async def _can_renew(self) -> bool:
        """检查是否可以续存"""
        # 检查是否有足够的压缩空间
        return self.agent.partition_mgr.compute_decay() < 1.0

    async def _do_renew(self):
        """执行续存操作"""
        await self.agent._trigger_compression()
```

#### 3.2 集成到 Agent

```python
# loom/agent/core.py

class Agent:
    def __init__(self, ...):
        # ...
        self.boundary_detector = BoundaryDetector(
            self.partition_mgr, self.resource_guard, self.scene_mgr
        )
        self.boundary_handler = BoundaryHandler(self)

    async def stream(self, input_text: str, signal: Any = None):
        # ...

        for step in range(max_steps):
            # 1. 检查边界
            boundary = self.boundary_detector.detect()
            if boundary:
                boundary_type, context = boundary
                response = await self.boundary_handler.handle(boundary_type, context)

                if response == BoundaryResponse.STOP:
                    yield BoundaryEvent(type=boundary_type, response=response)
                    break
                elif response == BoundaryResponse.RENEW:
                    yield BoundaryEvent(type=boundary_type, response=response)
                    continue  # 续存后继续

            # 2. 正常执行
            # ...
```

**验收标准**:
- ✅ 物理边界可检测
- ✅ 时间边界可检测
- ✅ 边界触发时有明确响应
- ✅ RENEW 响应可以压缩继续

---

### 阶段 4: WorkingState 结构化（L1 增强）

**目标**: 实现 v2.2 的预算化灵活结构

#### 4.1 定义 WorkingState

```python
# loom/types/working.py

from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class WorkingState:
    """工作状态 - 预算化的灵活结构"""

    budget: int = 2000  # token 预算

    # 推荐 schema（非强制）
    goal: Optional[str] = None
    plan: Optional[str] = None
    progress: Optional[Dict] = None
    blockers: Optional[List[str]] = None
    next_action: Optional[str] = None

    # 自由内容（计入预算）
    overflow: str = ""

    def to_text(self, tokenizer) -> str:
        """转换为文本（受预算限制）"""
        parts = []

        if self.goal:
            parts.append(f"<goal>{self.goal}</goal>")

        if self.plan:
            parts.append(f"<plan>{self.plan}</plan>")

        if self.progress:
            parts.append(f"<progress>{self.progress}</progress>")

        if self.blockers:
            parts.append(f"<blockers>{', '.join(self.blockers)}</blockers>")

        if self.next_action:
            parts.append(f"<next_action>{self.next_action}</next_action>")

        if self.overflow:
            parts.append(f"<overflow>{self.overflow}</overflow>")

        text = "\n".join(parts)

        # 截断到预算
        return tokenizer.truncate(text, self.budget)

    @classmethod
    def from_text(cls, text: str) -> "WorkingState":
        """从文本解析（尽力而为）"""
        import re

        state = cls()

        # 尝试提取结构化字段
        if match := re.search(r"<goal>(.*?)</goal>", text, re.DOTALL):
            state.goal = match.group(1).strip()

        if match := re.search(r"<plan>(.*?)</plan>", text, re.DOTALL):
            state.plan = match.group(1).strip()

        # ... 其他字段 ...

        # 剩余内容放入 overflow
        structured = re.sub(r"<\w+>.*?</\w+>", "", text, flags=re.DOTALL)
        state.overflow = structured.strip()

        return state
```

#### 4.2 修改 Agent 使用 WorkingState

```python
# loom/agent/core.py

class Agent:
    def __init__(self, ...):
        # ...
        self.working_state = WorkingState(budget=2000)

    def _build_working_state(self) -> str:
        """构建 working 分区内容"""
        # 更新结构化字段
        self.working_state.goal = self._goal

        # 更新最近动作
        recent = self._execution_trace[-3:] if self._execution_trace else []
        if recent:
            self.working_state.overflow = "\n".join(recent)

        # 转换为文本（自动截断）
        return self.working_state.to_text(self.tokenizer)
```

**验收标准**:
- ✅ WorkingState 有固定预算
- ✅ 支持推荐 schema
- ✅ 支持 overflow 自由内容
- ✅ 超出预算自动截断

---

## 阶段总结

完成以上 4 个阶段后，Loom 将达到 **L2 完整** 水平：

| 能力 | 状态 |
|------|------|
| ✅ 统一执行入口 | StepExecutor |
| ✅ 约束检查生效 | 热路径集成 |
| ✅ Scene 组合正确 | 约束收窄 |
| ✅ 边界检测响应 | 4 类边界 + 策略 |
| ✅ 工作状态结构化 | 预算化 WorkingState |

---

## 测试策略

### 单元测试
- `test_step_executor.py` - 执行器逻辑
- `test_scene_composition.py` - 场景组合
- `test_boundary_detection.py` - 边界检测
- `test_working_state.py` - 工作状态

### 集成测试
- `test_constraint_in_loop.py` - 约束在循环中生效
- `test_boundary_in_loop.py` - 边界触发和响应
- `test_working_state_update.py` - 工作状态更新

### 端到端测试
- `test_full_agent_l2.py` - 完整 L2 Agent 运行

---

## 下一步（v0.9.0 - L3 基础）

完成 L2 后，可选择性实现 L3 能力：

1. **Verifier 接口** - 支持外部验证
2. **事件日志** - 替代可变字典
3. **证据收集** - 完成时提供证据
4. **冲突检测** - 多 Agent 协作

但这些都是**可选增强**，不影响 L2 的完整性。

---

*Loom v0.8.0 Roadmap · 完*
