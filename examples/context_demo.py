"""维度一：上下文控制演示"""

from loom.context import ContextManager
from loom.types import Message


def demo_context_control():
    """演示上下文控制功能"""
    
    # 创建上下文管理器
    ctx = ContextManager(max_tokens=1000)
    ctx.current_goal = "实现一个简单的 Agent"
    
    # 添加系统消息（永不压缩）
    ctx.partitions.system.append(
        Message(role="system", content="你是一个 AI Agent")
    )
    
    # 添加历史消息
    for i in range(20):
        ctx.partitions.history.append(
            Message(role="user", content=f"消息 {i}" * 100)
        )
    
    print(f"初始 ρ: {ctx.rho:.2f}")
    
    # 检查是否需要压缩
    strategy = ctx.should_compress()
    if strategy:
        print(f"触发压缩策略: {strategy}")
        ctx.compress(strategy)
        print(f"压缩后 ρ: {ctx.rho:.2f}")
    
    # 检查是否需要续写
    if ctx.should_renew():
        print("触发 Context Renewal")
        ctx.renew()
        print(f"续写后 ρ: {ctx.rho:.2f}")


if __name__ == "__main__":
    demo_context_control()
