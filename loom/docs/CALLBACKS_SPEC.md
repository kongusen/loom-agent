# Loom Callbacks & Events Specification

本文件定义 Loom Agent 执行过程中对外回调（Callbacks）与流式事件（StreamEvent）的统一规范，便于接入日志、指标、可观测与外部控制系统。

## 设计目标

- 稳定且精简：事件种类有限、语义清晰、字段稳定。
- 可拓展：允许新增事件与字段，但不改变已发布字段含义。
- 正交于流式输出：回调与 `StreamEvent` 并行存在，可独立消费。

## 快速上手

- 定义回调：

```python
from loom.callbacks.base import BaseCallback

class LoggingCallback(BaseCallback):
    async def on_event(self, event_type: str, payload: dict) -> None:
        # payload 已包含标准字段: ts/type/source/iteration (部分事件可能缺省 iteration)
        print(f"[{event_type}] {payload}")
```

- 注入 Agent：

```python
import loom
cb = LoggingCallback()
agent = loom.agent(provider="openai", model="gpt-4o", callbacks=[cb])
```

- 与流式事件同时使用：

```python
async for ev in agent.astream("Tell me a joke"):
    if ev.type == "text_delta":
        ...
```

## 统一字段（payload 通用字段）

- `type: str` 事件名（与 on_event 的 event_type 一致）
- `ts: float` 事件时间戳（秒）
- `source: str` 发出来源：`execute` 或 `stream`
- `iteration: int` 当前迭代次数（在可用时提供；部分事件缺省）

说明：除以上通用字段外，每个事件还会携带特定字段，见下文“事件目录”。

## 事件目录（Callbacks）

- request_start
  - 时机：收到用户输入后，开始一次执行（非流式与流式各触发一次）
  - 额外字段：
    - `input: str` 用户输入
  - 示例：
    ```json
    {"type":"request_start","ts":1710000000.0,"source":"execute","iteration":0,"input":"Explain RAG"}
    ```

- retrieval_complete
  - 时机：启用 RAG 时，检索完成后
  - 额外字段：
    - `doc_count: int` 检索返回文档数量
  - 示例：
    ```json
    {"type":"retrieval_complete","ts":1710000001.2,"source":"stream","doc_count":3}
    ```

- compression_applied
  - 时机：触发上下文压缩后（execute/stream 两路径均可能触发）
  - 额外字段：
    - `before_tokens: int` 压缩前 token 数
    - `after_tokens: int` 压缩后 token 数
  - 示例：
    ```json
    {"type":"compression_applied","ts":1710000002.3,"source":"execute","before_tokens":6200,"after_tokens":3900}
    ```

- tool_calls_start
  - 时机：LLM 决策需要调用工具时
  - 额外字段：
    - `tool_calls: [{"id": str, "name": str}]` 即将调用的工具列表（id 可能为空字符串）
  - 示例：
    ```json
    {"type":"tool_calls_start","ts":1710000003.4,"source":"stream","iteration":1,"tool_calls":[{"id":"call_0","name":"calculator"}]}
    ```

- tool_result
  - 时机：单个工具执行完成
  - 额外字段：
    - `tool_call_id: str` 工具调用 id（与 LLM 返回关联）
    - `content: str` 工具返回（已序列化为字符串）
  - 示例：
    ```json
    {"type":"tool_result","ts":1710000003.9,"source":"execute","iteration":1,"tool_call_id":"call_0","content":"56"}
    ```

- agent_finish
  - 时机：Agent 生成最终答复（无后续工具调用）
  - 额外字段：
    - `content: str` 最终文本答案
  - 示例：
    ```json
    {"type":"agent_finish","ts":1710000004.1,"source":"stream","content":"Here's a short answer..."}
    ```

- error
  - 时机：在 LLM 生成/流式/工具执行等阶段出错
  - 额外字段：
    - `stage: str` 错误阶段（如 `llm_generate`/`llm_stream`/`llm_generate_with_tools`/`tool_execute`）
    - `message: str` 错误信息（不含堆栈）
  - 示例：
    ```json
    {"type":"error","ts":1710000005.6,"source":"execute","iteration":0,"stage":"llm_generate","message":"Rate limit"}
    ```

## 流式事件（StreamEvent）对照

- `request_start`（仅流式路径）
- `retrieval_complete`（metadata 包含 `doc_count`）
- `compression_applied`
- `tool_calls_start`（携带 `tool_calls`）
- `tool_result`（流式工具结果）
- `text_delta`（文本增量）
- `agent_finish`（结束）

说明：`StreamEvent` 面向调用方消费响应流；`Callbacks` 面向系统观测与侧写。两者事件集高度重合但不完全相同（例如 text_delta 默认不触发回调）。

## 最佳实践

- 指标与日志：
  - 使用回调记录关键阶段（request_start/agent_finish/error），结合 `MetricsCollector` 可获迭代次数、LLM 调用、工具调用、错误数等指标摘要。
- 链路追踪：
  - 给每次请求分配 request_id（可在 `system_instructions` 或自定义上下文里传递），在回调里注入并记录。
- 错误处理：
  - 回调异常不会中断 Agent 执行（best‑effort）；错误事件会包含 stage，便于快速定位。

## 稳定性约定

- 通用字段 `type/ts/source/iteration` 与各事件的特定字段将保持向后兼容。
- 可能新增事件或新增字段，但不会改变既有字段含义。

---

如需更多示例，参见：
- `loom/docs/QUICKSTART.md`
- `examples/` 目录下的一行构建与工具装饰器示例

