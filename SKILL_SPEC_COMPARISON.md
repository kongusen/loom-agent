# Skill 系统规范对比

## Claude Code 规范 vs Loom 实现

### ✅ 已实现的核心特性

| 特性 | Claude Code | Loom 实现 | 状态 |
|------|-------------|-----------|------|
| **Markdown + YAML frontmatter** | ✅ | ✅ | 完全一致 |
| **懒加载（Lazy Loading）** | ✅ | ✅ | 完全一致 |
| **参数替换** | `$ARGUMENTS`, `${ARG_NAME}` | `$ARGUMENTS`, `${ARGUMENTS}` | 部分实现 |
| **工具限制** | `allowed-tools` | `allowedTools` | ✅ 完全一致 |
| **关键词匹配** | `when_to_use` | `whenToUse` | ✅ 完全一致 |
| **用户可调用** | `user-invocable` | `userInvocable` | ✅ 完全一致 |
| **模型覆盖** | `model` | `model` | ✅ 完全一致 |
| **执行上下文** | `context: fork` | `context` | ✅ 完全一致 |

### ⚠️ 部分实现的特性

| 特性 | Claude Code | Loom 实现 | 差异 |
|------|-------------|-----------|------|
| **命名参数** | `arguments: [name, email]` | 不支持 | 只支持 `$ARGUMENTS` |
| **Shell 执行** | `!`command`` 内联执行 | 不支持 | 需要手动调用 Bash 工具 |
| **环境变量替换** | `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}` | 不支持 | 可以添加 |
| **Hooks** | `hooks: {onLoad, onInvoke}` | 不支持 | 高级特性 |
| **路径限制** | `paths: [src/**]` | 不支持 | 高级特性 |

### ❌ 未实现的高级特性

| 特性 | Claude Code | Loom 实现 | 说明 |
|------|-------------|-----------|------|
| **Effort 级别** | `effort: 1-5` | 不支持 | 控制 token 预算 |
| **Agent 类型** | `agent: general-purpose` | 不支持 | 指定子 agent 类型 |
| **版本控制** | `version: 1.0.0` | 不支持 | Skill 版本管理 |
| **Shell 配置** | `shell: {command, args}` | 不支持 | 自定义 shell |
| **渐进式 token 估算** | `estimateSkillFrontmatterTokens()` | 不支持 | 只加载 frontmatter 估算 |

## 渐进式加载机制对比

### Claude Code 实现

```typescript
// 1. 扫描时只解析 frontmatter
const frontmatter = parseFrontmatter(content)
const skill = {
  name: frontmatter.name,
  description: frontmatter.description,
  whenToUse: frontmatter.when_to_use,
  // 内容通过 getPromptForCommand 懒加载
  async getPromptForCommand(args, context) {
    let content = markdownContent  // 首次访问时才加载
    content = substituteArguments(content, args)
    content = await executeShellCommandsInPrompt(content)
    return content
  }
}
```

### Loom 实现

```python
# 1. 扫描时注册 lazy loader
registry.register_lazy(
    skill_name,
    lambda p=skill_file: SkillLoader.load_from_file(p)
)

# 2. 首次访问时加载完整内容
def get(name: str) -> Skill | None:
    if name in self._loaders:
        skill = self._loaders[name]()  # 懒加载
        self.skills[name] = skill
        del self._loaders[name]
        return skill
```

**差异**：
- ✅ 两者都实现了懒加载
- ⚠️ Claude Code 在调用时才加载内容（更懒）
- ⚠️ Loom 在首次访问时加载全部内容（稍微积极）

## 建议改进

### P0 - 关键特性（建议实现）

1. **命名参数支持**
   ```python
   # 支持 arguments: [name, email]
   content = content.replace('${name}', args['name'])
   content = content.replace('${email}', args['email'])
   ```

2. **环境变量替换**
   ```python
   content = content.replace('${CLAUDE_SKILL_DIR}', skill_dir)
   content = content.replace('${CLAUDE_SESSION_ID}', session_id)
   ```

3. **更懒的加载**
   ```python
   # 只在 skill_invoke 时加载内容，而不是在 get() 时
   class Skill:
       _content: str | None = None

       @property
       def content(self) -> str:
           if self._content is None:
               self._content = self._load_content()
           return self._content
   ```

### P1 - 增强特性（可选）

4. **Effort 级别** - 控制 token 预算
5. **Shell 内联执行** - `!`command`` 语法
6. **Hooks 系统** - onLoad, onInvoke 钩子

### P2 - 高级特性（低优先级）

7. **路径限制** - `paths: [src/**]`
8. **版本管理** - `version: 1.0.0`
9. **Agent 类型** - `agent: general-purpose`

## 总结

### 当前实现评分

- **核心功能**: ✅ 95% 完成
- **渐进式加载**: ✅ 90% 完成（略微积极）
- **参数系统**: ⚠️ 60% 完成（缺少命名参数）
- **高级特性**: ❌ 20% 完成（缺少 hooks, effort, shell）

### 是否符合 Claude 规范？

**结论：基本符合，核心功能完整**

✅ **符合的部分**：
- Markdown + YAML frontmatter 格式
- 懒加载机制（略有差异但概念一致）
- 工具限制、关键词匹配、用户可调用
- 模型覆盖、执行上下文

⚠️ **需要改进的部分**：
- 命名参数支持（`${name}` 而不只是 `$ARGUMENTS`）
- 环境变量替换（`${CLAUDE_SKILL_DIR}`）
- 更懒的内容加载（调用时才加载，而不是首次访问时）

❌ **缺少的高级特性**：
- Hooks 系统
- Effort 级别
- Shell 内联执行
- 路径限制

### 建议

对于 Loom 框架的当前阶段，**现有实现已经足够**。核心的渐进式加载和 skill 系统已经完整实现，可以满足大部分使用场景。

如果需要完全对齐 Claude Code，建议优先实现：
1. 命名参数支持
2. 环境变量替换
3. 更懒的内容加载

其他高级特性可以根据实际需求逐步添加。
