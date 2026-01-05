# Loom 执行引擎 (Execution Engine)

> **核心机制** - 探索 ToolExecutor 如何高效、并行、安全地执行工具调用。

## ToolExecutor 架构

`ToolExecutor` 是负责实际执行 Agent 指令的引擎。它不仅仅是简单地调用函数，而是提供了一整套企业级的执行管理机制。

### 核心功能
1. **工具注册与发现**：自动扫描和注册工具。
2. **并行执行调度**：智能分析工具依赖，实现最大化并行。
3. **结果缓存**：减少重复的外部 API 调用。
4. **错误恢复**：自动处理瞬态故障。
5. **安全沙箱**：控制工具的执行权限（计划中）。

---

## 智能并行执行 (Parallel Execution)

Loom 采用基于**读写屏障 (Read-Write Barrier)** 的调度策略来解决并发安全问题。

### 调度逻辑
执行引擎在接收到一组并行工具调用请求时，会按照以下规则分组：

1. **类型分类**：
    - `Read` (无副作用)：如 `search_web`, `read_file`, `get_weather`。
    - `Write` (有副作用)：如 `write_file`, `send_email`, `execute_code`。
    - 工具类型通过正则模式匹配或显式标注来确定。

2. **屏障分组**：
    - 连续的 `Read` 操作被归为一组，**并行执行** (Asyncio.gather)。
    - 每一个 `Write` 操作都是一个独立的屏障，必须**顺序执行**。

### 示例
假设 Agent 请求执行以下指令：
`[搜天气, 读文件 A, 写文件 B, 搜结果, 发邮件]`

**执行顺序**：
1. **Group 1 (Parallel)**: `搜天气` 和 `读文件 A` 同时开始，等待两者全部完成。
2. **Barrier**: 等待 Group 1 完成。
3. **Group 2 (Sequential)**: `写文件 B`。
4. **Barrier**: 等待 Group 2 完成。
5. **Group 3 (Parallel)**: `搜结果`。
6. **Barrier**: 等待 Group 3 完成。
7. **Group 4 (Sequential)**: `发邮件`。

---

## 性能优化机制

### 1. 结果缓存 (Result Caching)
针对幂等性工具（主要是 `Read` 类），Loom 内置了缓存层。

- **Key生成**：`hash(tool_name + sorted(args))`
- **TTL**：默认 5 分钟 (300秒)。
- **命中率**：在测试环境中达到了 50% 的命中率。
- **配置**：可针对特定工具配置不同的 TTL 或禁用缓存。

### 2. 自动重试 (Auto-Retry)
针对网络波动或瞬态错误，实现了智能重试机制。

- **策略**：指数退避 (Exponential Backoff)。
- **公式**：`wait_time = base * (2 ^ attempt)`
- **配置**：最大重试次数（默认 3 次）。

### 3. 调用去重 (Call De-duplication)
防止 Agent 因为幻觉或逻辑错误产生的重复调用。

- **逻辑**：在同一个执行批次 (Batch) 中，如果出现完全相同的工具调用（名称+参数相同），只保留一个执行。
- **效果**：在复杂测试用例中减少了 50% 的冗余调用，节省 Token 和时间。

---

## 错误处理与归一化

当工具执行失败时，Executor 不会简单地抛出异常导致 Agent 崩溃，而是返回格式化的错误信息。

- **标准化输出**：无论是 Timeout、NetworkError 还是 ValueError，都被封装为统一的 `ToolResult`。
- **修复提示**：错误信息中包含可操作的提示（例如"文件不存在，请检查路径"），引导 LLM 自我修正。

## 配置指南

```python
from loom.config import ExecutionConfig

config = ExecutionConfig(
    # 最大并发数
    max_workers=10,
    
    # 全局超时时间
    timeout=30,
    
    # 缓存配置
    enable_cache=True,
    cache_ttl=300,
    
    # 重试配置
    max_retries=3
)
```
