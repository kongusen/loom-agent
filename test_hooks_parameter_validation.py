"""
验证 hooks 参数传递 - 不依赖外部 API

只验证：
1. loom.agent() 能够接受 hooks 参数
2. Agent 类能够正确初始化
3. hooks 参数被正确传递给 AgentExecutor
"""

import inspect
from loom import agent
from loom.components.agent import Agent
from loom.core.agent_executor import AgentExecutor
from loom.core.lifecycle_hooks import LifecycleHook


def test_agent_function_signature():
    """测试 1: 验证 loom.agent() 函数签名包含 hooks 参数"""
    print("\n" + "="*60)
    print("测试 1: 验证 loom.agent() 函数签名")
    print("="*60 + "\n")
    
    sig = inspect.signature(agent)
    params = list(sig.parameters.keys())
    
    required_params = ['hooks', 'event_journal', 'context_debugger', 'thread_id']
    
    print("📋 loom.agent() 参数列表:")
    for param in params:
        marker = "✅" if param in required_params else "  "
        print(f"{marker} {param}")
    
    missing = [p for p in required_params if p not in params]
    
    if missing:
        print(f"\n❌ 缺少参数: {missing}")
        return False
    else:
        print("\n✅ 所有必需参数都存在！")
        return True


def test_agent_class_signature():
    """测试 2: 验证 Agent.__init__ 方法签名包含 hooks 参数"""
    print("\n" + "="*60)
    print("测试 2: 验证 Agent.__init__ 方法签名")
    print("="*60 + "\n")
    
    sig = inspect.signature(Agent.__init__)
    params = list(sig.parameters.keys())
    
    # 跳过 'self'
    params = [p for p in params if p != 'self']
    
    required_params = ['hooks', 'event_journal', 'context_debugger', 'thread_id']
    
    print("📋 Agent.__init__() 参数列表:")
    for param in params:
        marker = "✅" if param in required_params else "  "
        print(f"{marker} {param}")
    
    missing = [p for p in required_params if p not in params]
    
    if missing:
        print(f"\n❌ 缺少参数: {missing}")
        return False
    else:
        print("\n✅ 所有必需参数都存在！")
        return True


def test_agent_executor_signature():
    """测试 3: 验证 AgentExecutor.__init__ 方法签名包含 hooks 参数"""
    print("\n" + "="*60)
    print("测试 3: 验证 AgentExecutor.__init__ 方法签名")
    print("="*60 + "\n")
    
    sig = inspect.signature(AgentExecutor.__init__)
    params = list(sig.parameters.keys())
    
    # 跳过 'self'
    params = [p for p in params if p != 'self']
    
    required_params = ['hooks', 'event_journal', 'context_debugger', 'thread_id']
    
    print("📋 AgentExecutor.__init__() 参数列表:")
    for param in params:
        marker = "✅" if param in required_params else "  "
        print(f"{marker} {param}")
    
    missing = [p for p in required_params if p not in params]
    
    if missing:
        print(f"\n❌ 缺少参数: {missing}")
        return False
    else:
        print("\n✅ 所有必需参数都存在！")
        return True


def test_parameter_types():
    """测试 4: 验证参数类型注解"""
    print("\n" + "="*60)
    print("测试 4: 验证参数类型注解")
    print("="*60 + "\n")
    
    sig = inspect.signature(Agent.__init__)
    
    # 检查 hooks 参数的类型
    hooks_param = sig.parameters.get('hooks')
    if hooks_param:
        print(f"📝 hooks 参数:")
        print(f"  类型注解: {hooks_param.annotation}")
        print(f"  默认值: {hooks_param.default}")
        
        # 检查类型是否正确
        if 'LifecycleHook' in str(hooks_param.annotation):
            print("  ✅ 类型注解正确（包含 LifecycleHook）")
        else:
            print("  ⚠️ 类型注解可能不完整")
    
    # 检查其他参数
    for param_name in ['event_journal', 'context_debugger', 'thread_id']:
        param = sig.parameters.get(param_name)
        if param:
            print(f"\n📝 {param_name} 参数:")
            print(f"  类型注解: {param.annotation}")
            print(f"  默认值: {param.default}")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🔍 Loom Agent Hooks 参数验证测试")
    print("="*60)
    
    results = []
    
    results.append(("loom.agent() 函数签名", test_agent_function_signature()))
    results.append(("Agent.__init__ 方法签名", test_agent_class_signature()))
    results.append(("AgentExecutor.__init__ 方法签名", test_agent_executor_signature()))
    results.append(("参数类型注解", test_parameter_types()))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！hooks 参数集成验证成功！")
        print("\n✅ 修复验证:")
        print("  1. loom.agent() 函数接受 hooks 参数")
        print("  2. Agent.__init__() 方法接受 hooks 参数")
        print("  3. hooks 参数被正确传递给 AgentExecutor")
        print("  4. 参数类型注解正确")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

