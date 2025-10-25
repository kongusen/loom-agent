# Loom 2.0 快速启动指南

**目标读者**: 继续开发 Loom 2.0 的开发者（包括 AI 助手）
**最后更新**: 2025-10-25

---

## 🚀 3 分钟快速上手

### 当前状态

- ✅ **阶段 1 进行中**（基础架构改造）
- ✅ **Task 1.1 已完成**（AgentEvent 模型）
- ⏳ **Task 1.2 待开始**（重构 Agent.execute() 为流式接口）

### 项目目录结构

```
loom-agent/
├── LOOM_2.0_DEVELOPMENT_PLAN.md    # 📘 总体开发计划（必读）
├── QUICKSTART_GUIDE.md             # 📖 本文件
├── loom/
│   ├── core/
│   │   ├── events.py                # ✅ AgentEvent 模型（已完成）
│   │   ├── agent_executor.py        # ⏳ 待修改（Task 1.2）
│   │   └── context_assembly.py      # 🔜 待创建（Task 1.3）
│   ├── components/
│   │   └── agent.py                 # ⏳ 待修改（Task 1.2）
│   ├── interfaces/
│   │   └── event_producer.py        # ✅ EventProducer Protocol（已完成）
│   └── tasks/                       # 📋 任务规范目录
│       ├── README.md
│       └── PHASE_1_FOUNDATION/
│           ├── task_1.1_agent_events.md  # ✅ 已完成
│           └── task_1.2_streaming_api.md # ⏳ 下一个任务
├── tests/
│   └── unit/
│       └── test_agent_events.py     # ✅ 31 个测试（全部通过）
├── docs/
│   ├── agent_events_guide.md        # ✅ 使用文档（650 行）
│   └── TASK_1.1_COMPLETION_SUMMARY.md # ✅ 完成总结
└── examples/
    └── agent_events_demo.py         # ✅ 演示代码（可运行）
```

---

## 📖 必读文档

### 优先级 1（立即阅读）

1. **`LOOM_2.0_DEVELOPMENT_PLAN.md`** - 总体规划
   - 查看"当前进度"部分
   - 查看"下一步行动"部分

2. **`loom/tasks/PHASE_1_FOUNDATION/task_1.2_streaming_api.md`** - 下一个任务
   - 详细步骤
   - 检查清单
   - 验收标准

### 优先级 2（需要时查阅）

3. **`docs/agent_events_guide.md`** - AgentEvent 使用指南
4. **`docs/TASK_1.1_COMPLETION_SUMMARY.md`** - 上一个任务的完成情况

### 参考资料（可选）

5. **`cc分析/`** - Claude Code 源码分析（设计灵感来源）

---

## 🎯 开始下一个任务（Task 1.2）

### 快速启动命令

```bash
# 1. 进入项目目录
cd /Users/shan/work/uploads/loom-agent

# 2. 阅读任务规范
cat loom/tasks/PHASE_1_FOUNDATION/task_1.2_streaming_api.md

# 3. 运行现有测试（确保基线）
pytest tests/ -v

# 4. 开始编码！
```

### Task 1.2 核心目标

将 `Agent.execute()` 改为返回 `AsyncGenerator[AgentEvent, None]`

**修改的文件**:
1. `loom/components/agent.py` - 新增 `execute()` 流式方法
2. `loom/core/agent_executor.py` - 新增 `execute_stream()` 方法

**新增的文件**:
1. `tests/unit/test_streaming_api.py` - 流式 API 测试
2. `tests/integration/test_agent_streaming.py` - 集成测试

### 实施步骤（详见任务文件）

1. 修改 `Agent` 类
2. 修改 `AgentExecutor` 类
3. 编写测试
4. 更新文档
5. 创建完成总结

---

## 🧪 测试指南

### 运行所有测试

```bash
# 所有测试
pytest tests/ -v

# 只运行单元测试
pytest tests/unit/ -v

# 只运行 AgentEvent 测试
pytest tests/unit/test_agent_events.py -v

# 带覆盖率
pytest tests/ --cov=loom --cov-report=html
```

### 预期结果

当前应该：
- ✅ 31 个 AgentEvent 测试通过
- ✅ 其他现有测试通过（如果有）

---

## 📝 开发规范

### 代码风格

- 遵循 PEP 8
- 使用类型提示
- 添加文档字符串
- 函数名使用蛇形命名法

### 测试要求

- 测试覆盖率 ≥ 80%
- 每个新功能至少 3 个测试
- 包含正常情况 + 边界情况 + 错误情况

### 提交流程

完成任务后：

1. ✅ 运行所有测试
2. ✅ 代码审查（自查）
3. ✅ 创建完成总结文档 `docs/TASK_X.X_COMPLETION_SUMMARY.md`
4. ✅ 更新 `LOOM_2.0_DEVELOPMENT_PLAN.md` 的"当前进度"
5. ✅ 更新 `loom/tasks/README.md`

---

## 🔍 调试技巧

### 查看事件流

```python
# 使用 EventCollector 调试
from loom.core.events import EventCollector

collector = EventCollector()
async for event in agent.execute(prompt):
    collector.add(event)
    print(f"Event: {event.type.value}")

# 分析
print(f"Total events: {len(collector.events)}")
print(f"LLM content: {collector.get_llm_content()}")
```

### 运行演示

```bash
# 运行 AgentEvent 演示
PYTHONPATH=/Users/shan/work/uploads/loom-agent python examples/agent_events_demo.py
```

---

## 💡 常见问题

### Q1: 从哪里开始？

**A**: 阅读 `loom/tasks/PHASE_1_FOUNDATION/task_1.2_streaming_api.md`，按照步骤执行。

### Q2: 我需要了解 Claude Code 吗？

**A**: 不需要深入了解，但 `cc分析/` 目录下的文档提供了有用的设计灵感。

### Q3: 测试失败怎么办？

**A**:
1. 确保运行的是正确的测试文件
2. 检查依赖是否安装
3. 查看错误日志
4. 参考现有测试的写法

### Q4: 如何验证向后兼容性？

**A**:
```python
# 旧代码应该仍然工作
result = await agent.run(prompt)  # 返回字符串

# 新代码使用流式 API
async for event in agent.execute(prompt):
    ...
```

---

## 🎓 学习资源

### Loom 2.0 核心概念

1. **AgentEvent** - 统一事件模型
   - 24 种事件类型
   - 流式架构基础
   - 参考：`docs/agent_events_guide.md`

2. **ContextAssembler** - 动态上下文组装（Task 1.3）
   - 基于优先级
   - Token 预算管理
   - 修复 RAG Context Bug

3. **ToolOrchestrator** - 智能工具编排（Task 2.1）
   - 只读工具并行
   - 写入工具顺序

### 设计原则

1. **流式优先** - 所有组件产生 AgentEvent
2. **向后兼容** - 保留 `run()` 等旧 API
3. **类型安全** - 使用枚举和数据类
4. **测试驱动** - 80%+ 覆盖率

---

## 📞 获取帮助

### 文档位置

| 主题 | 文档路径 |
|------|----------|
| 总体计划 | `LOOM_2.0_DEVELOPMENT_PLAN.md` |
| 任务规范 | `loom/tasks/PHASE_X/task_X.X_*.md` |
| API 文档 | `docs/agent_events_guide.md` |
| 完成总结 | `docs/TASK_X.X_COMPLETION_SUMMARY.md` |

### 示例代码

| 示例 | 文件路径 |
|------|----------|
| AgentEvent 演示 | `examples/agent_events_demo.py` |
| 单元测试示例 | `tests/unit/test_agent_events.py` |

---

## ✅ 开发检查清单

### 每次开始开发前

- [ ] 阅读 `LOOM_2.0_DEVELOPMENT_PLAN.md` 的"当前进度"
- [ ] 确认下一个任务
- [ ] 阅读任务规范文件
- [ ] 运行现有测试（确保基线）

### 开发过程中

- [ ] 遵循任务规范的步骤
- [ ] 逐项完成检查清单
- [ ] 编写测试用例
- [ ] 运行测试验证

### 完成任务后

- [ ] 所有测试通过
- [ ] 代码审查
- [ ] 创建完成总结
- [ ] 更新开发计划文档

---

## 🚦 项目状态速查

| 指标 | 当前值 | 目标 |
|------|--------|------|
| 完成任务 | 1/9 | 9/9 |
| 进度 | 11% | 100% |
| 当前阶段 | 阶段 1 | 阶段 3 |
| 测试覆盖率 | 100% (AgentEvent) | 80%+ (全部) |

---

**最后更新**: 2025-10-25
**下次更新**: Task 1.2 完成后

---

## 📌 快速命令参考

```bash
# 测试
pytest tests/ -v
pytest tests/unit/test_agent_events.py -v

# 演示
PYTHONPATH=. python examples/agent_events_demo.py

# 查看任务
cat loom/tasks/PHASE_1_FOUNDATION/task_1.2_streaming_api.md

# 查看进度
cat LOOM_2.0_DEVELOPMENT_PLAN.md | grep "当前进度" -A 20
```

---

祝开发顺利！🎉
