#!/usr/bin/env python3
"""
Loom 框架自定义任务处理器示例

展示如何基于 TaskHandler 基类实现自定义的任务处理逻辑
"""

from typing import Dict, Any
from loom.core.agent_executor import TaskHandler


class SQLTaskHandler(TaskHandler):
    """SQL 任务处理器示例"""
    
    def can_handle(self, task: str) -> bool:
        """判断是否为 SQL 相关任务"""
        sql_keywords = ["sql", "query", "select", "database", "表", "查询", "数据库"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in sql_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成 SQL 任务的递归指导"""
        
        if result_analysis["has_errors"]:
            return f"""工具执行遇到问题。请重新尝试完成 SQL 任务：{original_task}

建议：
- 检查工具参数是否正确
- 尝试使用不同的方法获取数据
- 如果问题持续，请说明具体错误"""
        
        elif result_analysis["has_data"] and result_analysis["completeness_score"] >= 0.6:
            return f"""工具调用已完成，已获取到所需的数据信息。现在请基于这些数据生成最终的 SQL 查询语句。

重要提示：
- 不要继续调用工具
- 直接生成完整的 SQL 查询
- 确保 SQL 语法正确
- 包含适当的注释说明查询目的

原始任务：{original_task}"""
        
        elif recursion_depth >= 5:
            return f"""已达到较深的递归层级。请基于当前可用的信息生成 SQL 查询。

如果信息不足，请说明需要哪些额外信息。

原始任务：{original_task}"""
        
        else:
            return f"""继续处理 SQL 任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：使用更多工具收集相关信息，或分析已获得的数据"""


class AnalysisTaskHandler(TaskHandler):
    """分析任务处理器示例"""
    
    def can_handle(self, task: str) -> bool:
        """判断是否为分析相关任务"""
        analysis_keywords = ["analyze", "analysis", "examine", "review", "分析", "检查", "评估"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in analysis_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成分析任务的递归指导"""
        
        if result_analysis["suggests_completion"] or result_analysis["completeness_score"] >= 0.8:
            return f"""信息收集基本完成。请基于已收集的信息完成分析任务：{original_task}

请提供：
1. 关键发现和洞察
2. 数据支持的分析结论  
3. 建议或推荐行动
4. 任何需要注意的限制或风险"""
        
        elif result_analysis["has_errors"]:
            return f"""分析过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查数据源是否可用
- 尝试不同的分析方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续分析任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多数据或使用分析工具处理已获得的信息"""


class CodeGenerationTaskHandler(TaskHandler):
    """代码生成任务处理器示例"""
    
    def can_handle(self, task: str) -> bool:
        """判断是否为代码生成相关任务"""
        generation_keywords = ["generate", "create", "build", "make", "生成", "创建", "构建", "开发"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in generation_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成代码生成任务的递归指导"""
        
        if result_analysis["completeness_score"] >= 0.7:
            return f"""信息收集完成。请基于收集到的信息生成代码完成任务：{original_task}

请提供：
- 完整的代码实现
- 必要的注释和文档
- 使用说明或示例"""
        
        elif result_analysis["has_errors"]:
            return f"""代码生成过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查模板或参考代码是否可用
- 尝试不同的生成方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续代码生成任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多参考信息或使用代码分析工具"""


class CustomTaskHandler(TaskHandler):
    """自定义任务处理器示例"""
    
    def __init__(self, task_patterns: list[str], guidance_template: str):
        """
        初始化自定义任务处理器
        
        Args:
            task_patterns: 任务匹配模式列表
            guidance_template: 指导消息模板
        """
        self.task_patterns = task_patterns
        self.guidance_template = guidance_template
    
    def can_handle(self, task: str) -> bool:
        """判断是否能处理给定任务"""
        task_lower = task.lower()
        return any(pattern.lower() in task_lower for pattern in self.task_patterns)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成自定义指导消息"""
        
        # 使用模板生成指导消息
        guidance = self.guidance_template.format(
            original_task=original_task,
            completeness_score=result_analysis['completeness_score'],
            has_data=result_analysis['has_data'],
            has_errors=result_analysis['has_errors'],
            recursion_depth=recursion_depth
        )
        
        return guidance


def create_default_task_handlers() -> list[TaskHandler]:
    """创建默认的任务处理器集合"""
    return [
        SQLTaskHandler(),
        AnalysisTaskHandler(),
        CodeGenerationTaskHandler(),
    ]


def create_custom_task_handlers() -> list[TaskHandler]:
    """创建自定义任务处理器集合"""
    return [
        # 自定义报告生成处理器
        CustomTaskHandler(
            task_patterns=["report", "报告", "summary", "总结"],
            guidance_template="""继续生成报告任务：{original_task}

当前进度：{completeness_score:.0%}
状态：{'有数据' if has_data else '无数据'}, {'有错误' if has_errors else '无错误'}
递归深度：{recursion_depth}

建议：{'基于已有数据生成报告' if has_data else '收集更多数据'}"""
        ),
        
        # 自定义测试任务处理器
        CustomTaskHandler(
            task_patterns=["test", "测试", "testing"],
            guidance_template="""继续测试任务：{original_task}

进度：{completeness_score:.0%}
{'发现错误，需要修复' if has_errors else '测试正常进行'}
深度：{recursion_depth}

下一步：{'修复发现的问题' if has_errors else '继续执行测试'}"""
        ),
    ]


# 使用示例
if __name__ == "__main__":
    print("🎯 Loom 框架自定义任务处理器示例")
    print("=" * 50)
    
    # 创建默认处理器
    default_handlers = create_default_task_handlers()
    print(f"📋 默认处理器数量: {len(default_handlers)}")
    
    # 测试 SQL 处理器
    sql_handler = SQLTaskHandler()
    test_tasks = [
        "生成用户统计的 SQL 查询",
        "分析代码质量",
        "创建 REST API",
        "生成报告"
    ]
    
    print("\n🔍 任务匹配测试:")
    for task in test_tasks:
        for handler in default_handlers:
            if handler.can_handle(task):
                print(f"  ✅ '{task}' -> {handler.__class__.__name__}")
                break
        else:
            print(f"  ❌ '{task}' -> 无匹配处理器")
    
    # 创建自定义处理器
    custom_handlers = create_custom_task_handlers()
    print(f"\n📋 自定义处理器数量: {len(custom_handlers)}")
    
    print("\n✨ 开发者可以通过以下方式使用:")
    print("1. 继承 TaskHandler 基类")
    print("2. 实现 can_handle() 方法定义任务匹配逻辑")
    print("3. 实现 generate_guidance() 方法定义指导生成逻辑")
    print("4. 在创建 AgentExecutor 时传入自定义处理器")
    print("5. 框架会自动使用匹配的处理器生成递归指导")
