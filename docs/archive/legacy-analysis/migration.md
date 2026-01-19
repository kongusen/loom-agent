# Loom 框架能力迁移分析

> **版本**: v0.4.0-alpha
> **日期**: 2026-01-17
> **目的**: 分析旧实现中可迁移到新公理架构的能力

## 执行摘要

本文档系统分析了旧实现（loom_backup/）中的能力，并按照新架构的六大公理进行分类，识别可迁移的核心能力。

### 迁移优先级

- **P0 (必须)**: 核心功能，框架无法运行
- **P1 (重要)**: 关键特性，显著提升框架能力
- **P2 (有用)**: 增强功能，改善用户体验
- **P3 (可选)**: 边缘功能，可以延后

---

## 第一部分：按公理分类的能力清单

### A1: 统一接口公理 (protocol/)

#### 已迁移
- ✅ `NodeProtocol` - 统一节点接口
- ✅ `AgentCard` - 能力声明协议
- ✅ `Task` - A2A任务协议

#### 可迁移能力

**1. MCP协议支持** (P1)
- 源文件: `loom_backup/protocol/mcp.py`
- 功能: Model Context Protocol 集成
- 价值: 与外部工具生态系统互操作
- 迁移位置: `loom/protocol/mcp.py`
- 工作量: 中等（需要适配新的事件系统）

**2. 协议补丁机制** (P2)
- 源文件: `loom_backup/protocol/patch.py`
- 功能: 运行时协议扩展和修补
- 价值: 支持协议演化和向后兼容
- 迁移位置: `loom/protocol/patch.py`
- 工作量: 小

**3. 记忆操作协议** (P1)
- 源文件: `loom_backup/protocol/memory_operations.py`
- 功能: 标准化的记忆操作接口
- 价值: 统一记忆系统的操作语义
- 迁移位置: `loom/protocol/memory_ops.py`
- 工作量: 小

---

### A2: 事件主权公理 (events/)

#### 已迁移
- ✅ `CloudEvent` - 基于CNCF标准的事件
- ✅ `EventBus` - 事件总线
- ✅ `SSETransport` - SSE传输层

#### 可迁移能力

**1. 多传输层支持** (P1)
- 源文件: `loom_backup/infra/transport/`
  - `memory.py` - 内存传输（单进程）
  - `nats.py` - NATS传输（分布式）
  - `redis.py` - Redis传输（分布式）
- 功能: 支持多种传输后端，适应不同部署场景
- 价值:
  - Memory: 开发和测试
  - NATS: 高性能分布式部署
  - Redis: 简单分布式部署
- 迁移位置: `loom/events/transports/`
- 工作量: 中等（需要统一接口）

**2. 事件存储和回放** (P2)
- 源文件: `loom_backup/infra/store.py`
- 功能: 事件持久化和历史回放
- 价值: 调试、审计、事件溯源
- 迁移位置: `loom/events/store.py`
- 工作量: 中等

**3. 结构化日志系统** (P2)
- 源文件: `loom_backup/infra/logging.py`
- 功能: 与事件系统集成的结构化日志
- 价值: 可观测性、调试
- 迁移位置: `loom/events/logging.py`
- 工作量: 小

---

### A3: 分形自相似公理 (fractal/)

#### 已迁移
- ✅ `FractalOrchestrator` - 基础分形编排
- ✅ `FractalContainer` - 分形容器

#### 可迁移能力

**1. 结果合成器** (P0)
- 源文件: `loom_backup/kernel/fractal/synthesizer.py`
- 功能: 智能合成子任务结果
- 价值: 分形编排的核心能力，将子结果聚合为最终答案
- 迁移位置: `loom/fractal/synthesizer.py`
- 工作量: 中等（核心逻辑可复用）

**2. 模板管理器** (P1)
- 源文件: `loom_backup/kernel/fractal/template_manager.py`
- 功能: 管理分解模板和策略
- 价值: 提供预定义的分解模式，提升分解质量
- 迁移位置: `loom/fractal/templates.py`
- 工作量: 中等

**3. 分形工具集** (P1)
- 源文件: `loom_backup/kernel/fractal/fractal_utils.py`
- 功能: 分形相关的工具函数
- 价值: 简化分形操作，提供常用功能
- 迁移位置: `loom/fractal/utils.py`
- 工作量: 小

**4. 委托协议** (P0)
- 源文件: `loom_backup/protocol/delegation.py`
- 功能: 标准化的委托请求/响应协议
- 价值: 分形编排的通信基础
- 迁移位置: `loom/fractal/delegation.py`
- 工作量: 小

---

### A4: 记忆层次公理 (memory/)

#### 已迁移
- ✅ `MemoryHierarchy` - L1-L4层次结构
- ✅ `MemoryLayer` - 单层记忆抽象

#### 可迁移能力

**1. 完整的记忆系统实现** (P0)
- 源文件: `loom_backup/memory/core.py`
- 功能: 完整的L1-L4记忆实现
- 价值: 框架的核心能力，必须迁移
- 迁移位置: `loom/memory/core.py`
- 工作量: 大（需要重构以适配新架构）

**2. L4压缩算法** (P0)
- 源文件: `loom_backup/memory/compression.py`
- 功能: 语义感知的记忆压缩
- 价值: 保证记忆收敛性（定理T3）
- 迁移位置: `loom/memory/compression.py`
- 工作量: 中等

**3. 向量存储** (P0)
- 源文件: `loom_backup/memory/vector_store.py`
- 功能: L4的向量化存储和检索
- 价值: 语义记忆的基础
- 迁移位置: `loom/memory/vector_store.py`
- 工作量: 中等

**4. 嵌入生成** (P0)
- 源文件: `loom_backup/memory/embedding.py`
- 功能: 文本向量化
- 价值: 向量存储的前置依赖
- 迁移位置: `loom/memory/embedding.py`
- 工作量: 小

**5. 记忆策略** (P1)
- 源文件: `loom_backup/memory/strategies.py`
- 功能: 不同的记忆管理策略
- 价值: 灵活的记忆行为配置
- 迁移位置: `loom/memory/strategies.py`
- 工作量: 中等

**6. 上下文管理** (P1)
- 源文件: `loom_backup/memory/context.py`
- 功能: 上下文窗口管理和优化
- 价值: 高效利用LLM上下文
- 迁移位置: `loom/memory/context.py`
- 工作量: 中等

**7. 记忆度量** (P2)
- 源文件: `loom_backup/memory/metrics.py`
- 功能: 记忆系统的性能指标
- 价值: 可观测性和优化
- 迁移位置: `loom/memory/metrics.py`
- 工作量: 小

**8. 记忆可视化** (P2)
- 源文件: `loom_backup/memory/visualizer.py`
- 功能: 记忆结构的可视化
- 价值: 调试和理解
- 迁移位置: `loom/memory/visualizer.py`
- 工作量: 小

**9. 内容清理** (P1)
- 源文件: `loom_backup/memory/sanitizers.py`
- 功能: 清理和规范化记忆内容
- 价值: 保证记忆质量
- 迁移位置: `loom/memory/sanitizers.py`
- 工作量: 小

**10. Token计数** (P1)
- 源文件: `loom_backup/memory/tokenizer.py`
- 功能: 准确的token计数
- 价值: 上下文管理的基础
- 迁移位置: `loom/memory/tokenizer.py`
- 工作量: 小

**11. 记忆工厂** (P1)
- 源文件: `loom_backup/memory/factory.py`
- 功能: 记忆系统的创建和配置
- 价值: 简化记忆系统的初始化
- 迁移位置: `loom/memory/factory.py`
- 工作量: 小

**12. 记忆类型定义** (P1)
- 源文件: `loom_backup/memory/types.py`
- 功能: 记忆相关的类型定义
- 价值: 类型安全
- 迁移位置: `loom/memory/types.py`
- 工作量: 小

---

## 小结（第一部分）

第一部分分析了A1-A4四个公理相关的可迁移能力。关键发现：

1. **记忆系统最为完整** - 旧实现有12个记忆相关文件，几乎都需要迁移
2. **事件系统需要增强** - 多传输层支持是关键
3. **分形系统缺少合成器** - 这是P0优先级，必须迁移
4. **协议层相对完整** - 主要补充MCP和记忆操作协议

---

## 第二部分：A5、A6和Runtime能力分析

### A5: 认知调度公理 (orchestration/)

#### 已迁移
- ✅ `AttentionRouter` - 智能路由
- ✅ `CrewNode` - 团队协作
- ✅ `FractalOrchestrator` - 分形编排（基础版）

#### 可迁移能力

**1. Pipeline构建器** (P1)
- 源文件: `loom_backup/node/pipeline_builder.py`
- 功能: 声明式的节点流水线构建
- 价值: 简化复杂编排的定义
- 迁移位置: `loom/orchestration/pipeline.py`
- 工作量: 中等

**2. 节点基类增强** (P1)
- 源文件: `loom_backup/node/base.py`
- 功能: 节点的通用功能（生命周期、状态管理等）
- 价值: 统一节点行为
- 迁移位置: `loom/orchestration/node_base.py`
- 工作量: 中等

**3. Agent节点实现** (P0)
- 源文件: `loom_backup/node/agent.py`
- 功能: 完整的Agent节点实现
- 价值: 框架的核心节点类型
- 迁移位置: `loom/orchestration/agent_node.py`
- 工作量: 大（需要适配新架构）

**4. Tool节点实现** (P0)
- 源文件: `loom_backup/node/tool.py`
- 功能: 工具节点封装
- 价值: 将工具包装为节点
- 迁移位置: `loom/orchestration/tool_node.py`
- 工作量: 中等

---

### A6: 四范式工作公理 (paradigms/)

#### 已迁移
- ✅ `Reflection` - 反思范式（基础）
- ✅ `ToolUse` - 工具使用范式（基础）
- ✅ `Planning` - 规划范式（基础）
- ✅ `MultiAgent` - 多智能体范式（基础）

#### 可迁移能力

**1. 置信度评估器** (P1) - Reflection范式
- 源文件: `loom_backup/cognition/confidence.py`
- 功能: 评估输出质量，支持迭代改进
- 价值: Reflection范式的核心能力
- 迁移位置: `loom/paradigms/reflection/confidence.py`
- 工作量: 小

**2. 特征提取器** (P2) - Reflection范式
- 源文件: `loom_backup/cognition/features.py`
- 功能: 提取查询和响应的特征
- 价值: 支持置信度评估
- 迁移位置: `loom/paradigms/reflection/features.py`
- 工作量: 小

**3. 工具执行引擎** (P0) - ToolUse范式
- 源文件: `loom_backup/kernel/core/executor.py`
- 功能: 并行工具执行、缓存、重试
- 价值: ToolUse范式的核心引擎
- 迁移位置: `loom/paradigms/tool_use/executor.py`
- 工作量: 中等

**4. 工具注册表** (P0) - ToolUse范式
- 源文件: `loom_backup/tools/registry.py`
- 功能: 工具的注册和管理
- 价值: 工具系统的基础
- 迁移位置: `loom/paradigms/tool_use/registry.py`
- 工作量: 小

**5. 工具转换器** (P1) - ToolUse范式
- 源文件: `loom_backup/tools/converters.py`
- 功能: 不同工具格式的转换（MCP、OpenAI等）
- 价值: 与外部工具生态互操作
- 迁移位置: `loom/paradigms/tool_use/converters.py`
- 工作量: 中等

**6. 工作模式库** (P1) - Planning范式
- 源文件: `loom_backup/patterns/*.py`
  - `analytical.py` - 分析模式
  - `collaborative.py` - 协作模式
  - `creative.py` - 创意模式
  - `execution.py` - 执行模式
  - `iterative.py` - 迭代模式
- 功能: 预定义的工作模式
- 价值: 提供最佳实践模板
- 迁移位置: `loom/paradigms/planning/patterns/`
- 工作量: 中等

---

### Runtime支持 (runtime/)

#### 已迁移
- ✅ `Dispatcher` - 事件调度器
- ✅ `Interceptor` - 拦截器基类

#### 可迁移能力

**1. 完整的拦截器系统** (P0)
- 源文件: `loom_backup/kernel/control/*.py`
  - `budget.py` - 预算控制
  - `depth.py` - 深度限制
  - `timeout.py` - 超时控制
  - `hitl.py` - 人工介入
  - `studio.py` - Studio集成
  - `adaptive.py` - 自适应控制（SDE噪声控制）
- 功能: 完整的控制机制
- 价值: 框架的安全和控制能力
- 迁移位置: `loom/runtime/interceptors/`
- 工作量: 中等

**2. 状态管理** (P1)
- 源文件: `loom_backup/kernel/core/state.py`
- 功能: 节点状态的持久化和恢复
- 价值: 支持长时间运行和故障恢复
- 迁移位置: `loom/runtime/state.py`
- 工作量: 中等

**3. 认知状态** (P2)
- 源文件: `loom_backup/kernel/core/cognitive_state.py`
- 功能: Agent的认知状态管理
- 价值: 支持复杂的认知过程
- 迁移位置: `loom/runtime/cognitive_state.py`
- 工作量: 中等

**4. 优化系统** (P2)
- 源文件: `loom_backup/kernel/optimization/*.py`
  - `landscape_optimizer.py` - 景观优化
  - `pruning_strategies.py` - 剪枝策略
  - `structure_controller.py` - 结构控制
  - `structure_evolution.py` - 结构演化
  - `structure_health.py` - 结构健康
- 功能: 自动优化分形结构
- 价值: 提升系统性能
- 迁移位置: `loom/runtime/optimization/`
- 工作量: 大（可选功能）

---

## 小结（第二部分）

第二部分分析了A5、A6和Runtime相关的能力。关键发现：

1. **工具执行引擎是P0** - 必须迁移，是ToolUse范式的核心
2. **拦截器系统非常完整** - 6个拦截器提供了全面的控制能力
3. **工作模式库很有价值** - 提供了最佳实践模板
4. **优化系统可以延后** - 属于高级功能，不影响基础运行

下一部分将分析Providers和配置系统。

---

## 第三部分：Providers和配置系统

### Providers (providers/)

#### 已迁移
- ✅ `LLMProvider` - LLM提供者基类
- ✅ `VectorStoreProvider` - 向量存储提供者基类

#### 可迁移能力

**1. 完整的LLM提供者生态** (P0)
- 源文件: `loom_backup/llm/providers/*.py` (17个文件)
  - `anthropic.py` - Anthropic Claude
  - `openai.py` - OpenAI GPT
  - `deepseek.py` - DeepSeek
  - `gemini.py` - Google Gemini
  - `qwen.py` - 阿里通义千问
  - `zhipu.py` - 智谱AI
  - `kimi.py` - Moonshot Kimi
  - `doubao.py` - 字节豆包
  - `ollama.py` - Ollama本地模型
  - `vllm.py` - vLLM推理引擎
  - `gpustack.py` - GPUStack
  - `openai_compatible.py` - OpenAI兼容接口
  - `custom.py` - 自定义提供者
  - `mock.py` - 测试用Mock
- 功能: 支持主流LLM提供者
- 价值: 框架的核心能力，用户可以选择任意LLM
- 迁移位置: `loom/providers/llm/`
- 工作量: 大（但每个提供者相对独立）

**2. 重试处理器** (P1)
- 源文件: `loom_backup/llm/providers/retry_handler.py`
- 功能: 统一的重试和错误处理
- 价值: 提升系统稳定性
- 迁移位置: `loom/providers/llm/retry_handler.py`
- 工作量: 小

**3. 基础处理器** (P1)
- 源文件: `loom_backup/llm/providers/base_handler.py`
- 功能: 提供者的通用功能
- 价值: 简化提供者实现
- 迁移位置: `loom/providers/llm/base_handler.py`
- 工作量: 小

**4. LLM接口定义** (P0)
- 源文件: `loom_backup/llm/interface.py`
- 功能: 标准化的LLM接口（LLMResponse, StreamChunk）
- 价值: 统一不同提供者的接口
- 迁移位置: `loom/providers/llm/interface.py`
- 工作量: 小

---

### 配置系统 (config/)

#### 当前状态
- ❌ 新架构中尚未实现配置系统

#### 可迁移能力

**1. 配置模型** (P1)
- 源文件: `loom_backup/config/models.py`
- 功能: Pydantic配置模型（AgentConfig, CrewConfig, LoomConfig）
- 价值: 类型安全的配置
- 迁移位置: `loom/api/config.py`
- 工作量: 小

**2. LLM配置** (P1)
- 源文件: `loom_backup/config/llm.py`
- 功能: LLM相关配置
- 价值: 统一LLM配置管理
- 迁移位置: `loom/providers/llm/config.py`
- 工作量: 小

**3. 记忆配置** (P1)
- 源文件: `loom_backup/config/memory.py`
- 功能: 记忆系统配置
- 价值: 灵活的记忆配置
- 迁移位置: `loom/memory/config.py`
- 工作量: 小

**4. 分形配置** (P1)
- 源文件: `loom_backup/config/fractal.py`
- 功能: 分形编排配置
- 价值: 控制分形行为
- 迁移位置: `loom/fractal/config.py`
- 工作量: 小

**5. 执行配置** (P1)
- 源文件: `loom_backup/config/execution.py`
- 功能: 工具执行配置
- 价值: 控制并行执行等行为
- 迁移位置: `loom/paradigms/tool_use/config.py`
- 工作量: 小

**6. 拦截器配置** (P1)
- 源文件: `loom_backup/config/interceptor.py`
- 功能: 拦截器配置
- 价值: 统一拦截器配置
- 迁移位置: `loom/runtime/config.py`
- 工作量: 小

**7. 认知配置** (P2)
- 源文件: `loom_backup/config/cognitive.py`
- 功能: 认知相关配置
- 价值: 控制认知行为
- 迁移位置: `loom/runtime/cognitive_config.py`
- 工作量: 小

**8. 优化配置** (P2)
- 源文件: `loom_backup/config/optimization.py`
- 功能: 优化系统配置
- 价值: 控制优化行为
- 迁移位置: `loom/runtime/optimization/config.py`
- 工作量: 小

**9. 工具配置** (P1)
- 源文件: `loom_backup/config/tool.py`
- 功能: 工具相关配置
- 价值: 统一工具配置
- 迁移位置: `loom/paradigms/tool_use/tool_config.py`
- 工作量: 小

---

## 小结（第三部分）

第三部分分析了Providers和配置系统。关键发现：

1. **LLM提供者生态非常丰富** - 17个提供者，覆盖主流LLM
2. **配置系统很完整** - 9个配置模块，覆盖所有方面
3. **所有配置都是P1-P2** - 不影响核心功能，但对用户体验很重要
4. **迁移工作量相对较小** - 大部分是独立模块，可以逐个迁移

---

## 第四部分：其他能力和工具

### API和构建器 (api/)

#### 已迁移
- ✅ `Builder` - 基础构建器

#### 可迁移能力

**1. 完整的Loom API** (P0)
- 源文件: `loom_backup/api/loom.py`
- 功能: 统一的对外API，简化框架使用
- 价值: 用户体验的核心
- 迁移位置: `loom/api/loom.py`
- 工作量: 大（需要适配新架构）

**2. 高级构建器** (P1)
- 源文件: `loom_backup/builder.py`
- 功能: 声明式的系统构建
- 价值: 简化复杂系统的创建
- 迁移位置: `loom/api/builder.py`
- 工作量: 中等

---

### 工具函数 (utils/)

#### 可迁移能力

**1. 格式化工具** (P2)
- 源文件: `loom_backup/utils/formatting.py`
- 功能: 输出格式化和美化
- 价值: 改善用户体验
- 迁移位置: `loom/utils/formatting.py`
- 工作量: 小

**2. 规范化工具** (P2)
- 源文件: `loom_backup/utils/normalization.py`
- 功能: 数据规范化和清理
- 价值: 保证数据质量
- 迁移位置: `loom/utils/normalization.py`
- 工作量: 小

---

### 投影系统 (projection/)

#### 可迁移能力

**1. 投影配置** (P2)
- 源文件: `loom_backup/projection/profiles.py`
- 功能: 记忆投影配置文件
- 价值: 灵活的记忆视图
- 迁移位置: `loom/memory/projection.py`
- 工作量: 小

---

## 小结（第四部分）

第四部分分析了其他能力和工具。关键发现：

1. **Loom API是P0** - 必须迁移，是用户使用框架的入口
2. **工具函数优先级较低** - 不影响核心功能
3. **投影系统可以整合到记忆模块** - 作为记忆系统的一部分

