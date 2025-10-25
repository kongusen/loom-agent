# Task 2.4 分析：Loom-agent 的 Prompt 工程设计

**日期**: 2025-10-25
**状态**: 🔍 设计分析阶段

---

## 📋 核心矛盾

### Claude Code 的定位
- **终端用户产品** - 直接面向开发者用户的 CLI 工具
- **控制权集中** - Anthropic 完全控制行为规则和安全边界
- **固定工作流** - Git commit、PR 创建等流程硬编码
- **统一体验** - 所有用户获得相同的指导和限制

### Loom-agent 的定位
- **开发者框架** - 供其他开发者集成到自己的应用中
- **控制权分散** - 框架使用者需要自定义 Agent 行为
- **灵活工作流** - 不同应用场景需要不同的工具使用模式
- **定制体验** - 每个集成方可能有完全不同的需求

**关键问题**：如何在保留开发者自由度的同时，提供类似 Claude Code 的 Prompt 工程质量？

---

## 🔍 Claude Code Prompt 工程深度分析

### 1. 工具指导的层级结构

Claude Code 的每个工具都有多层指导：

```
Layer 0: 工具基础定义
  ├─ name: "ReadFileTool"
  ├─ description: "读取文件"
  └─ inputSchema: {...}

Layer 1: 使用说明（Usage）
  ├─ 必需参数说明
  ├─ 可选参数默认值
  ├─ 输出格式说明
  └─ 特殊文件类型处理

Layer 2: 最佳实践（Best Practices）
  ├─ 批量操作建议："speculatively read multiple files"
  ├─ 参数选择建议："recommended to read the whole file"
  └─ 错误处理建议："It is okay to read a file that does not exist"

Layer 3: 安全规则（CRITICAL/IMPORTANT）
  ├─ 禁止操作："NEVER use find/grep"
  ├─ 必须操作："ALWAYS use absolute paths"
  └─ 条件操作："If sandbox=true fails, retry with sandbox=false"

Layer 4: 反模式警告（Anti-patterns）
  ├─ 常见错误："Do not include line numbers in old_string"
  ├─ 性能陷阱："Avoid using BashTool for grep"
  └─ 惩罚机制："-$1000 penalty"

Layer 5: 工作流编排（Workflows）
  ├─ 多步骤流程："Step 1... Step 2... Step 3..."
  ├─ 并行执行建议："batch your tool calls together"
  └─ 错误恢复逻辑："If commit fails, retry ONCE"
```

**关键洞察**：Claude Code 的强大不在于单个指令，而在于**层级化的系统性指导**。

---

### 2. Prompt 工程的三大核心技术

#### 技术 1: 行为塑造（Behavioral Shaping）

```typescript
// Claude Code 的极简主义强制
"IMPORTANT: Keep your responses short...
You MUST answer concisely with fewer than 4 lines...
One word answers are best."

// 配合反模式清单
"Avoid text before/after your response, such as:
- 'The answer is <answer>.'
- 'Here is the content of the file...'
- 'Based on the information provided...'"
```

**效果**：通过重复强调 + 具体反例，强制 LLM 改变输出风格。

**Loom-agent 适用性**：⚠️ **有限制**
- 终端用户产品可以强制极简输出
- 但框架使用者可能希望 Agent 详细解释过程（如教育应用）
- **结论**：需要让开发者可配置输出风格

---

#### 技术 2: 安全规则分层（Safety Layers）

```typescript
// Layer 1: 工具级禁止
"NEVER use find/grep - use GrepTool instead"

// Layer 2: 条件安全
"Use sandbox=true for read operations
Use sandbox=false for write/network operations"

// Layer 3: 路径安全
"Validate paths are within project boundaries"

// Layer 4: 命令注入检测
"If command contains injection patterns, return 'command_injection_detected'"
```

**效果**：多层防御确保安全性。

**Loom-agent 适用性**：✅ **完全适用**
- 已实现 SecurityValidator 的 4 层安全检查
- 但需要将安全规则通过 Prompt 传达给 LLM
- **结论**：安全规则应该**硬编码到框架层**，不允许开发者禁用

---

#### 技术 3: 工作流自动化（Workflow Automation）

```typescript
// Git Commit 工作流
"Step 1: Run git status, git diff, git log IN PARALLEL
Step 2: Analyze changes in <commit_analysis> tags
Step 3: Run git add, git commit, git status IN PARALLEL
Step 4: If commit fails, retry ONCE"
```

**效果**：复杂操作被分解为可执行步骤。

**Loom-agent 适用性**：❌ **不适用**
- Claude Code 硬编码了 Git/PR 工作流
- Loom-agent 用户可能没有 Git 需求（可能是数据分析、自动化测试等）
- **结论**：工作流应该由**开发者自定义**，框架只提供模板

---

## 🎯 Loom-agent 的 Prompt 工程设计原则

基于上述分析，提出以下设计原则：

### 原则 1: 三层 Prompt 架构 ⭐⭐⭐

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Framework Core Prompts (Hard-coded)           │
│ - 安全规则（NEVER/ALWAYS）                              │
│ - 工具选择偏好（Prefer specialized tools）              │
│ - 基础工具使用说明                                      │
│                                                          │
│ 📌 开发者无法修改                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Developer Customization (Config)              │
│ - 行为风格（verbose/concise/balanced）                  │
│ - 工作流模板（可选，如 git_workflow）                   │
│ - 应用特定规则（domain-specific guidance）             │
│                                                          │
│ 📌 开发者通过配置控制                                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Tool-Specific Prompts (Per-tool)              │
│ - 每个工具的详细指导                                    │
│ - 开发者可以覆盖/扩展                                   │
│ - 框架提供默认值                                        │
│                                                          │
│ 📌 开发者可以完全自定义                                 │
└─────────────────────────────────────────────────────────┘
```

---

### 原则 2: 配置驱动的 Prompt 生成

```python
# 开发者可以这样配置
agent = Agent(
    llm=llm,
    tools=tools,
    prompt_config=PromptConfig(
        # Layer 2: 行为风格
        verbosity="concise",  # or "detailed", "balanced"

        # Layer 2: 启用内置工作流
        workflows=["git_commit", "error_recovery"],

        # Layer 2: 应用特定规则
        domain_rules=[
            "Focus on data analysis tasks",
            "Always validate data before processing",
            "Prefer pandas over raw Python loops"
        ],

        # Layer 3: 工具级自定义
        tool_prompts={
            "read_file": ToolPrompt(
                usage_notes="Our files are always UTF-8 encoded",
                best_practices=["Read entire files when possible"],
                warnings=["Never read files > 10MB"]
            )
        },

        # 完全禁用框架默认 Prompt（高级用法）
        use_framework_prompts=True,  # False 则完全自定义
    )
)
```

---

### 原则 3: 模板 + 变量的灵活系统

框架提供 Prompt 模板，开发者可以通过变量自定义：

```python
# 框架内置模板
TOOL_USAGE_TEMPLATE = """
## {tool_name}

{description}

### Usage
{usage_notes}

### Best Practices
{best_practices}

{#if critical_rules}
### CRITICAL
{critical_rules}
{/if}

{#if custom_rules}
### Additional Guidelines
{custom_rules}
{/if}
"""

# 开发者只需填充变量
tool_prompt = ToolPrompt(
    description="Read CSV files",
    usage_notes="- Specify encoding if not UTF-8\n- Returns DataFrame",
    best_practices=["Always check file size first"],
    critical_rules=["NEVER read files > 100MB"],
    custom_rules=developer_rules  # 开发者自定义
)
```

---

### 原则 4: 内置 vs 自定义的清晰边界

| Prompt 类型 | 框架提供 | 开发者可修改 | 说明 |
|------------|---------|-------------|------|
| **安全规则** | ✅ 内置硬编码 | ❌ 不可修改 | 路径安全、命令注入检测 |
| **工具选择偏好** | ✅ 内置默认 | ⚠️ 可覆盖 | "Prefer GrepTool over Bash grep" |
| **输出风格** | ✅ 提供预设 | ✅ 完全自定义 | concise/balanced/detailed |
| **工作流** | ✅ 提供模板 | ✅ 选择性启用 | Git/PR/Testing 等 |
| **工具说明** | ✅ 基础版本 | ✅ 可扩展 | 开发者添加应用特定说明 |
| **应用领域规则** | ❌ 不提供 | ✅ 完全自定义 | 由开发者定义 |

---

## 💡 具体实施方案

### 方案 A: 轻量级方案（推荐 ⭐）

**适合场景**：快速实现，保持框架简洁

**核心思路**：
1. 框架提供 **PromptBuilder** 类，负责组装 System Prompt
2. 开发者通过配置对象自定义行为
3. 工具级 Prompt 通过 `tool.prompt_template` 属性提供

**实现**：

```python
# 1. 工具定义增加 prompt 属性
class BaseTool(ABC):
    name: str
    description: str
    args_schema: type[BaseModel]

    # 🆕 Loom 2.0 - Prompt engineering
    prompt_template: Optional[str] = None
    """
    Optional detailed prompt for this tool.
    Can use variables: {tool_name}, {description}, {args_schema}
    """

    best_practices: List[str] = []
    """List of best practice instructions."""

    critical_rules: List[str] = []
    """List of CRITICAL rules (NEVER/ALWAYS)."""

# 2. PromptBuilder 组装系统提示
class PromptBuilder:
    """Build system prompts from layered configuration."""

    def __init__(
        self,
        tools: Dict[str, BaseTool],
        config: PromptConfig,
        security_validator: Optional[SecurityValidator] = None
    ):
        self.tools = tools
        self.config = config
        self.security_validator = security_validator

    def build_system_prompt(self) -> str:
        """Build complete system prompt."""
        sections = []

        # Layer 1: Framework core (always included)
        sections.append(self._build_core_instructions())

        # Layer 1: Security rules (if validator present)
        if self.security_validator:
            sections.append(self._build_security_rules())

        # Layer 2: Tool selection preferences
        sections.append(self._build_tool_preferences())

        # Layer 2: Verbosity style
        sections.append(self._build_verbosity_instructions(
            self.config.verbosity
        ))

        # Layer 2: Custom domain rules
        if self.config.domain_rules:
            sections.append(self._build_domain_rules(
                self.config.domain_rules
            ))

        # Layer 3: Tool-specific prompts
        sections.append(self._build_tool_instructions())

        # Layer 2: Workflows (if enabled)
        if self.config.workflows:
            sections.append(self._build_workflow_instructions(
                self.config.workflows
            ))

        return "\n\n".join(sections)

    def _build_core_instructions(self) -> str:
        """Core framework instructions (immutable)."""
        return """
# Core Instructions

You are an AI agent powered by the Loom framework. You have access to tools to complete tasks.

## Fundamental Rules

- **NEVER** execute tools you're unsure about
- **ALWAYS** read files before editing them
- **NEVER** guess tool parameters - ask the user if unclear
- When multiple tools are independent, call them in parallel for better performance
"""

    def _build_security_rules(self) -> str:
        """Security instructions from SecurityValidator."""
        return """
# Security Rules

## Path Security (CRITICAL)
- **NEVER** use path traversal patterns (../)
- **ALWAYS** use paths within the working directory
- System paths (/etc, /sys, /proc) are FORBIDDEN

## Command Safety
- Validate all bash commands for injection patterns
- Prefer specialized tools over bash commands
- Use sandbox mode when available
"""

    def _build_tool_preferences(self) -> str:
        """Tool selection preferences."""
        return """
# Tool Selection Preferences

- **Prefer** specialized tools over general ones
  - Use GrepTool instead of bash grep
  - Use ReadFileTool instead of bash cat
  - Use GlobTool instead of bash find

- **Batch** independent tool calls for performance
- **Read before write** - always read files before editing
"""

    def _build_verbosity_instructions(self, level: str) -> str:
        """Output verbosity instructions."""
        if level == "concise":
            return """
# Output Style: Concise

- Keep responses short (1-3 sentences)
- Avoid unnecessary explanations
- Get straight to the point
- Only elaborate if explicitly asked
"""
        elif level == "detailed":
            return """
# Output Style: Detailed

- Explain your reasoning step-by-step
- Provide context for your decisions
- Include relevant details and examples
- Help the user understand your thought process
"""
        else:  # balanced
            return """
# Output Style: Balanced

- Provide brief explanations for key decisions
- Balance conciseness with clarity
- Include important details but avoid verbosity
"""

    def _build_tool_instructions(self) -> str:
        """Generate instructions for all tools."""
        tool_sections = []

        for tool in self.tools.values():
            sections = [f"## {tool.name}", "", tool.description]

            # Input schema
            sections.append("\n### Input Parameters")
            sections.append(f"```json\n{self._schema_to_json(tool.args_schema)}\n```")

            # Custom prompt template
            if tool.prompt_template:
                sections.append("\n### Usage Notes")
                sections.append(tool.prompt_template)

            # Best practices
            if tool.best_practices:
                sections.append("\n### Best Practices")
                for practice in tool.best_practices:
                    sections.append(f"- {practice}")

            # Critical rules
            if tool.critical_rules:
                sections.append("\n### CRITICAL")
                for rule in tool.critical_rules:
                    sections.append(f"- {rule}")

            tool_sections.append("\n".join(sections))

        return "# Available Tools\n\n" + "\n\n".join(tool_sections)

    def _build_workflow_instructions(self, workflows: List[str]) -> str:
        """Build workflow instructions."""
        # Load workflow templates from loom/prompts/workflows/
        workflow_sections = []

        for workflow_name in workflows:
            template = self._load_workflow_template(workflow_name)
            if template:
                workflow_sections.append(template)

        if workflow_sections:
            return "# Workflow Automation\n\n" + "\n\n".join(workflow_sections)
        return ""

# 3. 配置对象
@dataclass
class PromptConfig:
    """Configuration for prompt engineering."""

    verbosity: str = "balanced"  # "concise" | "balanced" | "detailed"

    workflows: List[str] = field(default_factory=list)
    """List of workflow templates to include (e.g., ["git_commit", "testing"])."""

    domain_rules: List[str] = field(default_factory=list)
    """Application-specific rules."""

    tool_prompts: Dict[str, ToolPromptOverride] = field(default_factory=dict)
    """Per-tool prompt overrides."""

    use_framework_prompts: bool = True
    """Whether to include framework's default prompts."""

# 4. 集成到 Agent
class Agent:
    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool],
        prompt_config: Optional[PromptConfig] = None,
        # ... other params
    ):
        self.prompt_config = prompt_config or PromptConfig()

        # Build system prompt
        prompt_builder = PromptBuilder(
            tools={t.name: t for t in tools},
            config=self.prompt_config,
            security_validator=security_validator
        )

        system_prompt = prompt_builder.build_system_prompt()

        # Pass to executor
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools,
            system_instructions=system_prompt,
            # ...
        )
```

**优点**：
- ✅ 简单易用 - 开发者只需配置对象
- ✅ 灵活性高 - 可以细粒度控制每个部分
- ✅ 向后兼容 - 不破坏现有 API

**缺点**：
- ⚠️ Prompt 构建在 Python 侧 - 每次都要重新生成
- ⚠️ 缺少 Prompt 版本管理

---

### 方案 B: 重量级方案（功能完整）

**适合场景**：需要 Prompt 版本控制、A/B 测试、动态更新

**核心思路**：
1. Prompt 模板存储在文件系统（`loom/prompts/templates/`）
2. 使用 Jinja2 或自定义模板引擎
3. 支持 Prompt 继承和组合
4. 开发者可以覆盖任何模板

**实现**：

```python
# 目录结构
loom/prompts/
├── templates/
│   ├── core/
│   │   ├── base_instructions.jinja2
│   │   ├── security_rules.jinja2
│   │   └── tool_preferences.jinja2
│   ├── verbosity/
│   │   ├── concise.jinja2
│   │   ├── balanced.jinja2
│   │   └── detailed.jinja2
│   ├── workflows/
│   │   ├── git_commit.jinja2
│   │   ├── pull_request.jinja2
│   │   └── testing.jinja2
│   └── tools/
│       ├── read_file.jinja2
│       ├── bash.jinja2
│       └── ...
├── engine.py  # PromptEngine 类
└── registry.py  # PromptRegistry 类

# PromptEngine
class PromptEngine:
    """Jinja2-based prompt template engine."""

    def __init__(
        self,
        template_dirs: List[Path],
        custom_filters: Optional[Dict] = None
    ):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dirs),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Register custom filters
        if custom_filters:
            self.env.filters.update(custom_filters)

    def render(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Render a template with context."""
        template = self.env.get_template(template_name)
        return template.render(**context)

# 使用
prompt_engine = PromptEngine(
    template_dirs=[
        Path("loom/prompts/templates"),  # Framework templates
        Path("my_app/prompts")  # Developer overrides
    ]
)

system_prompt = prompt_engine.render(
    "system_prompt.jinja2",
    context={
        "tools": tools,
        "verbosity": "concise",
        "workflows": ["git_commit"],
        "domain_rules": my_rules
    }
)
```

**优点**：
- ✅ 模板可版本控制
- ✅ 开发者覆盖非常简单（只需提供同名模板）
- ✅ 支持 Prompt A/B 测试

**缺点**：
- ❌ 增加复杂度 - 引入模板引擎依赖
- ❌ 学习成本 - 开发者需要学习模板语法

---

### 方案 C: 混合方案（平衡 ⭐⭐）

**结合方案 A 和 B 的优点**：

1. **默认使用方案 A**（代码生成 Prompt）- 简单场景
2. **可选使用方案 B**（模板引擎）- 高级场景
3. 提供 `PromptBuilder` 和 `PromptEngine` 两种方式

```python
# 简单场景 - 方案 A
agent = Agent(
    llm=llm,
    tools=tools,
    prompt_config=PromptConfig(verbosity="concise")
)

# 高级场景 - 方案 B
agent = Agent(
    llm=llm,
    tools=tools,
    prompt_engine=PromptEngine(
        template_dirs=["my_app/prompts"],
        template_name="custom_system_prompt.jinja2"
    )
)
```

---

## 📊 对比总结

| 维度 | Claude Code | Loom-agent (建议方案) |
|-----|-------------|---------------------|
| **核心定位** | 终端用户产品 | 开发者框架 |
| **Prompt 控制** | 完全硬编码 | 三层架构（Framework/Developer/Tool） |
| **安全规则** | 硬编码，不可修改 | **硬编码在 Framework 层** |
| **输出风格** | 强制极简 | 可配置（concise/balanced/detailed） |
| **工作流** | 硬编码（Git/PR） | 模板库 + 开发者自定义 |
| **工具说明** | 详尽但固定 | 基础 + 开发者扩展 |
| **领域规则** | 通用编程 | **完全由开发者定义** |

---

## ✅ 推荐方案

**综合建议：采用方案 C（混合方案）**

### Phase 1 实现（MVP - 2-3 天）
1. 实现 `PromptBuilder` 类（方案 A）
2. 实现 `PromptConfig` 配置对象
3. 为所有内置工具添加基础 `prompt_template`
4. 集成到 `Agent.__init__()`
5. 编写 10-15 个测试

### Phase 2 增强（可选 - 2-3 天）
1. 添加 `PromptEngine` 模板引擎（方案 B）
2. 创建工作流模板库（git_commit, testing, etc.）
3. 支持模板继承和覆盖
4. 添加 Prompt 版本控制

### Phase 3 高级特性（未来）
1. Prompt A/B 测试框架
2. Prompt 性能分析（Token 使用、成功率）
3. 社区 Prompt 模板分享
4. Visual Prompt Editor

---

## 🎯 关键设计决策

### 决策 1: 安全规则不可修改 ✅
**理由**：路径遍历、命令注入等安全问题是框架责任，不应让开发者禁用。

### 决策 2: 输出风格可配置 ✅
**理由**：不同应用场景需要不同风格（CLI 工具 vs 聊天机器人 vs 教育应用）。

### 决策 3: 工作流提供模板但不强制 ✅
**理由**：Git 工作流对 Loom-agent 用户不一定相关，但可以作为可选模板。

### 决策 4: 工具说明采用"基础 + 扩展"模式 ✅
**理由**：框架提供基础说明确保质量，开发者可添加应用特定指导。

---

## 🚀 下一步行动

1. **与用户确认设计方向**
   - 方案 A（轻量）vs 方案 B（重量）vs 方案 C（混合）
   - Phase 1 实现范围

2. **创建实现规范**
   - 文件结构
   - 类接口设计
   - 模板格式规范

3. **开始实现**
   - `loom/prompts/builder.py`
   - `loom/prompts/config.py`
   - 工具 prompt 模板

---

**问题讨论**：
1. 你更倾向于哪个方案（A/B/C）？
2. Phase 1 实现范围是否合理？
3. 是否有其他需要考虑的框架约束？
4. 对工作流模板库有什么具体需求？
