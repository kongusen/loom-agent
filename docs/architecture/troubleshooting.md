# Loom Agent v0.1.1 故障排查指南

**系统化问题诊断** | **快速定位根因** | **一步步解决方案**

---

## 🔍 快速诊断流程图

```
Agent 出现问题？
│
├─ 1. Agent 不响应/不启动？
│   ├─ 检查 LLM 配置
│   │   ├─ API key 设置？ → export OPENAI_API_KEY=sk-...
│   │   ├─ Model 名称正确？ → "gpt-4" 不是 "gpt4"
│   │   └─ Provider 支持？ → openai/anthropic/azure
│   │
│   ├─ 检查导入
│   │   ├─ from loom import agent  ← 正确
│   │   └─ from loom import Agent  ← 也正确
│   │
│   └─ 检查 async/await
│       ├─ await agent.run() ← 正确
│       └─ agent.run()       ← 错误（返回coroutine）
│
├─ 2. Agent 执行后无输出？
│   ├─ 检查返回值
│   │   └─ result = await agent.run() → print(result)
│   │
│   ├─ 检查事件流
│   │   └─ async for event in agent.execute(): ...
│   │
│   └─ 检查日志
│       └─ 启用 LoggingHook
│
├─ 3. 工具调用失败？
│   ├─ 工具已注册？
│   │   └─ tools=[ReadFileTool(), BashTool()]
│   │
│   ├─ 工具名称正确？
│   │   └─ "read_file" 不是 "readfile"
│   │
│   └─ 权限问题？
│       └─ HITLHook 阻止？检查 ask_handler
│
├─ 4. 上下文/Token 问题？
│   ├─ 超过 token 限制？
│   │   ├─ 增加 max_context_tokens
│   │   └─ 启用 CompressionManager
│   │
│   ├─ 上下文丢失？
│   │   └─ 启用 ContextDebugger
│   │
│   └─ Compression 失败？
│       └─ 检查 COMPRESSION_FALLBACK 事件
│
├─ 5. 超过最大迭代？
│   ├─ 增加 max_iterations
│   ├─ 检查死循环
│   └─ 优化 system_instructions
│
├─ 6. Crash Recovery 失败？
│   ├─ thread_id 唯一？
│   ├─ EventJournal 配置正确？
│   └─ 日志文件存在？
│
└─ 7. 性能问题？
    ├─ Token 使用过高？ → 优化 context
    ├─ 响应慢？ → 使用更快的 model
    └─ 并发问题？ → 使用 Crew 并行执行
```

---

## 🚨 常见错误速查表

### 错误 1: `ToolNotFoundError: Tool 'bash' not found`

**原因**: 工具未注册到 Agent

**解决方案**:
```python
# ❌ 错误
agent(llm=llm, tools=[])  # 没有 BashTool

# ✅ 正确
from loom.builtin.tools import BashTool
agent(llm=llm, tools=[BashTool()])
```

**调试步骤**:
1. 检查 `tools=[]` 参数
2. 确认工具已导入
3. 验证工具名称拼写

---

### 错误 2: `MaxIterationsExceeded: Agent exceeded 50 iterations`

**原因**: Agent 陷入循环或任务太复杂

**解决方案**:
```python
# 方案 1: 增加迭代限制
agent(llm=llm, max_iterations=100)

# 方案 2: 优化 system_instructions
agent(
    llm=llm,
    system_instructions="""
    完成任务后立即停止。
    不要重复已完成的工作。
    如果遇到问题，报告而不是无限重试。
    """
)

# 方案 3: 添加取消令牌
cancel_token = asyncio.Event()
result = await agent.run("task", cancel_token=cancel_token)
```

**调试步骤**:
1. 启用详细日志查看迭代过程
2. 检查 ITERATION_START 事件
3. 分析是否有工具调用死循环

---

### 错误 3: `TokenLimitExceeded: Context size 12000 exceeds limit 8000`

**原因**: 上下文超过模型限制

**解决方案**:
```python
# 方案 1: 增加限制（如果模型支持）
agent(llm=llm, max_context_tokens=16000)

# 方案 2: 启用压缩（v0.1.1 自动启用）
from loom.core.compression_manager import CompressionManager
compressor = CompressionManager(llm=llm, compression_threshold=0.92)
agent(llm=llm, compressor=compressor)

# 方案 3: 优化 Context Assembly
from loom.core.context_assembly import ContextAssembler
assembler = ContextAssembler(max_tokens=8000)
# 使用 assembler 管理上下文组件优先级
```

**调试步骤**:
1. 启用 ContextDebugger 查看 token 使用
2. 检查哪些组件占用最多 tokens
3. 调整组件优先级或启用截断

---

### 错误 4: `ThreadIdRequired: enable_persistence=True requires thread_id`

**原因**: 启用持久化但未提供 thread_id

**解决方案**:
```python
# ❌ 错误
agent(llm=llm, enable_persistence=True)

# ✅ 正确
import uuid
agent(
    llm=llm,
    enable_persistence=True,
    thread_id=f"user-{user_id}-{uuid.uuid4()}"
)
```

**thread_id 最佳实践**:
- 格式: `user-{user_id}-{session_id}`
- 必须唯一（跨用户和会话）
- 用于 crash recovery 和会话管理

---

### 错误 5: `LLMError: OpenAI API key not found`

**原因**: API key 未设置或无效

**解决方案**:
```bash
# 方案 1: 环境变量
export OPENAI_API_KEY=sk-...

# 方案 2: .env 文件
echo "OPENAI_API_KEY=sk-..." > .env
pip install python-dotenv
```

```python
# 方案 3: 代码中设置（不推荐用于生产）
from loom.builtin.llms.openai import OpenAILLM
llm = OpenAILLM(model="gpt-4", api_key="sk-...")
```

**调试步骤**:
1. 运行 `echo $OPENAI_API_KEY` 验证环境变量
2. 检查 API key 是否有效（登录 OpenAI dashboard）
3. 确认 key 有足够的配额

---

### 错误 6: `TypeError: 'coroutine' object is not iterable`

**原因**: 忘记使用 `await` 或 `async for`

**解决方案**:
```python
# ❌ 错误
result = agent.run("task")  # 返回 coroutine
for event in agent.execute("task"):  # 错误：不是普通迭代器

# ✅ 正确
result = await agent.run("task")  # 使用 await
async for event in agent.execute("task"):  # 使用 async for
    print(event)
```

---

### 错误 7: `PermissionDenied: Tool 'bash' blocked by HITLHook`

**原因**: HITL Hook 阻止了工具执行

**解决方案**:
```python
# 检查 ask_handler 返回值
hitl = HITLHook(
    dangerous_tools=["bash"],
    ask_handler=lambda msg: input(f"{msg} (y/n): ") == "y"  # 确保返回 bool
)

# 或临时允许所有操作（开发环境）
hitl = HITLHook(
    dangerous_tools=[],  # 空列表 = 不拦截任何工具
)
```

---

### 错误 8: `MemoryError: Failed to save to disk`

**原因**: 磁盘空间不足或权限问题

**解决方案**:
```python
# 检查磁盘空间
import shutil
free_space = shutil.disk_usage(".").free / (1024**3)
print(f"Free space: {free_space:.2f} GB")

# 检查权限
from pathlib import Path
persist_dir = Path(".loom")
persist_dir.mkdir(parents=True, exist_ok=True)

# 检查持久化信息
memory = PersistentMemory()
info = memory.get_persistence_info()
print(info)
```

---

## 🔧 系统化调试检查清单

### Leve 1: 基础配置检查

```
[ ] 1. Python 版本 >= 3.9
[ ] 2. loom-agent 已安装 (pip list | grep loom)
[ ] 3. 依赖包已安装 (openai, anthropic 等)
[ ] 4. API key 已设置 (echo $OPENAI_API_KEY)
[ ] 5. 网络连接正常 (ping api.openai.com)
```

**验证脚本**:
```bash
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import loom
    print(f'loom-agent: {loom.__version__}')
except ImportError:
    print('loom-agent: NOT INSTALLED')
import os
print(f'OPENAI_API_KEY: {\"SET\" if os.getenv(\"OPENAI_API_KEY\") else \"NOT SET\"}')"
```

---

### Level 2: Agent 配置检查

```
[ ] 1. LLM 配置正确
[ ] 2. 工具已注册
[ ] 3. system_instructions 清晰
[ ] 4. max_iterations 合理
[ ] 5. max_context_tokens 足够
[ ] 6. Memory 配置正确（如需要）
[ ] 7. Hooks 配置正确（如需要）
```

**验证脚本**:
```python
# agent_config_check.py
from loom import agent
from loom.builtin.tools import ReadFileTool

my_my_agent = loom.agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool()],
    max_iterations=50,
    max_context_tokens=8000
)

# 检查配置
print(f"LLM: {my_agent.executor.llm}")
print(f"Tools: {list(my_agent.executor.tools.keys())}")
print(f"Max iterations: {my_agent.executor.max_iterations}")
print(f"Max context tokens: {my_agent.executor.max_context_tokens}")
```

---

### Level 3: 执行流程调试

启用详细日志：

```python
from loom import agent
from loom.core.lifecycle_hooks import LoggingHook
from loom.core.events import AgentEventType
from pathlib import Path

# 方式 1: LoggingHook
logging_hook = LoggingHook(
    log_level="DEBUG",
    log_file=Path("./agent_debug.log")
)

my_my_agent = loom.agent(
    llm=llm,
    tools=tools,
    hooks=[logging_hook]
)

# 方式 2: 手动事件监听
async for event in my_agent.execute("task"):
    print(f"[{event.type}] {event.metadata}")
    
    if event.type == AgentEventType.ERROR:
        print(f"ERROR: {event.error}")
        import traceback
        traceback.print_exc()
```

---

### Level 4: 上下文调试

```python
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)

my_my_agent = loom.agent(
    llm=llm,
    tools=tools,
    context_debugger=debugger
)

await my_agent.run("task")

# 生成诊断报告
print(debugger.generate_summary())

# 检查特定迭代
print(debugger.explain_iteration(5))

# 检查特定组件
print(debugger.explain_component("file_content"))
```

---

### Level 5: 性能分析

```python
from loom.core.lifecycle_hooks import LifecycleHook
import time

class PerformanceHook(LifecycleHook):
    """性能分析 Hook"""
    
    def __init__(self):
        self.metrics = {
            "llm_calls": 0,
            "llm_total_time": 0,
            "tool_calls": {},
            "iterations": 0
        }
        self._llm_start = None
    
    async def before_llm_call(self, frame, messages):
        self._llm_start = time.time()
        self.metrics["llm_calls"] += 1
        return None
    
    async def after_llm_response(self, frame, response):
        if self._llm_start:
            elapsed = time.time() - self._llm_start
            self.metrics["llm_total_time"] += elapsed
        return None
    
    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call.get("name", "unknown")
        if tool_name not in self.metrics["tool_calls"]:
            self.metrics["tool_calls"][tool_name] = 0
        self.metrics["tool_calls"][tool_name] += 1
        return None
    
    async def after_iteration_end(self, frame, result):
        self.metrics["iterations"] += 1
        return None
    
    def report(self):
        print("\n" + "=" * 60)
        print("性能报告")
        print("=" * 60)
        print(f"总迭代次数: {self.metrics['iterations']}")
        print(f"LLM 调用次数: {self.metrics['llm_calls']}")
        print(f"LLM 总耗时: {self.metrics['llm_total_time']:.2f}s")
        print(f"平均 LLM 耗时: {self.metrics['llm_total_time'] / max(self.metrics['llm_calls'], 1):.2f}s")
        print(f"\n工具使用统计:")
        for tool, count in self.metrics["tool_calls"].items():
            print(f"  - {tool}: {count} 次")
        print("=" * 60)

# 使用
perf = PerformanceHook()
my_my_agent = loom.agent(llm=llm, tools=tools, hooks=[perf])
await my_agent.run("task")
perf.report()
```

---

## 📊 问题分类和解决方案

### 类别 1: 配置问题

| 症状 | 根因 | 解决方案 |
|------|------|----------|
| Agent 不启动 | LLM 配置错误 | 检查 provider, model, api_key |
| 工具无法使用 | 工具未注册 | 添加到 tools=[] |
| 权限错误 | HITLHook 拦截 | 配置 ask_handler 或移除拦截 |

---

### 类别 2: 执行问题

| 症状 | 根因 | 解决方案 |
|------|------|----------|
| 超过最大迭代 | 死循环或任务太复杂 | 增加 max_iterations 或优化指令 |
| 无输出 | 忘记 await | 使用 await agent.run() |
| Crash | 未捕获异常 | 添加 try-except，检查日志 |

---

### 类别 3: 性能问题

| 症状 | 根因 | 解决方案 |
|------|------|----------|
| 响应慢 | 模型太大 | 使用更快的模型（如 gpt-3.5-turbo） |
| Token 使用高 | 上下文太大 | 启用压缩，优化组件优先级 |
| 内存占用高 | 历史消息太多 | 定期清理 memory |

---

### 类别 4: 上下文问题

| 症状 | 根因 | 解决方案 |
|------|------|----------|
| Token 超限 | 上下文太大 | 启用 CompressionManager |
| 上下文丢失 | 压缩过度 | 调整 compression_threshold |
| 组件被排除 | 优先级太低 | 提高优先级或增加 budget |

---

## 💡 调试技巧

### 技巧 1: 使用流式API查看实时进度

```python
async for event in agent.execute("task"):
    print(f"[{event.timestamp:.2f}] {event.type}: {event.metadata}")
```

### 技巧 2: 保存事件日志用于离线分析

```python
events = []
async for event in agent.execute("task"):
    events.append(event)

# 保存到文件
import json
with open("events.json", "w") as f:
    json.dump([e.__dict__ for e in events], f, indent=2, default=str)
```

### 技巧 3: 使用 ContextDebugger 可视化上下文

```python
debugger = ContextDebugger(enable_auto_export=True)
agent(llm=llm, context_debugger=debugger)

# 执行后查看
print(debugger.generate_summary())
```

### 技巧 4: 创建最小复现案例

```python
# minimal_repro.py
import asyncio
from loom import agent

async def main():
    # 最简配置
    my_my_agent = loom.agent(provider="openai", model="gpt-4")
    
    # 最简任务
    result = await my_agent.run("Hello")
    print(result)

asyncio.run(main())
```

---

## 🆘 获取帮助

### 1. 检查文档
- Quick Reference: `docs/user/quick-reference.md`
- User Guide: `docs/user/user-guide.md`
- API Reference: `docs/user/api-reference.md`

### 2. 查看示例
- 完整示例: `examples/complete/`
- 集成示例: `examples/integrations/`

### 3. 提交 Issue
GitHub: https://github.com/your-org/loom-agent/issues

**提交时请包含**:
- loom-agent 版本
- Python 版本
- 最小复现案例
- 完整错误堆栈
- 相关日志

---

**Version**: v0.1.1  
**Last Updated**: 2024-12-12  
**License**: MIT
