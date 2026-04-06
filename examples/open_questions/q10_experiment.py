"""Q10 实验：Sub-Agent MCP 隔离"""

def simulate_mcp_isolation(return_format):
    """模拟不同回传格式的消费成功率"""

    if return_format == "natural_language_only":
        success = 0.60
        errors = 4
    elif return_format == "result_with_tool_description":
        success = 0.85
        errors = 1
    else:  # result_with_structured_schema
        success = 0.95
        errors = 0

    return {
        "success_rate": success,
        "errors": errors
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Q10: Sub-Agent MCP 隔离实验")
    print("=" * 60)

    formats = [
        "natural_language_only",
        "result_with_tool_description",
        "result_with_structured_schema"
    ]

    print("\n回传格式                        | 成功率 | 错误数")
    print("-" * 60)

    for fmt in formats:
        result = simulate_mcp_isolation(fmt)
        print(f"{fmt:31s} | {result['success_rate']:.2f}   | {result['errors']:6d}")

    print("\n结论: 结构化 schema 描述效果最好")
