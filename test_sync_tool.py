"""
同步方式测试工具定义
"""
import os
from loom.protocol.mcp import MCPToolDefinition

os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

print("=" * 60)
print("测试工具定义序列化")
print("=" * 60)

# 创建工具定义
tool_def = MCPToolDefinition(
    name="add",
    description="Add two numbers",
    inputSchema={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"]
    }
)

print("\n1. 使用 model_dump() (默认):")
dump_default = tool_def.model_dump()
print(f"   {dump_default}")
print(f"   参数字段名: {list(dump_default.keys())}")

print("\n2. 使用 model_dump(by_alias=True):")
dump_alias = tool_def.model_dump(by_alias=True)
print(f"   {dump_alias}")
print(f"   参数字段名: {list(dump_alias.keys())}")

print("\n3. 对比:")
if 'input_schema' in dump_default:
    print("   ✅ 默认输出包含 'input_schema' (snake_case)")
if 'inputSchema' in dump_alias:
    print("   ✅ by_alias输出包含 'inputSchema' (camelCase)")

print("\n4. OpenAI期望的格式:")
print("   OpenAI provider查找: tool.get('inputSchema', tool.get('parameters', {}))")
print(f"   默认方式能找到参数: {'inputSchema' in dump_default or 'parameters' in dump_default}")
print(f"   by_alias方式能找到参数: {'inputSchema' in dump_alias or 'parameters' in dump_alias}")

print("\n✅ 测试完成")
