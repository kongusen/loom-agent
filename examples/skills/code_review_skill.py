"""
代码审查 Skill

用于COMPILATION示例：将此skill编译为工具
"""

SKILL_METADATA = {
    "name": "code_review",
    "version": "1.0.0",
    "description": "代码审查工具，检查代码质量、安全性和最佳实践",
    "activation_forms": ["COMPILATION"],
}

SKILL_PROMPT = """你是一个专业的代码审查专家。

审查要点：
1. 代码质量：可读性、可维护性、复杂度
2. 安全性：SQL注入、XSS、认证问题
3. 性能：算法效率、资源使用
4. 最佳实践：设计模式、命名规范

请提供：
- 问题列表（按严重程度排序）
- 改进建议
- 示例代码（如适用）
"""

def review_code(code: str, language: str = "python") -> dict:
    """
    审查代码

    Args:
        code: 要审查的代码
        language: 编程语言

    Returns:
        审查结果
    """
    return {
        "action": "review_code",
        "parameters": {
            "code": code,
            "language": language,
        },
        "prompt": SKILL_PROMPT,
    }
