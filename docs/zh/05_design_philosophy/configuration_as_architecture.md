# 配置即架构（Configuration as Architecture）

## 核心设计理念

Loom 框架的核心设计理念是**配置即架构**：前端配置可以直接映射为运行时节点结构，无需适配层。

## 节点类型与配置映射关系

### 1. 基础节点（Primitive Nodes）

#### ToolNode - 工具节点
- **配置类型**: `ToolConfig`
- **映射关系**: 一对一直接映射
- **特点**: 封装函数，无状态，可独立存在

```python
# 配置
tool_config = {
    "name": "calculator",
    "python_path": "my_tools.calculate",
    "parameters": {...}
}

# 直接映射为
ToolNode(node_id="calculator", tool_def=..., func=...)
```

#### AgentNode - 智能代理节点
- **配置类型**: `AgentConfig`
- **映射关系**: 一对一直接映射，但可引用 ToolNode
- **特点**: 有状态（Memory），有推理能力（LLM）

```python
# 配置
agent_config = {
    "name": "assistant",
    "role": "助手",
    "tools": ["calculator", "search"],  # 引用已存在的 ToolNode
    "memory": {...},
    "provider": {...}
}

# 直接映射为
AgentNode(
    node_id="assistant",
    tools=[tool_calculator, tool_search],  # 引用已创建的节点
    memory=...,
    provider=...
)
```

### 2. 容器节点（Container Nodes）

容器节点是**包含其他节点引用**的节点，它们封装了**编排规则**或**路由规则**。

#### CrewNode - 编排节点
- **配置类型**: `CrewConfig`
- **映射关系**: 创建节点，但需要引用已存在的 AgentNode
- **特点**: 
  - 是一个**节点**（继承自 Node）
  - 内部包含**编排规则**（pattern: sequential/parallel）
  - 持有其他节点的引用（`agents: List[AgentNode]`）

```python
# 配置
crew_config = {
    "name": "content-crew",
    "pattern": "sequential",  # 编排规则
    "agents": ["researcher", "writer"],  # 引用已存在的 AgentNode
    "sanitizer": {...}  # 上下文清洗规则
}

# 映射为
CrewNode(
    node_id="content-crew",
    agents=[agent_researcher, agent_writer],  # 引用已创建的节点
    pattern="sequential",  # 编排规则
    sanitizer=...
)
```

**关键理解**：
- CrewNode **是节点**，可以被其他节点调用
- CrewNode **包含编排规则**（如何执行 agents）
- CrewNode **引用其他节点**（不是创建，是引用）

#### RouterNode - 路由节点
- **配置类型**: `RouterConfig`
- **映射关系**: 创建节点，但需要引用已存在的 AgentNode
- **特点**:
  - 是一个**节点**（继承自 Node）
  - 内部包含**路由规则**（如何选择目标 Agent）
  - 持有其他节点的引用（`agents: List[AgentNode]`）

```python
# 配置
router_config = {
    "name": "main-router",
    "type": "attention",  # 路由规则类型
    "agents": ["math-agent", "writing-agent"],  # 引用已存在的 AgentNode
    "provider": {...}  # LLM Provider 用于路由决策
}

# 映射为
AttentionRouter(
    node_id="main-router",
    agents=[agent_math, agent_writing],  # 引用已创建的节点
    provider=...  # 路由规则（LLM 决策）
)
```

**关键理解**：
- RouterNode **是节点**，可以被其他节点调用
- RouterNode **包含路由规则**（如何选择目标）
- RouterNode **引用其他节点**（不是创建，是引用）

## 配置结构设计

### 配置的层次结构

```
配置结构 = 运行时结构

{
  "tools": [                    # 第一层：基础节点
    {"name": "tool1", ...}      # → ToolNode
  ],
  "agents": [                   # 第二层：智能节点（可引用 tools）
    {
      "name": "agent1",
      "tools": ["tool1"]        # 引用 tool
    }                           # → AgentNode
  ],
  "crews": [                    # 第三层：编排节点（引用 agents）
    {
      "name": "crew1",
      "pattern": "sequential",
      "agents": ["agent1", "agent2"]  # 引用 agents
    }                           # → CrewNode
  ],
  "routers": [                  # 第四层：路由节点（引用 agents/crews）
    {
      "name": "router1",
      "type": "attention",
      "agents": ["agent1", "agent2"]  # 引用 agents
    }                           # → RouterNode
  ]
}
```

### 配置解析流程

```python
def build_from_config(config: dict, app: LoomApp):
    # 1. 创建基础节点（ToolNode）
    tools = {}
    for tool_config in config.get("tools", []):
        tool_node = ToolFactory.create_node(tool_config, app.dispatcher)
        tools[tool_config["name"]] = tool_node
        app.add_node(tool_node)
    
    # 2. 创建智能节点（AgentNode，可引用 ToolNode）
    agents = {}
    for agent_config in config.get("agents", []):
        # 解析工具引用
        tool_refs = [tools[name] for name in agent_config.get("tools", [])]
        agent_node = AgentFactory.create_node(
            agent_config, 
            app.dispatcher,
            tools=tool_refs
        )
        agents[agent_config["name"]] = agent_node
        app.add_node(agent_node)
    
    # 3. 创建编排节点（CrewNode，引用 AgentNode）
    crews = {}
    for crew_config in config.get("crews", []):
        # 解析 Agent 引用
        agent_refs = [agents[name] for name in crew_config.get("agents", [])]
        crew_node = CrewFactory.create_node(
            crew_config,
            app.dispatcher,
            agents=agent_refs
        )
        crews[crew_config["name"]] = crew_node
        app.add_node(crew_node)
    
    # 4. 创建路由节点（RouterNode，引用 AgentNode）
    routers = {}
    for router_config in config.get("routers", []):
        # 解析 Agent 引用（可以是 AgentNode 或 CrewNode）
        node_refs = []
        for name in router_config.get("agents", []):
            if name in agents:
                node_refs.append(agents[name])
            elif name in crews:
                node_refs.append(crews[name])
        
        router_node = RouterFactory.create_node(
            router_config,
            app.dispatcher,
            agents=node_refs
        )
        routers[router_config["name"]] = router_node
        app.add_node(router_node)
    
    return {"tools": tools, "agents": agents, "crews": crews, "routers": routers}
```

## 分形递归的威力

### 节点可以无限嵌套

```
router-main (RouterNode)
  ├─ crew-research (CrewNode)          ← RouterNode 可以引用 CrewNode
  │   ├─ agent-researcher (AgentNode)   ← CrewNode 引用 AgentNode
  │   │   └─ tool-search (ToolNode)      ← AgentNode 引用 ToolNode
  │   └─ agent-analyst (AgentNode)
  │       └─ tool-calculator (ToolNode)
  └─ crew-content (CrewNode)
      └─ agent-writer (AgentNode)
          └─ tool-writer (ToolNode)
```

**关键点**：
- RouterNode 可以引用 CrewNode（因为 CrewNode 也是 Node）
- CrewNode 可以引用 AgentNode
- AgentNode 可以引用 ToolNode
- 这种嵌套可以无限递归

### 配置即架构的优势

1. **零适配层**：配置结构 = 运行时结构
2. **类型安全**：配置类型直接映射到节点类型
3. **可组合性**：通过引用关系实现复杂拓扑
4. **可扩展性**：新增节点类型只需新增配置类型

## 配置示例

### 完整配置示例

```yaml
# 工具配置
tools:
  - name: calculator
    python_path: my_tools.calculate
    parameters:
      expression:
        type: string
  
  - name: search
    python_path: my_tools.search
    parameters:
      query:
        type: string

# Agent 配置
agents:
  - name: researcher
    role: 研究员
    tools: [search]  # 引用 tool
    memory:
      type: hierarchical
    provider:
      type: openai
      model: gpt-4
  
  - name: writer
    role: 作家
    memory:
      type: metabolic
    provider:
      type: openai
      model: gpt-4

# Crew 配置
crews:
  - name: content-crew
    pattern: sequential
    agents: [researcher, writer]  # 引用 agents
    sanitizer:
      type: bubble-up
      target_token_limit: 100

# Router 配置
routers:
  - name: main-router
    type: attention
    agents: [researcher, writer, content-crew]  # 可以引用 agent 或 crew
    provider:
      type: openai
      model: gpt-4
```

## 总结

### 配置映射关系表

| 配置类型 | 节点类型 | 映射方式 | 引用关系 |
|---------|---------|---------|---------|
| ToolConfig | ToolNode | 直接创建 | 无 |
| AgentConfig | AgentNode | 直接创建 | 可引用 ToolNode |
| CrewConfig | CrewNode | 创建节点 | **引用 AgentNode**（编排规则） |
| RouterConfig | RouterNode | 创建节点 | **引用 AgentNode/CrewNode**（路由规则） |

### 关键理解

1. **CrewNode 和 RouterNode 都是节点**：它们继承自 Node，可以被调用
2. **它们包含规则**：CrewNode 包含编排规则，RouterNode 包含路由规则
3. **它们引用其他节点**：通过引用关系组合成复杂拓扑
4. **配置结构 = 运行时结构**：无需适配层，直接映射

### 设计原则

- ✅ **配置即架构**：配置结构直接映射为运行时结构
- ✅ **引用而非创建**：容器节点引用已存在的节点
- ✅ **规则封装**：编排规则和路由规则封装在节点内部
- ✅ **分形递归**：节点可以无限嵌套，形成复杂拓扑

