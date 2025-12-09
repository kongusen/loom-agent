"""
钩子（Hooks）完整演示

展示 Loom Agent 框架中钩子的各种用法：
1. 内置钩子使用
2. 自定义钩子实现
3. 多个钩子组合
4. HITL（Human-in-the-Loop）
5. 高级用法
"""

import asyncio
from typing import Dict, Any, List, Optional
from loom import agent
from loom.core.lifecycle_hooks import (
    LifecycleHook,
    LoggingHook,
    MetricsHook,
    HITLHook,
    InterruptException,
    SkipToolException
)


# ========================================
# 示例 1: 内置钩子使用
# ========================================

async def example_builtin_hooks():
    """演示内置钩子的使用"""
    print("\n" + "="*60)
    print("示例 1: 内置钩子使用")
    print("="*60 + "\n")
    
    # 创建内置钩子
    logging_hook = LoggingHook(verbose=True)
    metrics_hook = MetricsHook()
    
    # 创建 Agent（注意：这里使用模拟 LLM，实际使用时替换为真实 API）
    # my_agent = agent(
    #     provider="openai",
    #     model="gpt-4o-mini",
    #     hooks=[logging_hook, metrics_hook]
    # )
    
    print("✅ 内置钩子创建成功")
    print("  - LoggingHook: 记录执行日志")
    print("  - MetricsHook: 收集执行指标")
    
    # 执行后可以获取指标
    # metrics = metrics_hook.get_metrics()
    # print(f"指标: {metrics}")


# ========================================
# 示例 2: 自定义分析钩子
# ========================================

class AnalyticsHook:
    """自定义分析钩子：收集详细的执行统计"""
    
    def __init__(self):
        self.stats = {
            "iterations": [],
            "llm_calls": 0,
            "tool_executions": {},
            "token_usage": []
        }
    
    async def before_iteration_start(self, frame):
        """迭代开始"""
        self.stats["iterations"].append({
            "depth": frame.depth,
            "frame_id": frame.frame_id
        })
        print(f"📊 [Analytics] 迭代 {frame.depth} 开始")
        return None
    
    async def before_llm_call(self, frame, messages):
        """LLM 调用前"""
        self.stats["llm_calls"] += 1
        print(f"📊 [Analytics] LLM 调用 #{self.stats['llm_calls']}")
        return None
    
    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        """上下文组装后"""
        tokens = context_metadata.get("total_tokens", 0)
        self.stats["token_usage"].append({
            "iteration": frame.depth,
            "tokens": tokens
        })
        return None
    
    async def after_tool_execution(self, frame, tool_result):
        """工具执行后"""
        tool_name = tool_result.get("tool_name", "unknown")
        self.stats["tool_executions"][tool_name] = \
            self.stats["tool_executions"].get(tool_name, 0) + 1
        return None
    
    def get_report(self) -> Dict[str, Any]:
        """获取分析报告"""
        total_tokens = sum(t["tokens"] for t in self.stats["token_usage"])
        return {
            "total_iterations": len(self.stats["iterations"]),
            "total_llm_calls": self.stats["llm_calls"],
            "total_tokens": total_tokens,
            "tool_usage": self.stats["tool_executions"],
            "avg_tokens_per_iteration": total_tokens / len(self.stats["token_usage"]) if self.stats["token_usage"] else 0
        }


async def example_custom_analytics():
    """演示自定义分析钩子"""
    print("\n" + "="*60)
    print("示例 2: 自定义分析钩子")
    print("="*60 + "\n")
    
    analytics = AnalyticsHook()
    
    print("✅ 自定义分析钩子创建成功")
    print("  功能：")
    print("  - 跟踪迭代次数")
    print("  - 统计 LLM 调用")
    print("  - 记录 token 使用")
    print("  - 统计工具使用情况")
    
    # 使用示例
    # my_agent = agent(
    #     provider="openai",
    #     model="gpt-4o-mini",
    #     hooks=[analytics]
    # )
    # await my_agent.run("你的任务")
    # report = analytics.get_report()
    # print(report)


# ========================================
# 示例 3: 权限控制钩子
# ========================================

class PermissionHook:
    """基于角色的权限控制钩子"""
    
    def __init__(self, user_role: str = "guest"):
        self.user_role = user_role
        self.permissions = {
            "admin": ["*"],  # 所有权限
            "user": ["read_file", "search", "write_file"],
            "guest": ["search", "read_file"]  # 只读权限
        }
    
    async def before_tool_execution(self, frame, tool_call):
        """工具执行前检查权限"""
        tool_name = tool_call.get("name", "")
        allowed_tools = self.permissions.get(self.user_role, [])
        
        # 检查权限
        if "*" not in allowed_tools and tool_name not in allowed_tools:
            print(f"🚫 [Permission] 角色 '{self.user_role}' 无权执行 '{tool_name}'")
            raise SkipToolException(f"Permission denied for {tool_name}")
        
        print(f"✅ [Permission] 允许执行: {tool_name}")
        return None


async def example_permission_control():
    """演示权限控制钩子"""
    print("\n" + "="*60)
    print("示例 3: 权限控制钩子")
    print("="*60 + "\n")
    
    # 不同角色的钩子
    admin_hook = PermissionHook(user_role="admin")
    user_hook = PermissionHook(user_role="user")
    guest_hook = PermissionHook(user_role="guest")
    
    print("✅ 权限控制钩子创建成功")
    print("  角色权限：")
    print("  - admin: 所有工具")
    print("  - user: read_file, search, write_file")
    print("  - guest: search, read_file (只读)")
    
    # 使用示例
    # guest_agent = agent(
    #     provider="openai",
    #     model="gpt-4o-mini",
    #     hooks=[guest_hook]
    # )


# ========================================
# 示例 4: HITL (Human-in-the-Loop) 钩子
# ========================================

class CustomHITLHook:
    """自定义 HITL 钩子：在执行危险操作前暂停"""
    
    def __init__(self, dangerous_tools: List[str]):
        self.dangerous_tools = dangerous_tools
    
    async def before_tool_execution(self, frame, tool_call):
        """工具执行前检查"""
        tool_name = tool_call.get("name", "")
        
        if tool_name in self.dangerous_tools:
            # 显示详细信息
            tool_args = tool_call.get("arguments", {})
            print(f"\n⚠️  [HITL] 检测到危险操作:")
            print(f"  工具: {tool_name}")
            print(f"  参数: {tool_args}")
            
            # 暂停执行，等待用户确认
            raise InterruptException(
                reason=f"需要确认执行危险工具: {tool_name}",
                requires_user_input=True,
                frame_id=frame.frame_id
            )
        
        return None


async def example_hitl():
    """演示 HITL 钩子"""
    print("\n" + "="*60)
    print("示例 4: HITL (Human-in-the-Loop) 钩子")
    print("="*60 + "\n")
    
    # 使用内置 HITLHook
    hitl_hook_builtin = HITLHook(
        dangerous_tools=["delete_file", "send_email", "execute_shell"],
        ask_user_callback=lambda msg: input(f"{msg} (y/n): ").lower() == "y"
    )
    
    # 或使用自定义 HITLHook
    hitl_hook_custom = CustomHITLHook(
        dangerous_tools=["delete_file", "send_email"]
    )
    
    print("✅ HITL 钩子创建成功")
    print("  功能：")
    print("  - 在执行危险工具前暂停")
    print("  - 等待用户确认")
    print("  - 支持自定义确认逻辑")
    
    # 使用示例
    # my_agent = agent(
    #     provider="openai",
    #     model="gpt-4o-mini",
    #     hooks=[hitl_hook_builtin],
    #     enable_persistence=True  # 建议启用持久化
    # )


# ========================================
# 示例 5: 消息修改钩子
# ========================================

class MessageModificationHook:
    """修改发送给 LLM 的消息"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt
    
    async def before_llm_call(self, frame, messages):
        """LLM 调用前修改消息"""
        # 检查是否已有系统消息
        has_system = any(msg.get("role") == "system" for msg in messages)
        
        if not has_system and self.system_prompt:
            # 添加系统提示
            messages.insert(0, {
                "role": "system",
                "content": self.system_prompt
            })
            print(f"📝 [MessageMod] 添加了系统提示")
            return messages
        
        return None


async def example_message_modification():
    """演示消息修改钩子"""
    print("\n" + "="*60)
    print("示例 5: 消息修改钩子")
    print("="*60 + "\n")
    
    message_hook = MessageModificationHook(
        system_prompt="你是一个专业的 Python 开发助手，擅长代码分析和问题解决。"
    )
    
    print("✅ 消息修改钩子创建成功")
    print("  功能：")
    print("  - 自动添加系统提示")
    print("  - 修改用户消息")
    print("  - 注入上下文信息")


# ========================================
# 示例 6: 结果验证和缓存钩子
# ========================================

class ResultValidationHook:
    """验证和缓存工具执行结果"""
    
    def __init__(self):
        self.cache = {}
        self.validation_errors = []
    
    async def after_tool_execution(self, frame, tool_result):
        """工具执行后验证结果"""
        tool_name = tool_result.get("tool_name", "")
        content = tool_result.get("content", "")
        is_error = tool_result.get("is_error", False)
        
        # 验证结果
        if is_error:
            print(f"⚠️  [Validation] 工具 {tool_name} 执行出错")
            self.validation_errors.append({
                "tool": tool_name,
                "error": content,
                "iteration": frame.depth
            })
        
        # 缓存结果
        cache_key = f"{tool_name}:{hash(str(content))}"
        self.cache[cache_key] = {
            "content": content,
            "timestamp": frame.created_at if hasattr(frame, 'created_at') else None
        }
        
        return None
    
    def get_validation_report(self):
        """获取验证报告"""
        return {
            "cached_results": len(self.cache),
            "validation_errors": len(self.validation_errors),
            "errors": self.validation_errors
        }


async def example_result_validation():
    """演示结果验证钩子"""
    print("\n" + "="*60)
    print("示例 6: 结果验证和缓存钩子")
    print("="*60 + "\n")
    
    validation_hook = ResultValidationHook()
    
    print("✅ 结果验证钩子创建成功")
    print("  功能：")
    print("  - 验证工具执行结果")
    print("  - 缓存结果避免重复执行")
    print("  - 记录验证错误")


# ========================================
# 示例 7: 多个钩子组合
# ========================================

async def example_multiple_hooks():
    """演示多个钩子组合使用"""
    print("\n" + "="*60)
    print("示例 7: 多个钩子组合")
    print("="*60 + "\n")
    
    # 创建多个钩子
    logging_hook = LoggingHook(verbose=False)
    metrics_hook = MetricsHook()
    analytics_hook = AnalyticsHook()
    permission_hook = PermissionHook(user_role="user")
    message_hook = MessageModificationHook(
        system_prompt="你是一个有帮助的 AI 助手。"
    )
    
    # 组合使用
    all_hooks = [
        logging_hook,      # 1. 日志记录
        metrics_hook,      # 2. 指标收集
        analytics_hook,    # 3. 详细分析
        permission_hook,   # 4. 权限控制
        message_hook       # 5. 消息修改
    ]
    
    print("✅ 多个钩子组合成功")
    print("  执行顺序：")
    for i, hook in enumerate(all_hooks, 1):
        print(f"  {i}. {hook.__class__.__name__}")
    
    print("\n  说明：")
    print("  - 钩子按列表顺序执行")
    print("  - 前一个钩子的返回值作为下一个钩子的输入")
    print("  - 可以修改数据并传递给下一个钩子")
    
    # 使用示例
    # my_agent = agent(
    #     provider="openai",
    #     model="gpt-4o-mini",
    #     hooks=all_hooks
    # )
    # 
    # result = await my_agent.run("你的任务")
    # 
    # # 获取各种统计
    # print("\n📊 指标:", metrics_hook.get_metrics())
    # print("📈 分析:", analytics_hook.get_report())


# ========================================
# 示例 8: 完整工作流
# ========================================

async def example_complete_workflow():
    """完整工作流示例"""
    print("\n" + "="*60)
    print("示例 8: 完整工作流")
    print("="*60 + "\n")
    
    # 创建所有钩子
    hooks = [
        LoggingHook(verbose=True),
        MetricsHook(),
        AnalyticsHook(),
        PermissionHook(user_role="user"),
        MessageModificationHook(
            system_prompt="你是一个专业的 Python 开发助手。"
        )
    ]
    
    print("✅ 完整工作流配置：")
    print("  1. 日志记录 - 跟踪执行过程")
    print("  2. 指标收集 - 收集基本指标")
    print("  3. 详细分析 - 深度分析执行数据")
    print("  4. 权限控制 - 确保安全执行")
    print("  5. 消息修改 - 优化提示词")
    
    print("\n💡 使用建议：")
    print("  - 开发环境：启用所有钩子进行调试")
    print("  - 生产环境：只启用必要的钩子（性能考虑）")
    print("  - 根据需求组合不同的钩子")
    
    # 实际使用代码（注释掉，需要真实 API）
    """
    my_agent = agent(
        provider="openai",
        model="gpt-4o-mini",
        hooks=hooks
    )
    
    # 执行任务
    result = await my_agent.run("你的任务")
    
    # 获取统计信息
    metrics = hooks[1].get_metrics()  # MetricsHook
    analytics = hooks[2].get_report()  # AnalyticsHook
    
    print(f"\n结果: {result}")
    print(f"\n指标: {metrics}")
    print(f"\n分析: {analytics}")
    """


# ========================================
# 主函数
# ========================================

async def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("Loom Agent 钩子（Hooks）完整演示")
    print("="*60)
    
    await example_builtin_hooks()
    await example_custom_analytics()
    await example_permission_control()
    await example_hitl()
    await example_message_modification()
    await example_result_validation()
    await example_multiple_hooks()
    await example_complete_workflow()
    
    print("\n" + "="*60)
    print("✅ 所有示例演示完成！")
    print("="*60)
    print("\n📚 更多信息请查看:")
    print("  - docs/HOOKS_USAGE_GUIDE.md - 详细使用指南")
    print("  - docs/API_REFERENCE_v0_0_8.md - API 参考")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

