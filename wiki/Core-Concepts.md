# 核心概念

理解 Loom 的核心架构。

## 能力等级

Loom 采用渐进式能力模型：

- **L0**: 基础循环 (Context + Memory + Loop)
- **L1**: 可续存 (外部持久化)
- **L2**: 受约束 (Scene + 边界)
- **L3**: 可验证 (Verifier + 事件日志)

v0.7.0 实现了完整的 L2。

## 核心组件

### StepExecutor

统一的工具调用执行入口，自动完成：
1. 资源配额检查
2. 约束验证
3. 工具执行
4. 轨迹记录
5. 状态更新
6. 输出过滤

### PartitionManager

管理 5 个上下文分区：
- system: 基础 prompt
- working: 当前任务状态
- memory: L2/L3 检索
- skill: 激活的技能
- history: 对话历史

### SceneManager

场景包系统，支持：
- 工具白名单
- 约束定义
- 场景组合（约束收窄）

### BoundaryDetector

检测 4 类边界：
- 物理边界 (token 耗尽)
- 权限边界 (缺少权限)
- 能力边界 (超出能力)
- 时间边界 (超时)

### WorkingState

预算化的工作状态：
- 固定预算 (2000 tokens)
- 推荐 schema
- overflow 字段

下一步 → [API 参考](./API-Reference.md)
