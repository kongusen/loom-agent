# 运行时与任务模型

`loom/runtime/` 定义了框架的基础运行时组件，包括 Task 模型、状态管理和拦截器。

## 文件结构

```
loom/runtime/
├── task.py           # Task - A2A 协议任务模型
├── dispatcher.py     # 任务分发器
├── interceptor.py    # InterceptorChain - 拦截器链
├── session_lane.py   # SessionLaneInterceptor - Session 隔离
├── state_manager.py  # StateManager - 状态管理
├── state_store.py    # StateStore - 状态存储后端
├── state.py          # 状态定义
└── checkpoint.py     # CheckpointManager - 检查点恢复
```

## Task

Task 是框架的通信原语（公理 A2），基于 Google A2A 协议，使用 Pydantic BaseModel。

```python
class Task(BaseModel):
    taskId: str              # 任务唯一标识
    sourceAgent: str         # 发起 Agent ID
    targetAgent: str         # 目标 Agent ID
    action: str              # 动作（execute, plan, delegate...）
    parameters: dict         # 任务参数
    status: TaskStatus       # PENDING / RUNNING / COMPLETED / FAILED / CANCELLED
    createdAt: datetime      # 创建时间
    updatedAt: datetime      # 更新时间
    result: Any              # 任务结果
    error: str | None        # 错误信息
    metadata: dict           # 元数据（重要性、摘要、标签等）
    parentTaskId: str | None # 父任务 ID（分形架构）
    sessionId: str | None    # 会话 ID
```

### 命名约定

Task 使用驼峰命名（与 A2A 协议一致），同时提供蛇形命名的属性别名以兼容 Python 风格：

```python
task = Task(taskId="123", sourceAgent="agent-1")
task.taskId == task.task_id  # True（别名访问）
```

### 序列化

```python
# 导出为 A2A JSON
data = task.to_dict()

# 从字典创建（支持驼峰和蛇形输入）
task = Task.from_dict({"task_id": "123", "source_agent": "agent-1"})
task = Task.from_dict({"taskId": "123", "sourceAgent": "agent-1"})
```

## TaskStatus

```python
class TaskStatus(StrEnum):
    PENDING = "pending"       # 待处理
    RUNNING = "running"       # 运行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
```

## InterceptorChain

中间件模式，在任务执行前后插入处理逻辑：

```python
chain = InterceptorChain()
chain.add(SessionLaneInterceptor(mode=SessionIsolationMode.STRICT))
chain.add(custom_interceptor)

# 执行时自动经过拦截器链
result = await chain.execute(task, actual_handler)
```

## SessionLaneInterceptor

确保同一 Session 内的任务串行执行，防止并发冲突：

```python
class SessionIsolationMode(StrEnum):
    STRICT = "strict"       # 强制串行（asyncio.Lock）
    ADVISORY = "advisory"   # 仅警告
    NONE = "none"           # 无控制
```

## CheckpointManager

支持任务中断后恢复执行：

```python
agent = Agent.create(
    llm,
    enable_checkpoint=True,
    state_store=MemoryStateStore(),  # 或自定义存储后端
)
```

### StateStore

状态存储后端抽象：

| 实现 | 说明 |
|------|------|
| `MemoryStateStore` | 内存存储（默认，重启丢失） |
| 自定义 | 实现 `StateStore` 接口（Redis、数据库等） |
