# EventBus 问题清单与优化思路

本文用于后续实施与检查，聚焦于当前 EventBus 机制的工程性缺陷与系统性风险，并给出分阶段优化路径与验收清单。

---

## 1. 问题清单（按严重度，含原因与修复提示）

### P0（立刻影响正确性/一致性）

- 任务状态被强制覆盖  
  原因：`publish()` 入口强制写入 `RUNNING`，成功后又覆盖为 `COMPLETED`。  
  影响：Task 语义失真，历史不可依赖。  
  修复提示：仅在“队列接收/调度成功”时写 `RUNNING`；完成状态必须来自 handler 返回值。

- 无 handler 即判失败  
  原因：无 handler 分支直接设置 `FAILED`。  
  影响：观测事件被误标失败，历史污染。  
  修复提示：引入“事件型 Task”路径（无 handler 视为 `COMPLETED`），或将“订阅”与“处理”逻辑解耦。

- 只执行第一个 handler  
  原因：`handlers[0]` 硬编码。  
  影响：观察者和次级处理器永远不被触发。  
  修复提示：执行 handler 列表（串行或并行），区分“处理器”与“观察者”执行策略。

- 分布式路径无请求-响应闭环  
  原因：`publish()` 只发不收，没有 response topic 与 correlation。  
  影响：分布式 `wait_result=True` 语义无效。  
  修复提示：加入 `correlation_id` / `reply_to` 并订阅响应通道。

- fire-and-forget 静默失败  
  原因：异常被 suppress 且没有后置写回。  
  影响：静默失败、监控失效。  
  修复提示：捕获异常并发布 `FAILED` 事件，或写入日志/告警。

### P1（可观测性/可靠性显著下降）

- 通配订阅不可用  
  原因：EventBus 仅支持精确匹配。  
  影响：`stream_all_events()` 无效。  
  修复提示：支持 glob/regex 或维护独立“pattern 订阅表”。

- 订阅泄漏与背压缺失  
  原因：没有 unsubscribe；队列无上限。  
  影响：内存膨胀、慢消费者拖垮系统。  
  修复提示：断开时注销 handler；队列加上限和丢弃策略。

- 历史不是不可变快照  
  原因：存储可变对象引用。  
  影响：历史可被后续修改破坏。  
  修复提示：持久化 `task.to_dict()` 或深拷贝快照。

- query_by_target 去重策略丢事件  
  原因：按 `task_id` 去重。  
  影响：多阶段消息被吞。  
  修复提示：改用事件级唯一 ID 或允许同 task_id 多条记录。

- TTL 与时区潜在崩溃  
  原因：naive 与 aware datetime 混用。  
  影响：TTL 查询可能崩溃。  
  修复提示：统一 UTC aware 时间戳，或在 Task 初始化时强制时区。

- 传输层异常被吞  
  原因：`return_exceptions=True` 且无日志。  
  影响：失败不可见。  
  修复提示：收集异常并发出 error 事件或日志告警。

### P2（可维护性/一致性风险）

- `updated_at` 不更新  
  原因：状态写入未同步更新时间。  
  影响：排序和追踪错误。  
  修复提示：每次状态变更更新 `updated_at`。

- 文档与实现偏差  
  原因：文档未与代码同步。  
  影响：集成方踩坑。  
  修复提示：以实现为准更新文档或补实现缺失 API。

- 事件历史被高频思考挤爆  
  原因：FIFO 无优先级区分。  
  影响：关键事件被驱逐。  
  修复提示：分层存储或按优先级/类型配额裁剪。

---

## 2. 整体优化思路（分阶段）

### 阶段 A（修复语义与可观测性，1-2 周）

- 明确“任务处理”与“事件观测”双通道：  
  新增订阅 API（真正的 pub-sub），处理器与观察者分离。  
- 修复状态流转：  
  EventBus 不强改 handler 返回状态；保存 Task 快照；`updated_at` 自动更新。  
- fire-and-forget 的完成回写：  
  异步执行结束后补写 `COMPLETED/FAILED` 事件（至少落到历史）。  
- 让 `node.*` 等通配订阅生效（glob/regex）。  
- 记录并暴露异常：  
  失败必须转成 error 事件或日志记录，禁止静默失败。

### 阶段 B（分布式闭环，2-4 周）

- 加入 correlation_id / reply_to 机制，构建请求-响应通道。  
- 支持 `wait_result` 的真实等待语义（含超时）。  
- 明确分布式消息结构（可选兼容 CloudEvents）。

### 阶段 C（可持续性与性能，持续）

- 事件历史持久化/分层：  
  短期：优先级裁剪；长期：落库或外部事件存储。  
- 订阅背压与断线清理：  
  队列上限、慢消费者丢弃策略、自动注销与清理。
- 文档与测试对齐：  
  以功能为准校正文档，并补齐关键测试用例。

---

## 3. 验收/检查清单（实施完成后的验证）

### 语义一致性

- [ ] handler 返回 `FAILED/CANCELLED` 时，EventBus 不覆盖状态  
- [ ] 观测事件无 handler 时不会被标记为 `FAILED`
- [ ] fire-and-forget 任务最终会记录完成/失败状态

### 订阅与观测

- [ ] `node.*` 等通配订阅可收到事件  
- [ ] 多 handler/多订阅者均可被触发  
- [ ] 订阅断开后 handler 被清理

### 分布式能力

- [ ] `wait_result=True` 能在分布式模式下拿到结果或超时  
- [ ] correlation_id 能关联请求-响应  
- [ ] transport 异常可观测

### 历史与索引

- [ ] 历史记录为不可变快照  
- [ ] `updated_at` 随状态变更更新  
- [ ] TTL 过滤不会触发时区异常  
- [ ] query_by_target 不丢多阶段事件

### 文档与测试

- [ ] 文档与实际 API 对齐  
- [ ] 新增测试覆盖：通配订阅、多 handler、分布式请求-响应、状态流转、TTL

---

## 4. 关键文件索引（便于实施定位）

- `loom/events/event_bus.py`  
- `loom/events/stream_converter.py`  
- `loom/events/transport.py`  
- `loom/events/memory_transport.py`  
- `loom/protocol/task.py`  
- `loom/orchestration/base_node.py`  
- `docs/framework/event-bus.md`  
- `wiki/Event-Bus.md`
