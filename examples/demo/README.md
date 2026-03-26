# Loom v0.7.0 Demo 系列

展示 Loom 框架的核心能力，按能力等级组织。

## 能力等级

- **L0**: 基础循环 (Context + Memory + Loop)
- **L1**: 可续存 (外部持久化)
- **L2**: 受约束 (Scene + 边界)

## Demo 列表

### L0 - 基础能力

**01_basic_agent.py**
- 最简单的 Agent 使用
- 展示基础对话和配置

### L2 - 约束能力

**02_scene_constraints.py**
- 场景包系统
- 工具白名单和约束定义

**03_boundary_detection.py**
- 边界检测机制
- 资源配额和腐烂系数

**04_working_state.py**
- 工作状态管理
- 预算化的状态结构

**07_scene_composition.py**
- 场景组合
- 约束收窄规则

### L1 - 持久化能力

**05_memory_layers.py**
- 多层内存系统
- L1/L2/L3 层级检索

**06_skill_system.py**
- 技能加载和使用
- 技能注册表

## 运行方式

```bash
# 设置 API Key
export OPENAI_API_KEY="your-key"

# 运行任意 demo
python examples/demo/01_basic_agent.py
```

## 注意事项

1. 所有 demo 需要配置有效的 LLM Provider API Key
2. Demo 按能力等级组织，建议按顺序学习
3. 每个 demo 聚焦单一概念，代码简洁明了
