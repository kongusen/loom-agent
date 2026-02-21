# Context Architecture Design

## 概述

本文档描述 Loom 框架的上下文控制架构。

**核心思想**：
- Session 在 EventBus 层，控制 Task 流
- ContextOrchestrator 控制 Memory 和其他上下文来源
- Memory 只是上下文的一个来源，不是全部

## 7大上下文来源

```
┌─────────────────────────────────────────────────────────────┐
│                    Context Sources                           │
│                                                              │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│  │  User  │ │ Agent  │ │ Memory │ │  Know  │ │ Prompt │    │
│  │ Input  │ │ Output │ │ (L1-4) │ │ ledge  │ │        │    │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
│                                                              │
│  ┌────────┐ ┌────────┐                                      │
│  │ Tools  │ │ Skills │                                      │
│  └────────┘ └────────┘                                      │
└─────────────────────────────────────────────────────────────┘
```

| # | 来源 | 说明 | Token 特点 |
|---|------|------|------------|
| 1 | User Input | 用户当前输入 | 必须包含，高优先级 |
| 2 | Agent Output | Agent 历史输出 | 按时间衰减 |
| 3 | Memory | L1-L4 历史记忆 | 分层压缩 |
| 4 | Knowledge | RAG 知识库 | 按相关性 |
| 5 | Prompt | 系统提示词 | 固定开销 |
| 6 | Tools | 工具定义 | 按需加载 |
| 7 | Skills | 技能定义 | 按需激活 |

## 层级架构

```
┌─────────────────────────────────────────────────────────────┐
│                    EventBus Layer (A2)                       │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 ContextController                      │  │
│  │  - 管理多个 Session                                    │  │
│  │  - 聚合：多 Session → 一个 Agent                       │  │
│  │  - 分发：一个 Agent → 多 Session                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│              ┌─────────────┼─────────────┐                  │
│              ▼             ▼             ▼                  │
│        ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│        │Session A │  │Session B │  │Session C │            │
│        └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────┘
                            │ 拥有
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Context Layer                             │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               ContextOrchestrator                      │  │
│  │  - 预算管理 (Token Budget)                             │  │
│  │  - 从 7 大来源收集上下文                               │  │
│  │  - 优先级排序                                          │  │
│  │  - 压缩策略                                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│       ┌──────┬──────┬──────┼──────┬──────┬──────┐          │
│       ▼      ▼      ▼      ▼      ▼      ▼      ▼          │
│     User   Agent  Memory  Know  Prompt Tools  Skills       │
│     Input  Output (L1-4)  ledge                            │
└─────────────────────────────────────────────────────────────┘
                            │ 读取
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Memory  │  │ Knowledge│  │  Config  │  │  Tools   │    │
│  │  (L1-L4) │  │  (RAG)   │  │ (Prompt) │  │ Registry │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. ContextController

**位置**: `loom/events/context_controller.py`

**职责**:
- 管理多个 Session
- 聚合多 Session 上下文
- 分发 Task 到多 Session

### 2. Session

**位置**: `loom/events/session.py`

**职责**:
- Task 流管理
- 生命周期管理 (ACTIVE/PAUSED/ENDED)
- 拥有 ContextOrchestrator

### 3. ContextOrchestrator

**位置**: `loom/context/orchestrator.py`

**职责**:
- 从 7 大来源收集上下文
- Token 预算管理
- 优先级排序
- 压缩策略

## 数据流

### 聚合流（多 Session → Agent）

```
Agent 请求上下文
       │
       ▼
ContextController.aggregate_context([A, B, C])
       │
       ├──► Session A.build_context()
       ├──► Session B.build_context()
       └──► Session C.build_context()
       │
       ▼
合并 + 排序 + 裁剪
       │
       ▼
返回给 Agent
```

### 分发流（Agent → 多 Session）

```
Agent 产生 Task
       │
       ▼
ContextController.distribute_task(task, [A, B, C])
       │
       ├──► Session A.add_task(task)
       ├──► Session B.add_task(task)
       └──► Session C.add_task(task)
```

## ContextSource 接口体系

### 基础接口

```python
class ContextSource(ABC):
    """上下文来源抽象接口"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """来源名称"""
        pass

    @abstractmethod
    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: TokenCounter,
    ) -> list[ContextBlock]:
        """收集上下文"""
        pass
```

### 7 大 Source 实现

| Source | 位置 | 状态 |
|--------|------|------|
| UserInputSource | `context/sources/user.py` | 待实现 |
| AgentOutputSource | `context/sources/agent.py` | 待实现 |
| L1RecentSource | `context/sources/memory.py` | ✅ 已有 |
| L2ImportantSource | `context/sources/memory.py` | ✅ 已有 |
| RAGKnowledgeSource | `context/sources/rag.py` | ✅ 已有 |
| PromptSource | `context/sources/prompt.py` | 待实现 |
| ToolSource | `context/sources/tool.py` | 待实现 |
| SkillSource | `context/sources/skill.py` | 待实现 |

## Token 预算分配

### 设计原则

**按比例配置**：用户配置模型的总 token 量（不同模型上下文窗口不同），系统按比例分配。

```python
# 用户配置
model_context_window = 128000  # Claude: 200K, GPT-4: 128K, 小模型: 8K
output_reserve_ratio = 0.10    # 预留输出比例

# 系统自动计算
available = model_context_window * (1 - output_reserve_ratio)
# 然后按比例分配给各来源
```

### 默认分配比例

```
可用预算 = 总预算 × (1 - 预留输出比例)

├── system_prompt: 12%  # 系统提示词
├── user_input: 12%     # 用户输入
├── tools: 15%          # 工具定义
├── skills: 10%         # 技能定义
├── L1_recent: 18%      # 最近任务
├── L2_important: 12%   # 重要任务
├── L4_semantic: 6%     # 语义检索
├── RAG_knowledge: 10%  # 知识库
└── agent_output: 5%    # Agent输出
```

### 示例计算

| 模型 | 总窗口 | 预留输出(10%) | 可用 | Prompt(12%) | Memory(36%) |
|------|--------|---------------|------|-------------|-------------|
| Claude 3 | 200K | 20K | 180K | 21.6K | 64.8K |
| GPT-4 | 128K | 12.8K | 115.2K | 13.8K | 41.5K |
| 小模型 | 8K | 0.8K | 7.2K | 0.86K | 2.6K |

## 实现计划

### Phase 1: 基础架构
- [x] Session 移到 events 层
- [x] ContextController 基础实现
- [x] Session 整合 ContextOrchestrator

### Phase 2: Source 实现
- [x] ToolSource
- [x] SkillSource
- [x] UserInputSource
- [x] PromptSource
- [x] AgentOutputSource

### Phase 3: 聚合/分发
- [x] 多 Session 聚合
- [x] Task 分发（broadcast, distribute_filtered）
- [x] 预算分配策略（按比例配置）

## 记忆层级与分发体系

### 层级作用域

```
┌──────────────────────────────────────────────────────────────┐
│                     L4: 全局持久化 (EventBus)                 │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  L3: Agent 级聚合                       │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │  │
│  │  │  Session A   │ │  Session B   │ │  Session C   │   │  │
│  │  │ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │   │  │
│  │  │ │L2: 重要  │ │ │ │L2: 重要  │ │ │ │L2: 重要  │ │   │  │
│  │  │ │┌────────┐│ │ │ │┌────────┐│ │ │ │┌────────┐│ │   │  │
│  │  │ ││L1:最近 ││ │ │ ││L1:最近 ││ │ │ ││L1:最近 ││ │   │  │
│  │  │ │└────────┘│ │ │ │└────────┘│ │ │ │└────────┘│ │   │  │
│  │  │ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 层级定义

| 层级 | 作用域 | 分发方式 | 生命周期 | 存储位置 |
|------|--------|----------|----------|----------|
| L1 | Session 私有 | 不分发 | 短期(分钟) | Session.memory |
| L2 | Session 级 | distribute | 中期(小时) | Session.memory |
| L3 | Agent 级 | aggregate | 长期(天) | ContextController |
| L4 | 全局级 | EventBus | 永久 | 持久化存储 |

### 数据流向

```
                    ┌─────────────┐
                    │   Agent     │
                    └──────┬──────┘
                           │ 产生 Task
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    ContextController                          │
│                                                               │
│  ┌─────────────┐      distribute      ┌─────────────┐       │
│  │  Session A  │◄────────────────────►│  Session B  │       │
│  │    L1/L2    │                      │    L1/L2    │       │
│  └──────┬──────┘                      └──────┬──────┘       │
│         │                                    │               │
│         └────────────┬───────────────────────┘               │
│                      │ aggregate                             │
│                      ▼                                       │
│               ┌─────────────┐                                │
│               │     L3      │                                │
│               │  聚合摘要    │                                │
│               └──────┬──────┘                                │
└──────────────────────┼───────────────────────────────────────┘
                       │ persist
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                      EventBus (L4)                            │
│                   全局持久化存储                               │
└──────────────────────────────────────────────────────────────┘
```

### 提升流程

```
L1 ──重要性评估──► L2 ──跨Session聚合──► L3 ──持久化──► L4
     (Session内)      (ContextController)    (EventBus)
```

**触发条件：**

| 提升 | 触发条件 | 方法 |
|------|----------|------|
| L1→L2 | importance > 0.6 | Session.promote_tasks() |
| L2→L3 | 跨 Session 需要 | ContextController.aggregate_context() |
| L3→L4 | 会话结束/定时 | EventBus.publish(persist_action) |

### Phase 4: 记忆层级实现

- [x] L3 聚合存储（ContextController 层）
- [x] L4 持久化接口（EventBus 层）
- [x] 提升触发器实现
- [x] 跨 Session 记忆共享
