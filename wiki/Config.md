# 配置体系

`loom/config/` 实现了渐进式披露（Progressive Disclosure）的配置系统，从零配置到完全自定义。

## 文件结构

```
loom/config/
├── base.py        # 基础配置类
├── agent.py       # AgentConfig - Agent 级配置
├── tool.py        # ToolConfig - 工具配置
├── context.py     # ContextConfig - 上下文配置
├── memory.py      # MemoryConfig - 记忆配置
├── execution.py   # ExecutionConfig - 执行配置
├── fractal.py     # FractalConfig - 分形配置
├── knowledge.py   # KnowledgeConfig - 知识库配置
└── llm.py         # LLMConfig - LLM 配置
```

## 渐进式披露

配置系统支持三个层次，用户按需选择复杂度：

### Level 1 — 零配置

```python
agent = Agent.create(llm, system_prompt="你是一个AI助手")
# 所有配置使用默认值
```

### Level 2 — 聚合配置

```python
agent = Agent.create(
    llm,
    system_prompt="你是一个AI助手",
    tool_config=ToolConfig(
        skills_dir="./skills",
        builtin_tools=["bash", "file", "http"],
    ),
    context_config=ContextConfig(
        max_context_tokens=8000,
        budget_ratios={"L1_recent": 0.3, "L2_important": 0.2},
    ),
)
```

### Level 3 — 完全自定义

```python
agent = Agent.create(
    llm,
    memory_config=MemoryConfig(
        l1=LayerConfig(capacity=8000, retention_hours=24),
        l2=LayerConfig(capacity=16000, retention_hours=168),
        l3=LayerConfig(capacity=32000, auto_compress=True),
        l4=LayerConfig(capacity=100000),
        strategy=MemoryStrategyType.IMPORTANCE_BASED,
    ),
    compaction_config=CompactionConfig(
        trigger_threshold=0.8,
        target_ratio=0.6,
    ),
    session_isolation=SessionIsolationMode.STRICT,
)
```

## AgentConfig

Agent 级配置，支持继承和增量覆盖：

```python
@dataclass
class AgentConfig:
    enabled_skills: set[str]    # 启用的 Skill 集合
    disabled_tools: set[str]    # 禁用的工具集合
    extra_tools: set[str]       # 额外启用的工具
    # ... 其他配置
```

### 配置继承

分形架构中，子节点继承父节点配置并可增量修改：

```python
child_config = AgentConfig.inherit(
    parent=parent_config,
    add_skills={"code_review"},      # 子节点额外启用
    remove_skills={"data_analysis"}, # 子节点禁用
    add_tools={"custom_tool"},
    remove_tools={"bash"},
)
```

## ToolConfig

工具相关配置：

```python
@dataclass
class ToolConfig:
    skills_dir: str | Path | list | None  # Skill 目录
    skill_loaders: list | None            # 自定义加载器
    builtin_tools: list[str] | None       # 内置工具列表
    sandbox_root: str | None              # 沙盒根目录
```

## ContextConfig

上下文管理配置：

```python
@dataclass
class ContextConfig:
    max_context_tokens: int          # 上下文窗口大小
    output_reserve_ratio: float      # 输出预留比例
    budget_ratios: dict[str, float]  # 各源预算比例
```

## MemoryConfig

记忆系统配置：

```python
@dataclass
class MemoryConfig:
    l1: LayerConfig                        # L1 层配置
    l2: LayerConfig                        # L2 层配置
    l3: LayerConfig                        # L3 层配置
    l4: LayerConfig                        # L4 层配置
    strategy: MemoryStrategyType           # 记忆策略
    enable_auto_migration: bool            # 自动迁移
    enable_compression: bool               # 启用压缩
    importance_threshold: float            # 重要性阈值

@dataclass
class LayerConfig:
    capacity: int                          # token 容量
    retention_hours: int | None            # 保留时间
    promote_threshold: int                 # 提升阈值
    auto_compress: bool                    # 自动压缩
```

### MemoryStrategyType

```python
class MemoryStrategyType(StrEnum):
    IMPORTANCE_BASED = "importance_based"  # 基于重要性（默认）
    SIMPLE = "simple"                      # 基于频率
```
