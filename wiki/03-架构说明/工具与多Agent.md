# 工具与多Agent

Loom 的"行动能力"主要来自工具系统和多 Agent 协作。

## 工具系统架构

```mermaid
graph TB
    subgraph ToolSystem["工具系统 loom/tools/"]
        Reg["ToolRegistry<br/>工具注册表<br/>register / get / list_tools"]
        Exec["ToolExecutor<br/>工具执行器<br/>统一执行入口"]
        Schema["ToolDefinition<br/>工具定义<br/>name / description / parameters"]
        Pipe["Pipeline<br/>执行管线<br/>前置 → 执行 → 后置"]
        Gov["Governance<br/>工具治理<br/>权限 / 频率 / 策略"]
        Res["ResourceAllocator<br/>资源分配<br/>预算 / 配额"]
    end

    subgraph Builtin["内置工具 loom/tools/builtin/"]
        File["文件操作<br/>read_file / edit_file<br/>write_file / list_directory"]
        Shell["Shell 操作<br/>bash"]
        Search["搜索操作<br/>glob / grep<br/>web_fetch / web_search"]
        Note["Notebook 操作<br/>notebook_edit"]
        MCP["MCP 操作<br/>mcp_tool_call"]
    end

    Reg --> Exec
    Exec --> Schema
    Exec --> Pipe
    Pipe --> Gov
    Gov --> Res
    Reg --> Builtin

    style ToolSystem fill:#3498DB,color:#fff
    style Builtin fill:#2D8659,color:#fff
```

### 工具注册与执行流程

```mermaid
sequenceDiagram
    participant Agent as Agent Core
    participant Reg as ToolRegistry
    participant Gov as Governance
    participant Exec as ToolExecutor
    participant Tool as 具体工具

    Agent->>Reg: register(tool)
    Reg->>Reg: tools[name] = tool

    rect rgb(255, 245, 230)
        Note over Agent,Tool: 工具调用流程
        Agent->>Reg: get("read_file")
        Reg-->>Agent: Tool 对象

        Agent->>Gov: check_permission(tool, context)
        Gov-->>Agent: allowed / denied

        alt 权限通过
            Agent->>Exec: execute(tool, params)
            Exec->>Tool: handler(params)
            Tool-->>Exec: result
            Exec-->>Agent: ToolResult
        else 权限拒绝
            Gov-->>Agent: PermissionDenied
        end
    end
```

### 工具系统代码

| 模块 | 文件 | 职责 |
|---|---|---|
| 工具注册 | `loom/tools/registry.py` | `ToolRegistry` — 注册、查询、列举 |
| 工具定义 | `loom/tools/schema.py` | `Tool`、`ToolDefinition` — 工具元数据 |
| 工具执行 | `loom/tools/executor.py` | `ToolExecutor` — 统一执行入口 |
| 执行管线 | `loom/tools/pipeline.py` | 前置检查 → 执行 → 后置处理 |
| 工具治理 | `loom/tools/governance.py` | 权限、频率限制、策略 |
| 资源分配 | `loom/tools/resource_allocator.py` | 预算、配额管理 |
| 内置工具 | `loom/tools/builtin/` | 文件/Shell/搜索等操作 |
| 知识工具 | `loom/tools/knowledge.py` | 知识检索工具 |
| 证据压缩 | `loom/tools/evidence_compressor.py` | Evidence Pack 压缩 |

### 当前实现判断

| 能力 | 状态 | 说明 |
|---|---|---|
| 工具注册表 | `已实现` | `ToolRegistry` 已可 `register`、`get`、`list_tools`、`unregister` |
| 工具定义模型 | `已实现` | `Tool` + `ToolDefinition` 已明确定义 |
| 工具执行器 | `已实现` | `ToolExecutor` 已存在独立执行层 |
| 工具治理与资源分配 | `部分实现` | `Governance`、`ResourceAllocator` 结构已存在 |
| 内置工具集合 | `已实现` | `loom/tools/builtin/` 已有文件/Shell/搜索等操作 |
| 知识检索工具 | `部分实现` | `knowledge.py` 已有基础骨架 |

## 多 Agent 协作

```mermaid
graph TB
    subgraph Orch["编排层 loom/orchestration/"]
        SAM["SubAgentManager<br/>子 Agent 管理<br/>生成 / 回收 / 深度控制"]
        Coord["Coordinator<br/>协调器<br/>任务分配 / 结果聚合"]
        Planner["Planner<br/>规划器<br/>任务拆解策略"]
        Bus["EventBus<br/>事件总线<br/>Agent 间通信"]
    end

    subgraph Cluster["集群层 loom/cluster/"]
        Fork["Fork<br/>Agent 分叉"]
        SM["SharedMemory<br/>Agent 间共享状态"]
        DMax["DMaxStrategy<br/>最大深度策略"]
        Cache["CacheScheduler<br/>结果缓存"]
        VW["VersionedWriter<br/>版本化写入"]
    end

    Parent["父 Agent"] -->|"拆分任务"| SAM
    SAM -->|"生成"| Child1["子 Agent 1"]
    SAM -->|"生成"| Child2["子 Agent 2"]
    SAM -->|"生成"| ChildN["子 Agent N"]

    Child1 -->|"结果"| Bus
    Child2 -->|"结果"| Bus
    ChildN -->|"结果"| Bus

    Bus -->|"聚合"| Coord
    Coord -->|"回传"| Parent

    SAM --> DMax
    SAM --> Fork
    Child1 --> SM
    Child2 --> SM

    style Orch fill:#D4850A,color:#fff
    style Cluster fill:#7D3C98,color:#fff
```

### 多 Agent 协作流程

```mermaid
sequenceDiagram
    participant Parent as 父 Agent
    participant SAM as SubAgentManager
    participant Planner as Planner
    participant Child as 子 Agent
    participant Bus as EventBus
    participant Coord as Coordinator

    Parent->>Planner: 拆解任务
    Planner-->>Parent: 子任务列表

    loop 每个子任务
        Parent->>SAM: spawn(subtask, depth+1)
        SAM->>SAM: check depth < d_max
        SAM->>Child: 创建并启动子 Agent

        loop 子 Agent 执行
            Child->>Child: L* 闭环
        end

        Child->>Bus: publish(result)
    end

    Bus->>Coord: 聚合所有子结果
    Coord-->>Parent: 合并结果
```

### 多 Agent 代码

| 模块 | 文件 | 职责 |
|---|---|---|
| 子 Agent 管理 | `loom/orchestration/subagent.py` | `SubAgentManager` — 生成、回收、深度控制 |
| 事件总线 | `loom/orchestration/events.py` | `EventBus` — Agent 间通信 |
| 协调器 | `loom/orchestration/coordinator.py` | `Coordinator` — 任务分配与结果聚合 |
| 规划器 | `loom/orchestration/planner.py` | `Planner` — 任务拆解策略 |
| Agent 分叉 | `loom/cluster/fork.py` | `Fork` — Agent 分叉机制 |
| 共享内存 | `loom/cluster/shared_memory.py` | `SharedMemory` — Agent 间共享状态 |
| 深度策略 | `loom/cluster/dmax_strategy.py` | `DMaxStrategy` — 最大深度策略 |
| 缓存调度 | `loom/cluster/cache_scheduler.py` | `CacheScheduler` — 结果缓存 |
| 版本化写入 | `loom/cluster/versioned_writer.py` | `VersionedWriter` — 版本控制 |
| 子结果 | `loom/cluster/subagent_result.py` | 子 Agent 结果封装 |

### 当前实现判断

| 能力 | 状态 | 说明 |
|---|---|---|
| 子 Agent 生成 | `已实现` | `SubAgentManager` 已存在 |
| 最大深度约束 `d_max` | `已实现` | 代码中有递归终止判断 |
| 事件总线 | `已实现` | `EventBus` 已存在 |
| 任务规划器 | `部分实现` | `Planner` 已有基础结构 |
| Fork、共享内存、版本化写入 | `部分实现` | `loom/cluster/` 中已有对应方向的模块 |

## 真实能力表达

- 工具系统已经形成独立能力层，`ToolRegistry` 可直接使用
- 多 Agent 协作已经有基础实现，`SubAgentManager` + `EventBus` 可用
- 高级协作策略（动态调度、自适应拆解）仍在演进
- 不宜包装成完全成熟的编排平台

## 相关页面

- [运行时与决策](运行时与决策.md)
- [生态与安全](生态与安全.md)
- [扩展开发](../../04-开发说明/扩展开发.md)
