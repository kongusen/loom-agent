# loom-agent v0.0.8 社交媒体公告

## Twitter/X 公告

```
🚀 loom-agent v0.0.8 is here!

New: Recursive State Machine architecture with:
🎬 Event Sourcing
🪝 Lifecycle Hooks (9 points)
🛡️ HITL Support
🔄 Crash Recovery
🐛 Context Debugger
📊 Execution Visualizer

Unique vs LangGraph: Strategy upgrade during replay!

pip install loom-agent==0.0.8

#AI #LLM #Agents #Python #OpenSource
```

## LinkedIn 公告

```
🎉 Excited to announce loom-agent v0.0.8 - Recursive State Machine for AI Agents

Major architectural upgrade focused on production reliability:

✨ Key Features:
• Event Sourcing for crash recovery
• Lifecycle Hooks (9 interception points) for elegant control flow
• Human-in-the-Loop (HITL) support for dangerous operations
• Context Debugger for transparent context management
• Execution Visualizer with flame graph visualization

🎯 Unique Differentiator:
Unlike LangGraph's static snapshots, loom-agent supports "Strategy Upgrade" - replay old events with new strategies. This is a unique capability that enables continuous improvement without losing execution history.

📦 Install: pip install loom-agent==0.0.8

🔗 GitHub: https://github.com/kongusen/loom-agent
📚 Docs: https://github.com/kongusen/loom-agent#readme

#AI #MachineLearning #Python #OpenSource #LLM #Agents
```

## Reddit 公告 (r/LocalLLaMA, r/MachineLearning)

```
loom-agent v0.0.8 Released - Recursive State Machine for AI Agents

Major architectural upgrade focused on production reliability:

**New Features:**
- Event sourcing for crash recovery
- Lifecycle hooks for elegant control flow (9 interception points)
- Human-in-the-Loop (HITL) support
- Context debugging and transparency
- Execution visualization with flame graphs

**Key Differentiator vs LangGraph:**
Can replay old events with new strategies (unique capability!). Unlike LangGraph's static snapshots, loom-agent's event sourcing allows you to upgrade your compression/context strategies and replay historical executions with the new approach.

**Installation:**
```bash
pip install loom-agent==0.0.8
```

**Links:**
- PyPI: https://pypi.org/project/loom-agent/0.0.8/
- GitHub: https://github.com/kongusen/loom-agent
- Quick Start: https://github.com/kongusen/loom-agent/blob/main/docs/QUICKSTART_v0_0_8.md

Would love feedback from the community! Especially interested in:
- Use cases for event sourcing in production
- HITL workflow patterns
- Context management strategies

**Example Usage:**
```python
from loom import agent
from loom.core.lifecycle_hooks import HITLHook, LoggingHook
from pathlib import Path

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    enable_persistence=True,  # Event sourcing
    hooks=[
        HITLHook(dangerous_tools=["delete_file", "send_email"]),
        LoggingHook(verbose=True)
    ],
)
```

Looking forward to your thoughts!
```

## Hacker News 公告

```
Show HN: loom-agent v0.0.8 - Recursive State Machine for AI Agents

loom-agent is a Python framework for building production-ready AI agents with event sourcing, lifecycle hooks, and crash recovery.

**What makes it different:**
- Event Sourcing vs static snapshots (can replay with new strategies)
- Lifecycle Hooks (9 points) vs explicit graph edges
- Context Governance with full transparency
- Built-in HITL support for dangerous operations

**v0.0.8 Highlights:**
- ~3,500 lines of new core components
- Complete event sourcing implementation
- Time travel debugging
- Flame graph visualization

**Installation:**
```bash
pip install loom-agent==0.0.8
```

**GitHub:** https://github.com/kongusen/loom-agent

**Docs:** https://github.com/kongusen/loom-agent#readme

Would love feedback on the architecture and use cases!
```

## 中文社区公告 (掘金、知乎、V2EX)

```
🚀 loom-agent v0.0.8 发布 - 递归状态机架构

重大架构升级：从"隐式递归框架"升级为生产级**递归状态机（RSM）**。

**核心特性：**
- 🎬 事件溯源 - 完整的执行历史，支持崩溃恢复
- 🪝 生命周期钩子 - 9 个拦截点，优雅的控制流
- 🛡️ 人机协同（HITL）- 危险操作自动拦截和确认
- 🔄 崩溃恢复 - 从任意断点恢复执行
- 🐛 上下文调试器 - 透明化上下文管理决策
- 📊 执行可视化 - 火焰图展示递归深度和时序

**vs LangGraph 的独特优势：**
- 事件溯源 vs 静态快照（可以重新计算）
- 策略升级 - 用新策略重放旧事件（LangGraph 做不到）
- 上下文治理 - 完整的透明度和调试能力
- 钩子式控制流 - 无需显式连线

**安装：**
```bash
pip install loom-agent==0.0.8
```

**GitHub:** https://github.com/kongusen/loom-agent
**文档:** https://github.com/kongusen/loom-agent#readme

欢迎反馈和建议！
```

