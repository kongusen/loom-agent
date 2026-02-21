"""04 — 拦截器：中间件管道在 LLM 调用前注入上下文、增强对话。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, InterceptorChain, InterceptorContext
from loom.types import SystemMessage


class ExpertiseInterceptor:
    """注入领域专家身份，增强 LLM 回答质量。"""

    name = "expertise"

    async def intercept(self, ctx: InterceptorContext, nxt):
        ctx.messages.insert(
            0, SystemMessage(content="你是资深 Python 架构师，回答要包含具体代码示例。")
        )
        await nxt()


class GuardrailInterceptor:
    """添加安全护栏，限制输出范围。"""

    name = "guardrail"

    async def intercept(self, ctx: InterceptorContext, nxt):
        ctx.messages.insert(0, SystemMessage(content="回答限制在3句话以内，使用中文。"))
        await nxt()


async def main():
    provider = create_provider()
    question = "如何实现单例模式？"

    # ── 1. 无拦截器 — 普通回答 ──
    print("[1] 无拦截器")
    agent1 = Agent(provider=provider, config=AgentConfig(max_steps=2))
    r1 = await agent1.run(question)
    print(f"  回复: {r1.content[:120]}...")

    # ── 2. 有拦截器 — 注入专家身份 + 护栏 ──
    print("\n[2] 拦截器增强 (专家身份 + 护栏)")
    chain = InterceptorChain()
    chain.use(ExpertiseInterceptor())
    chain.use(GuardrailInterceptor())

    agent2 = Agent(
        provider=provider,
        config=AgentConfig(max_steps=2),
        interceptors=chain,
    )
    r2 = await agent2.run(question)
    print(f"  回复: {r2.content[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
