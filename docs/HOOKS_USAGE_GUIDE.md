# Loom Agent 钩子（Hooks）使用指南

## 目录

1. [概述](#概述)
2. [钩子系统架构](#钩子系统架构)
3. [9个钩子点详解](#9个钩子点详解)
4. [内置钩子](#内置钩子)
5. [自定义钩子](#自定义钩子)
6. [高级用法](#高级用法)
7. [最佳实践](#最佳实践)
8. [完整示例](#完整示例)

---

## 概述

### 什么是钩子？

钩子（Hooks）是 Loom Agent 框架中的**生命周期拦截点**，允许你在 Agent 执行的特定阶段插入自定义逻辑，而无需修改核心执行代码。

### 设计理念

- **中间件模式**：通过钩子而非显式图连接实现控制流
- **Pythonic 设计**：使用 Python Protocol，无需继承基类
- **可选实现**：只需实现你需要的钩子方法
- **链式执行**：支持多个钩子按顺序执行

### 核心优势

1. **Human-in-the-Loop (HITL)**：在执行危险操作前暂停并等待用户确认
2. **日志和监控**：跟踪执行过程，收集指标
3. **动态路由**：根据状态影响决策
4. **上下文注入**：在特定阶段添加额外上下文
5. **错误处理**：自定义恢复策略

### 与 LangGraph 的对比

| LangGraph | Loom Agent |
|-----------|------------|
| `graph.add_conditional_edges("node", router_function)` | `agent(hooks=[MyHook()])` |
| 显式图结构 | 隐式钩子链 |
| 需要定义节点和边 | 只需实现钩子方法 |

---

## 钩子系统架构

### 执行流程

```
loom.agent(hooks=[hook1, hook2, ...])
  ↓
Agent.__init__(hooks=[...])
  ↓
AgentExecutor.__init__(hooks=[...])
  ↓
HookManager(hooks)
  ↓
在 tt 递归循环的各个阶段调用钩子
```

### HookManager 工作原理

`HookManager` 负责协调多个钩子的执行：

1. **顺序执行**：按列表顺序依次调用每个钩子
2. **结果传递**：前一个钩子的返回值作为下一个钩子的输入
3. **异常处理**：捕获 `InterruptException` 和 `SkipToolException`
4. **链式修改**：每个钩子可以修改数据，传递给下一个

---

## 9个钩子点详解

### 执行顺序图

```
一次 tt 迭代的完整流程：

1. before_iteration_start(frame)
   ↓
2. before_context_assembly(frame)
   ↓
3. after_context_assembly(frame, context_snapshot, context_metadata)
   ↓
4. before_llm_call(frame, messages)
   ↓
5. after_llm_response(frame, response, tool_calls)
   ↓
6. before_tool_execution(frame, tool_call)  ← 每个工具调用一次
   ↓
7. after_tool_execution(frame, tool_result)  ← 每个工具执行后调用
   ↓
8. before_recursion(frame, next_frame)
   ↓
9. after_iteration_end(frame)
```

---

### 1. `before_iteration_start`

**调用时机**：每次 tt 迭代开始时

**参数**：
- `frame: ExecutionFrame` - 当前执行帧

**返回值**：
- `Optional[ExecutionFrame]` - 修改后的帧，或 `None` 表示不修改

**用途**：
- 检查递归限制
- 注入元数据
- 预检验证

**示例**：

```python
class RecursionLimitHook:
    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth
    
    async def before_iteration_start(self, frame):
        if frame.depth >= self.max_depth:
            print(f"⚠️ 达到最大深度限制: {frame.depth}")
            # 可以在这里修改 frame 或抛出异常
        return None
```

---

### 2. `before_context_assembly`

**调用时机**：上下文组装之前（Phase 1）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧

**返回值**：
- `Optional[ExecutionFrame]` - 修改后的帧，或 `None`

**用途**：
- 注入额外上下文
- 调整 token 预算
- 预处理消息

**示例**：

```python
class ContextInjectionHook:
    async def before_context_assembly(self, frame):
        # 可以在这里修改 frame，添加额外的上下文信息
        # 例如：添加系统提示、调整 token 预算等
        return None
```

---

### 3. `after_context_assembly`

**调用时机**：上下文组装完成后（Phase 1 结束）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧
- `context_snapshot: Dict[str, Any]` - 组装好的上下文快照
- `context_metadata: Dict[str, Any]` - 上下文元数据（token 使用等）

**返回值**：
- `Optional[tuple[Dict[str, Any], Dict[str, Any]]]` - 修改后的 (context_snapshot, context_metadata)，或 `None`

**用途**：
- 检查上下文决策
- 覆盖上下文组件
- 记录 token 使用

**示例**：

```python
class TokenTrackingHook:
    def __init__(self):
        self.token_history = []
    
    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        tokens_used = context_metadata.get("total_tokens", 0)
        self.token_history.append({
            "iteration": frame.depth,
            "tokens": tokens_used
        })
        print(f"📊 迭代 {frame.depth}: 使用了 {tokens_used} tokens")
        return None  # 不修改上下文
```

---

### 4. `before_llm_call`

**调用时机**：调用 LLM 之前（Phase 2）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧
- `messages: List[Dict[str, Any]]` - 要发送给 LLM 的消息列表

**返回值**：
- `Optional[List[Dict[str, Any]]]` - 修改后的消息列表，或 `None`

**用途**：
- 记录提示词
- 注入系统消息
- 修改用户查询
- 预算控制

**示例**：

```python
class PromptLoggingHook:
    def __init__(self, log_file: str = "prompts.log"):
        self.log_file = log_file
    
    async def before_llm_call(self, frame, messages):
        # 记录提示词
        with open(self.log_file, "a") as f:
            f.write(f"\n=== Iteration {frame.depth} ===\n")
            for msg in messages:
                f.write(f"{msg['role']}: {msg['content']}\n")
        
        # 可以修改消息（例如添加系统提示）
        # messages.append({"role": "system", "content": "You are helpful."})
        # return messages
        
        return None  # 不修改消息
```

---

### 5. `after_llm_response`

**调用时机**：LLM 响应完成后（Phase 2 结束）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧
- `response: str` - LLM 的文本响应
- `tool_calls: List[Dict[str, Any]]` - LLM 请求的工具调用列表

**返回值**：
- `Optional[tuple[str, List[Dict[str, Any]]]]` - 修改后的 (response, tool_calls)，或 `None`

**用途**：
- 分析 LLM 决策
- 过滤/修改工具调用
- 记录响应

**示例**：

```python
class ToolCallFilterHook:
    def __init__(self, blocked_tools: List[str]):
        self.blocked_tools = blocked_tools
    
    async def after_llm_response(self, frame, response, tool_calls):
        # 过滤被阻止的工具
        filtered_tool_calls = [
            tc for tc in tool_calls
            if tc.get("name") not in self.blocked_tools
        ]
        
        if len(filtered_tool_calls) < len(tool_calls):
            print(f"🚫 阻止了 {len(tool_calls) - len(filtered_tool_calls)} 个工具调用")
            return response, filtered_tool_calls
        
        return None  # 不修改
```

---

### 6. `before_tool_execution` ⭐ **最重要**

**调用时机**：执行每个工具之前（Phase 4）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧
- `tool_call: Dict[str, Any]` - 要执行的工具调用

**返回值**：
- `Optional[Dict[str, Any]]` - 修改后的工具调用，或 `None`

**可抛出异常**：
- `InterruptException` - 暂停执行，等待用户输入（HITL）
- `SkipToolException` - 跳过这个工具

**用途**：
- **Human-in-the-Loop 确认**
- 权限检查
- 速率限制
- 修改工具参数

**示例 - HITL**：

```python
from loom.core.lifecycle_hooks import InterruptException

class DangerousToolHook:
    def __init__(self, dangerous_tools: List[str]):
        self.dangerous_tools = dangerous_tools
    
    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call.get("name", "")
        
        if tool_name in self.dangerous_tools:
            # 暂停执行，等待用户确认
            raise InterruptException(
                reason=f"需要确认执行危险工具: {tool_name}",
                requires_user_input=True,
                frame_id=frame.frame_id
            )
        
        return None
```

**示例 - 修改参数**：

```python
class ParameterSanitizationHook:
    async def before_tool_execution(self, frame, tool_call):
        # 清理工具参数
        if tool_call.get("name") == "read_file":
            args = tool_call.get("arguments", {})
            # 防止路径遍历攻击
            path = args.get("path", "")
            if ".." in path:
                args["path"] = path.replace("..", "")
                tool_call["arguments"] = args
                return tool_call
        
        return None
```

---

### 7. `after_tool_execution`

**调用时机**：每个工具执行完成后（Phase 4）

**参数**：
- `frame: ExecutionFrame` - 当前执行帧
- `tool_result: Dict[str, Any]` - 工具执行结果

**返回值**：
- `Optional[Dict[str, Any]]` - 修改后的结果，或 `None`

**用途**：
- 后处理结果
- 错误恢复
- 结果缓存
- 指标收集

**示例**：

```python
class ResultCachingHook:
    def __init__(self):
        self.cache = {}
    
    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result.get("tool_name")
        result_content = tool_result.get("content", "")
        
        # 缓存结果
        cache_key = f"{tool_name}:{hash(result_content)}"
        self.cache[cache_key] = result_content
        
        return None
```

---

### 8. `before_recursion`

**调用时机**：准备递归调用之前（Phase 5）

**参数**：
- `current_frame: ExecutionFrame` - 当前帧
- `next_frame: ExecutionFrame` - 即将创建的下一帧

**返回值**：
- `Optional[ExecutionFrame]` - 修改后的下一帧，或 `None`

**用途**：
- 决定是否继续递归
- 修改下一迭代的状态
- 为下一轮注入指导

**示例**：

```python
class RecursionControlHook:
    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
    
    async def before_recursion(self, current_frame, next_frame):
        if next_frame.depth >= self.max_depth:
            print(f"⚠️ 阻止递归：已达到最大深度 {self.max_depth}")
            # 可以修改 next_frame 或抛出异常来阻止递归
            # 这里我们返回 None，让执行继续，但可以添加警告
        
        return None
```

---

### 9. `after_iteration_end`

**调用时机**：每次迭代结束时

**参数**：
- `frame: ExecutionFrame` - 当前执行帧（处理完成后）

**返回值**：
- `Optional[ExecutionFrame]` - 修改后的帧，或 `None`

**用途**：
- 清理资源
- 收集指标
- 保存检查点

**示例**：

```python
class CheckpointHook:
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        import os
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    async def after_iteration_end(self, frame):
        # 保存检查点
        checkpoint_file = f"{self.checkpoint_dir}/frame_{frame.frame_id}.json"
        # 序列化 frame 并保存
        # ... 保存逻辑 ...
        return None
```

---

## 内置钩子

### 1. LoggingHook

**功能**：简单的日志记录钩子，用于调试

**使用**：

```python
from loom.core.lifecycle_hooks import LoggingHook
from loom import agent

# 创建钩子
logging_hook = LoggingHook(verbose=True)

# 使用
my_agent = agent(
    provider="openai",
    model="gpt-4o-mini",
    hooks=[logging_hook]
)
```

**输出示例**：

```
[Iteration 0] Starting
[Iteration 0] Calling LLM with 2 messages
  Last message: 请帮我搜索 Python 文档...
[Iteration 0] Executing tool: search
  Arguments: {'query': 'Python'}
```

---

### 2. MetricsHook

**功能**：收集执行指标

**使用**：

```python
from loom.core.lifecycle_hooks import MetricsHook
from loom import agent

# 创建钩子
metrics_hook = MetricsHook()

# 使用
my_agent = agent(
    provider="openai",
    model="gpt-4o-mini",
    hooks=[metrics_hook]
)

# 执行任务
await my_agent.run("你的任务")

# 获取指标
metrics = metrics_hook.get_metrics()
print(metrics)
# {
#   "iterations": 3,
#   "llm_calls": 3,
#   "tool_executions": {"search": 2, "read_file": 1},
#   "errors": 0
# }
```

---

### 3. HITLHook

**功能**：Human-in-the-Loop，在执行危险操作前暂停并等待用户确认

**使用**：

```python
from loom.core.lifecycle_hooks import HITLHook
from loom import agent

# 创建 HITL 钩子
hitl_hook = HITLHook(
    dangerous_tools=["delete_file", "send_email", "execute_shell"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ").lower() == "y"
)

# 使用
my_agent = agent(
    provider="openai",
    model="gpt-4o-mini",
    tools=all_tools,
    hooks=[hitl_hook],
    enable_persistence=True  # 建议启用持久化以支持检查点
)

# 执行任务
await my_agent.run("删除旧日志并发送报告")
# ⏸️  输出: "Allow execution of 'delete_file'? (y/n):"
```

**自定义确认回调**：

```python
async def custom_confirmation(message: str) -> bool:
    """自定义确认逻辑（可以是异步的）"""
    # 可以集成到 Web UI、Slack、邮件等
    print(f"🔔 {message}")
    response = input("确认执行？(y/n): ")
    return response.lower() == "y"

hitl_hook = HITLHook(
    dangerous_tools=["delete_file"],
    ask_user_callback=custom_confirmation
)
```

---

## 自定义钩子

### 基本结构

钩子可以是任何实现了 `LifecycleHook` Protocol 的类。所有方法都是**可选的**，只需实现你需要的。

```python
class MyCustomHook:
    """自定义钩子示例"""
    
    def __init__(self):
        # 初始化状态
        self.counter = 0
    
    async def before_llm_call(self, frame, messages):
        """实现你需要的钩子方法"""
        self.counter += 1
        print(f"LLM 调用 #{self.counter}")
        return None  # 不修改消息
```

---

### 示例 1: 分析钩子

```python
class AnalyticsHook:
    """收集执行分析数据"""
    
    def __init__(self):
        self.tool_usage = {}
        self.llm_calls = 0
        self.token_usage = []
    
    async def before_llm_call(self, frame, messages):
        self.llm_calls += 1
        return None
    
    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        tokens = context_metadata.get("total_tokens", 0)
        self.token_usage.append({
            "iteration": frame.depth,
            "tokens": tokens
        })
        return None
    
    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result.get("tool_name", "unknown")
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None
    
    def get_report(self):
        """获取分析报告"""
        return {
            "llm_calls": self.llm_calls,
            "total_tokens": sum(t["tokens"] for t in self.token_usage),
            "tool_usage": self.tool_usage,
            "avg_tokens_per_iteration": sum(t["tokens"] for t in self.token_usage) / len(self.token_usage) if self.token_usage else 0
        }

# 使用
analytics = AnalyticsHook()
agent = agent(provider="openai", model="gpt-4o-mini", hooks=[analytics])

await agent.run("你的任务")

report = analytics.get_report()
print(report)
```

---

### 示例 2: 权限控制钩子

```python
from loom.core.lifecycle_hooks import SkipToolException

class PermissionHook:
    """基于角色的权限控制"""
    
    def __init__(self, user_role: str = "guest"):
        self.user_role = user_role
        self.permissions = {
            "admin": ["*"],  # 所有权限
            "user": ["read_file", "search"],
            "guest": ["search"]  # 只读权限
        }
    
    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call.get("name", "")
        allowed_tools = self.permissions.get(self.user_role, [])
        
        # 检查权限
        if "*" not in allowed_tools and tool_name not in allowed_tools:
            print(f"🚫 权限不足：角色 '{self.user_role}' 无法执行 '{tool_name}'")
            raise SkipToolException(f"Permission denied for {tool_name}")
        
        return None

# 使用
permission_hook = PermissionHook(user_role="guest")
agent = agent(provider="openai", model="gpt-4o-mini", hooks=[permission_hook])
```

---

### 示例 3: 速率限制钩子

```python
import time
from loom.core.lifecycle_hooks import InterruptException

class RateLimitHook:
    """工具调用速率限制"""
    
    def __init__(self, calls_per_minute: int = 10):
        self.calls_per_minute = calls_per_minute
        self.call_times = []
    
    async def before_tool_execution(self, frame, tool_call):
        now = time.time()
        
        # 清理一分钟前的记录
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        # 检查速率限制
        if len(self.call_times) >= self.calls_per_minute:
            wait_time = 60 - (now - self.call_times[0])
            raise InterruptException(
                f"速率限制：已达到 {self.calls_per_minute} 次/分钟，请等待 {wait_time:.1f} 秒"
            )
        
        # 记录本次调用
        self.call_times.append(now)
        return None
```

---

### 示例 4: 结果验证钩子

```python
class ResultValidationHook:
    """验证工具执行结果"""
    
    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result.get("tool_name", "")
        content = tool_result.get("content", "")
        is_error = tool_result.get("is_error", False)
        
        # 验证结果
        if is_error:
            print(f"⚠️ 工具 {tool_name} 执行出错: {content}")
            # 可以在这里实现错误恢复逻辑
        
        # 检查结果格式
        if tool_name == "read_file" and not isinstance(content, str):
            print(f"⚠️ read_file 返回了意外的类型: {type(content)}")
            # 可以修改结果
            tool_result["content"] = str(content)
            return tool_result
        
        return None
```

---

## 高级用法

### 1. 多个钩子组合

```python
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook
from loom import agent

# 组合多个钩子
my_agent = agent(
    provider="openai",
    model="gpt-4o-mini",
    hooks=[
        LoggingHook(verbose=True),      # 日志
        MetricsHook(),                   # 指标
        HITLHook(dangerous_tools=["delete_file"]),  # HITL
        AnalyticsHook()                  # 自定义分析
    ]
)
```

**执行顺序**：钩子按列表顺序执行，前一个钩子的返回值作为下一个钩子的输入。

---

### 2. 条件钩子

```python
class ConditionalHook:
    """根据条件决定是否执行钩子逻辑"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    async def before_llm_call(self, frame, messages):
        if not self.enabled:
            return None
        
        # 只在启用时执行
        print("钩子逻辑执行中...")
        return None
```

---

### 3. 状态管理钩子

```python
class StatefulHook:
    """维护状态的钩子"""
    
    def __init__(self):
        self.conversation_history = []
        self.tool_results_cache = {}
    
    async def before_llm_call(self, frame, messages):
        # 保存对话历史
        self.conversation_history.append({
            "iteration": frame.depth,
            "messages": messages
        })
        return None
    
    async def after_tool_execution(self, frame, tool_result):
        # 缓存工具结果
        tool_name = tool_result.get("tool_name")
        cache_key = f"{tool_name}:{frame.depth}"
        self.tool_results_cache[cache_key] = tool_result
        return None
```

---

### 4. 异步操作钩子

```python
import aiohttp

class ExternalAPILoggingHook:
    """将日志发送到外部 API"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def after_tool_execution(self, frame, tool_result):
        # 异步发送到外部 API
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.api_url,
                json={
                    "tool": tool_result.get("tool_name"),
                    "iteration": frame.depth,
                    "timestamp": time.time()
                }
            )
        return None
```

---

### 5. 修改执行流程

```python
class MessageModificationHook:
    """修改发送给 LLM 的消息"""
    
    async def before_llm_call(self, frame, messages):
        # 添加系统提示
        if not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {
                "role": "system",
                "content": "你是一个专业的 Python 开发助手。"
            })
            return messages
        
        return None
```

---

## 最佳实践

### 1. 钩子职责单一

✅ **好的做法**：

```python
class LoggingHook:
    """只负责日志记录"""
    async def before_llm_call(self, frame, messages):
        print(f"LLM 调用: {len(messages)} 条消息")
        return None

class MetricsHook:
    """只负责指标收集"""
    async def before_llm_call(self, frame, messages):
        self.llm_calls += 1
        return None
```

❌ **不好的做法**：

```python
class MixedHook:
    """混合了多种职责"""
    async def before_llm_call(self, frame, messages):
        # 日志
        print(f"LLM 调用: {len(messages)}")
        # 指标
        self.llm_calls += 1
        # 权限检查
        if not self.has_permission():
            raise Exception("No permission")
        # 太多职责！
        return None
```

---

### 2. 返回值处理

- **返回 `None`**：表示不修改数据，继续使用原始值
- **返回修改后的值**：会传递给下一个钩子
- **抛出异常**：`InterruptException` 或 `SkipToolException`

```python
class GoodHook:
    async def before_llm_call(self, frame, messages):
        # 不修改，返回 None
        print("记录日志")
        return None  # ✅

class ModifyHook:
    async def before_llm_call(self, frame, messages):
        # 修改消息
        messages.append({"role": "system", "content": "..."})
        return messages  # ✅ 返回修改后的值
```

---

### 3. 错误处理

```python
class RobustHook:
    """健壮的钩子，处理异常"""
    
    async def before_tool_execution(self, frame, tool_call):
        try:
            # 你的逻辑
            self.validate_tool(tool_call)
        except Exception as e:
            # 记录错误但不中断执行
            print(f"钩子错误: {e}")
            # 返回 None 继续执行
            return None
        
        return None
```

---

### 4. 性能考虑

- **避免阻塞操作**：使用异步操作
- **缓存结果**：避免重复计算
- **轻量级检查**：在钩子中只做必要的检查

```python
class EfficientHook:
    def __init__(self):
        self.cache = {}  # 缓存
    
    async def before_llm_call(self, frame, messages):
        # 使用缓存避免重复计算
        cache_key = hash(str(messages))
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 计算...
        result = expensive_computation(messages)
        self.cache[cache_key] = result
        return result
```

---

## 完整示例

### 示例：完整的 Agent 配置

```python
import asyncio
from loom import agent
from loom.core.lifecycle_hooks import (
    LoggingHook,
    MetricsHook,
    HITLHook,
    InterruptException
)

# 自定义分析钩子
class AnalyticsHook:
    def __init__(self):
        self.stats = {
            "llm_calls": 0,
            "tool_calls": {},
            "total_tokens": 0
        }
    
    async def before_llm_call(self, frame, messages):
        self.stats["llm_calls"] += 1
        return None
    
    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        tokens = context_metadata.get("total_tokens", 0)
        self.stats["total_tokens"] += tokens
        return None
    
    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result.get("tool_name", "unknown")
        self.stats["tool_calls"][tool_name] = \
            self.stats["tool_calls"].get(tool_name, 0) + 1
        return None
    
    def get_stats(self):
        return self.stats.copy()

# 自定义权限钩子
class PermissionHook:
    def __init__(self, allowed_tools: list):
        self.allowed_tools = allowed_tools
    
    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call.get("name", "")
        if tool_name not in self.allowed_tools:
            raise InterruptException(f"工具 '{tool_name}' 需要权限确认")
        return None

# 创建钩子
logging_hook = LoggingHook(verbose=True)
metrics_hook = MetricsHook()
analytics_hook = AnalyticsHook()
permission_hook = PermissionHook(allowed_tools=["search", "read_file"])

# 创建 Agent
my_agent = agent(
    provider="openai",
    model="gpt-4o-mini",
    hooks=[
        logging_hook,
        metrics_hook,
        analytics_hook,
        permission_hook
    ]
)

# 执行任务
async def main():
    result = await my_agent.run("搜索 Python 文档")
    print(f"\n结果: {result}")
    
    # 查看统计
    print("\n📊 指标:")
    print(metrics_hook.get_metrics())
    
    print("\n📈 分析:")
    print(analytics_hook.get_stats())

asyncio.run(main())
```

---

## 总结

### 关键要点

1. **钩子是 Protocol**：无需继承，只需实现需要的方法
2. **9个钩子点**：覆盖执行流程的所有关键阶段
3. **链式执行**：多个钩子按顺序执行，可以修改数据
4. **异常控制**：`InterruptException` 和 `SkipToolException` 控制流程
5. **组合使用**：可以组合多个钩子实现复杂功能

### 常见用例

- ✅ **HITL**：使用 `before_tool_execution` + `InterruptException`
- ✅ **日志**：使用 `before_llm_call`、`after_tool_execution`
- ✅ **指标**：使用 `after_context_assembly`、`after_tool_execution`
- ✅ **权限**：使用 `before_tool_execution` + `SkipToolException`
- ✅ **修改数据**：返回修改后的值

### 下一步

- 查看 [API 参考文档](API_REFERENCE_v0_0_8.md) 了解详细 API
- 查看 [示例代码](../examples/) 了解更多用例
- 阅读 [架构文档](ARCHITECTURE_REFACTOR.md) 了解内部实现

---

**文档版本**: v0.0.9  
**最后更新**: 2024-12-09

