# Skill 系统高级特性实现规划

## 优先级分析（Agent 框架视角）

### P0 - 核心 Agent 特性（必须实现）

1. **Agent 类型** (`agent: general-purpose`)
   - 为什么重要：agent 框架的核心是支持不同类型的 agent
   - 用途：指定 skill 应该由哪种 agent 执行
   - 实现难度：中等

2. **Effort 级别** (`effort: 1-5`)
   - 为什么重要：控制 agent 的资源分配和 token 预算
   - 用途：不同任务需要不同的计算资源
   - 实现难度：简单

3. **执行上下文增强** (`context: fork` 已支持，需要完善)
   - 为什么重要：agent 需要隔离执行环境
   - 用途：子 agent 独立运行，避免状态污染
   - 实现难度：中等（已有基础）

### P1 - 增强 Agent 能力（应该实现）

4. **Hooks 系统** (`hooks: {onLoad, onInvoke, onComplete}`)
   - 为什么重要：agent 生命周期管理
   - 用途：在 skill 加载/执行前后执行自定义逻辑
   - 实现难度：中等

5. **Shell 内联执行** (`` !`command` ``)
   - 为什么重要：agent 需要执行系统命令
   - 用途：在 skill 中直接嵌入命令执行
   - 实现难度：中等

6. **路径限制** (`paths: [src/**]`)
   - 为什么重要：限制 agent 的文件访问范围
   - 用途：安全性和权限控制
   - 实现难度：简单

### P2 - 辅助特性（可选实现）

7. **版本控制** (`version: 1.0.0`)
   - 为什么重要：skill 版本管理和兼容性
   - 用途：支持多版本 skill 共存
   - 实现难度：简单

8. **Shell 配置** (`shell: {command, args}`)
   - 为什么重要：自定义 shell 环境
   - 用途：特殊环境下的命令执行
   - 实现难度：简单

9. **渐进式 token 估算** (`estimateSkillFrontmatterTokens()`)
   - 为什么重要：优化 context 管理
   - 用途：只加载 frontmatter 估算 token 消耗
   - 实现难度：简单

## 实现计划

### 阶段 1：核心 Agent 特性（P0）

**目标**：让 Skill 系统真正成为 agent 框架的一部分

#### 1.1 Agent 类型支持

```python
# loom/ecosystem/skill.py
@dataclass
class Skill:
    agent: str | None = None  # general-purpose, code-expert, debug-assistant

# loom/tools/builtin/skill_operations.py
async def skill_invoke(skill: str, args: str = "", agent_type: str | None = None):
    # 根据 skill.agent 选择合适的 agent 执行
    if skill_obj.agent:
        # 使用指定的 agent 类型
        agent = get_agent_by_type(skill_obj.agent)
    else:
        # 使用默认 agent
        agent = get_default_agent()
```

#### 1.2 Effort 级别

```python
@dataclass
class Skill:
    effort: int | None = None  # 1-5, 控制 token 预算

# 在执行时应用 effort
def apply_effort_limit(effort: int) -> int:
    """Convert effort level to token limit"""
    effort_map = {
        1: 1000,    # 简单任务
        2: 2000,    # 中等任务
        3: 4000,    # 复杂任务
        4: 8000,    # 困难任务
        5: 16000,   # 极其复杂任务
    }
    return effort_map.get(effort, 4000)
```

#### 1.3 执行上下文增强

```python
@dataclass
class Skill:
    context: str = "inline"  # inline | fork | isolated

# fork: 子 agent 执行
# isolated: 完全隔离的环境（新进程）
```

### 阶段 2：增强 Agent 能力（P1）

#### 2.1 Hooks 系统

```python
@dataclass
class SkillHooks:
    on_load: str | None = None      # 加载时执行
    on_invoke: str | None = None    # 调用前执行
    on_complete: str | None = None  # 完成后执行
    on_error: str | None = None     # 错误时执行

@dataclass
class Skill:
    hooks: SkillHooks | None = None
```

#### 2.2 Shell 内联执行

```python
# 支持 !`command` 语法
content = """
Current directory: !`pwd`
Git status: !`git status --short`
"""

# 解析并执行
async def execute_inline_shell(content: str) -> str:
    pattern = r'!`([^`]+)`'
    matches = re.findall(pattern, content)
    for cmd in matches:
        result = await execute_bash(cmd)
        content = content.replace(f'!`{cmd}`', result)
    return content
```

#### 2.3 路径限制

```python
@dataclass
class Skill:
    paths: list[str] | None = None  # [src/**, tests/**]

# 在工具执行时检查路径
def check_path_access(file_path: str, allowed_paths: list[str]) -> bool:
    import fnmatch
    for pattern in allowed_paths:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False
```

### 阶段 3：辅助特性（P2）

#### 3.1 版本控制

```python
@dataclass
class Skill:
    version: str | None = None  # 1.0.0

# 支持版本选择
registry.get("code-reviewer", version="1.0.0")
registry.get("code-reviewer", version="latest")
```

#### 3.2 Shell 配置

```python
@dataclass
class ShellConfig:
    command: str = "/bin/bash"
    args: list[str] = field(default_factory=lambda: ["-c"])
    env: dict[str, str] = field(default_factory=dict)

@dataclass
class Skill:
    shell: ShellConfig | None = None
```

#### 3.3 渐进式 token 估算

```python
def estimate_skill_tokens(skill: Skill, load_content: bool = False) -> int:
    """估算 skill 的 token 消耗

    Args:
        skill: Skill 对象
        load_content: 是否加载完整内容（默认只估算 frontmatter）
    """
    if not load_content:
        # 只估算 frontmatter
        text = f"{skill.name} {skill.description} {skill.when_to_use}"
        return len(text.split()) * 1.3  # 粗略估算
    else:
        # 估算完整内容
        return len(skill.content.split()) * 1.3
```

## 实现顺序

### Sprint 1（核心）
1. ✅ Effort 级别 - 1 小时
2. ✅ Agent 类型 - 2 小时
3. ✅ 执行上下文增强 - 1 小时

### Sprint 2（增强）
4. ✅ 路径限制 - 1 小时
5. ✅ Hooks 系统 - 3 小时
6. ✅ Shell 内联执行 - 2 小时

### Sprint 3（辅助）
7. ✅ 版本控制 - 1 小时
8. ✅ Shell 配置 - 1 小时
9. ✅ 渐进式 token 估算 - 1 小时

**总计**: 约 13 小时开发时间

## 成功标准

- [ ] 所有 P0 特性实现并测试通过
- [ ] 至少 80% P1 特性实现
- [ ] 与 Claude Code 规范对齐度达到 95%+
- [ ] 所有示例 skills 正常运行
- [ ] 文档完整更新

## 下一步

开始实现 Sprint 1（核心特性）：
1. Effort 级别
2. Agent 类型
3. 执行上下文增强
