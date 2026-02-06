---
name: Code Review
description: 代码审查技能，检查代码质量和最佳实践
required_tools:
  - read_file
  - grep
---

# Code Review Instructions

## 审查流程

1. **结构分析** - 检查代码组织
2. **命名规范** - 验证变量和函数命名
3. **错误处理** - 检查异常处理
4. **安全检查** - 识别潜在漏洞

## 输出格式

```json
{
  "summary": "审查摘要",
  "issues": ["问题列表"],
  "suggestions": ["改进建议"]
}
```
