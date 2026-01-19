# 分形递归测试项目设计

## 测试目标

验证loom-agent框架的核心机制：
1. **分形自相似** (A3) - 节点递归组合
2. **认知调度** (A5) - 编排器协调执行
3. **记忆层次** (A4) - 记忆系统迭代
4. **四范式工作** (A6) - Reflection, ToolUse, Planning, MultiAgent

## 测试场景：递归文档分析系统

### 场景描述
构建一个递归文档分析系统，能够：
- 接收文档输入
- 递归分解分析任务
- 多层次协作执行
- 迭代优化结果

### 架构设计

```
DocumentAnalysisSystem (Root Container)
├── PlanningAgent (任务分解)
│   └── 分解为3个子任务
├── AnalysisOrchestrator (编排执行)
│   ├── SummaryAgent (摘要提取)
│   ├── KeywordAgent (关键词提取)
│   └── SentimentAgent (情感分析)
└── ReflectionAgent (质量评估)
    └── 评估结果并决定是否需要重新分析
```

### 测试用例

#### 1. 分形递归测试
- 测试NodeContainer的递归组合
- 验证子节点可以是容器或叶子节点
- 验证execute_task的递归调用

#### 2. 编排器测试
- 测试CrewOrchestrator的并行执行
- 验证多节点协作
- 验证结果聚合

#### 3. 四范式测试
- **Planning**: 任务分解为子任务
- **MultiAgent**: 多个agent协作
- **ToolUse**: 调用分析工具
- **Reflection**: 评估和迭代

#### 4. 记忆系统测试
- 测试中间结果存储
- 测试记忆检索
- 测试记忆层次管理

## 实现计划

### Phase 1: 基础Agent实现
- MockAnalysisAgent: 模拟分析agent
- MockPlanningAgent: 模拟规划agent
- MockReflectionAgent: 模拟反思agent

### Phase 2: 分形结构测试
- 测试单层容器
- 测试多层嵌套容器
- 测试递归执行

### Phase 3: 编排器测试
- 测试并行执行
- 测试结果聚合
- 测试错误处理

### Phase 4: 端到端测试
- 完整场景测试
- 性能测试
- 边界条件测试
