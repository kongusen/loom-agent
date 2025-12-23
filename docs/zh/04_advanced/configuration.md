# 配置与控制 (Configuration & Controls)

Loom 提供了多层配置，从全局的应用级控制到细粒度的节点级设置。

## `LoomApp` 配置

在初始化 `LoomApp` 时，你可以传递 `control_config` 来设置全局拦截器。

```python
config = {
    "budget": {"max_tokens": 100000},  # 令牌预算
    "depth": {"max_depth": 10},        # 最大递归深度
    "hitl": ["DELETE", "PURCHASE"]     # 触发"人机回环/人工确认"的敏感词
}

app = LoomApp(control_config=config)
```

### 1. 预算拦截器 (BudgetInterceptor)
- **目的**: 防止意外的 token 消耗激增。
- **机制**: 跟踪所有事件的元数据，如果总消耗超过阈值，阻止新的 request。

### 2. 深度拦截器 (DepthInterceptor)
- **目的**: 防止无限递归调用（例如 Agent A 调 Agent B 调用 Agent A）。
- **机制**: 检查 `traceparent` 或事件链的长度。

### 3. HITL 拦截器 (Human-in-the-Loop)
- **目的**: 对敏感操作进行人工审核。
- **机制**: 如果 CloudEvent 的内容包含敏感词，拦截事件并挂起，直到人工批准（目前通过报错或日志提示实现，未来支持 UI 交互）。
