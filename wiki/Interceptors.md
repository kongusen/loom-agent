# Interceptors

拦截器链（InterceptorChain）是中间件管道，在 LLM 调用前对消息进行变换、注入上下文或添加约束。

## 定义拦截器

实现 `intercept(ctx, nxt)` 方法，调用 `await nxt()` 传递到下一个拦截器：

```python
from loom import InterceptorContext
from loom.types import SystemMessage

class ExpertiseInterceptor:
    """注入领域专家身份。"""
    name = "expertise"

    async def intercept(self, ctx: InterceptorContext, nxt):
        ctx.messages.insert(0, SystemMessage(
            content="你是资深 Python 架构师，回答要包含代码示例。"
        ))
        await nxt()


class GuardrailInterceptor:
    """添加输出约束。"""
    name = "guardrail"

    async def intercept(self, ctx: InterceptorContext, nxt):
        ctx.messages.insert(0, SystemMessage(
            content="回答限制在3句话以内。"
        ))
        await nxt()
```

## 组装拦截器链

```python
from loom import Agent, AgentConfig, InterceptorChain

chain = InterceptorChain()
chain.use(ExpertiseInterceptor())
chain.use(GuardrailInterceptor())

agent = Agent(
    provider=provider,
    config=AgentConfig(max_steps=2),
    interceptors=chain,
)
```

## 效果对比

无拦截器 vs 有拦截器的同一问题：

```python
# 无拦截器 — 通用回答
agent1 = Agent(provider=provider, config=AgentConfig(max_steps=2))
r1 = await agent1.run("如何实现单例模式？")
# → 长篇通用介绍

# 有拦截器 — 专家级精简回答
agent2 = Agent(provider=provider, interceptors=chain)
r2 = await agent2.run("如何实现单例模式？")
# → 3句话 + Python 代码示例
```

## API 参考

```python
chain = InterceptorChain()
chain.use(interceptor)  # 添加拦截器（按顺序执行）

# InterceptorContext
@dataclass
class InterceptorContext:
    messages: list[Message]  # 可修改的消息列表
    metadata: dict           # 元数据字典
```

> 完整示例：[`examples/demo/04_interceptors.py`](../examples/demo/04_interceptors.py)
