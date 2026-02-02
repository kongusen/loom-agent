"""
任务执行器 TUI Demo - 基于Textual的交互式任务执行界面

特性：
- 任务分解和进度追踪
- 结构化输出（代码、方案）
- 智能RAG知识库
- 工具和Skill集成
- 实时执行状态

运行：
  OPENAI_API_KEY=... python examples/task_executor_tui.py

快捷键：
  - Tab: 切换面板
  - Ctrl+C: 退出
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from loom.agent import Agent
from loom.tools.registry import ToolRegistry
from loom.config.llm import LLMConfig
from loom.events import EventBus
from loom.protocol import Task
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.llm.openai import OpenAIProvider

# ==================== 数据结构 ====================


@dataclass
class TaskExecutionState:
    """任务执行状态（优化版）"""

    # 任务列表（包含状态信息）
    # 每个任务: {"step": str, "status": str, "index": int}
    # status: "pending", "in_progress", "completed"
    tasks: list[dict[str, Any]] = field(default_factory=list)

    # 当前执行的任务索引
    current_task_index: int = -1

    # 当前执行的任务
    current_task: str = ""

    # 生成的代码块
    code_blocks: list[dict[str, str]] = field(default_factory=list)

    # 解决方案
    solutions: list[str] = field(default_factory=list)

    # 工具调用记录
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)

    # 知识库查询记录
    knowledge_queries: int = 0

    # 统计信息
    total_tasks: int = 0
    completed_tasks: int = 0


# ==================== 技术知识库 ====================


class TechnicalKnowledgeBase(KnowledgeBaseProvider):
    """技术知识库 - 用于任务执行的技术参考"""

    def __init__(self):
        self.knowledge_data = [
            {
                "id": "kb_auth_001",
                "content": "用户认证系统通常包括：用户注册、登录、密码加密（bcrypt/argon2）、"
                "会话管理（JWT/Session）、权限控制（RBAC）。"
                "安全要点：密码哈希、HTTPS传输、防暴力破解、双因素认证。",
                "source": "认证系统设计指南",
                "tags": ["auth", "security", "jwt", "session"],
            },
            {
                "id": "kb_queue_001",
                "content": "任务队列系统核心组件：生产者、消费者、队列存储（Redis/RabbitMQ）、"
                "任务调度器。实现要点：任务持久化、失败重试、优先级队列、并发控制。",
                "source": "任务队列架构",
                "tags": ["queue", "redis", "rabbitmq", "async"],
            },
            {
                "id": "kb_db_001",
                "content": "数据库优化策略：索引优化（B-tree/Hash）、查询优化（EXPLAIN分析）、"
                "连接池管理、缓存策略（Redis）、分库分表、读写分离。",
                "source": "数据库性能优化",
                "tags": ["database", "optimization", "index", "cache"],
            },
            {
                "id": "kb_api_001",
                "content": "RESTful API设计原则：资源导向、HTTP方法语义、状态码规范、"
                "版本控制、认证授权、限流熔断、文档规范（OpenAPI）。",
                "source": "API设计最佳实践",
                "tags": ["api", "rest", "design", "http"],
            },
        ]

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        """查询技术知识"""
        query_lower = query.lower()
        results = []

        for item in self.knowledge_data:
            content_lower = item["content"].lower()
            tags_lower = [tag.lower() for tag in item["tags"]]

            relevance = 0.0
            if query_lower in content_lower:
                relevance = 0.95
            elif any(query_lower in tag for tag in tags_lower):
                relevance = 0.85
            elif any(word in content_lower for word in query_lower.split()):
                relevance = 0.75

            if relevance > 0:
                results.append(
                    KnowledgeItem(
                        id=item["id"],
                        content=item["content"],
                        source=item["source"],
                        relevance=relevance,
                        metadata={"tags": item["tags"]},
                    )
                )

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """根据ID获取知识项"""
        for item in self.knowledge_data:
            if item["id"] == knowledge_id:
                return KnowledgeItem(
                    id=item["id"],
                    content=item["content"],
                    source=item["source"],
                    relevance=1.0,
                    metadata={"tags": item["tags"]},
                )
        return None


# ==================== 工具定义 ====================


# 工具实现函数
async def generate_code(language: str, description: str) -> str:
    """
    代码生成工具实现

    Args:
        language: 编程语言
        description: 代码功能描述

    Returns:
        生成的代码
    """
    # 简单的代码模板生成（实际应用中可以使用 LLM 生成）
    code_templates = {
        "python": f'''# {description}

def main():
    """
    {description}
    """
    # TODO: 实现具体逻辑
    pass

if __name__ == "__main__":
    main()
''',
        "javascript": f"""// {description}

function main() {{
    // TODO: 实现具体逻辑
}}

main();
""",
        "go": f"""// {description}

package main

import "fmt"

func main() {{
    // TODO: 实现具体逻辑
    fmt.Println("Hello, World!")
}}
""",
    }

    template = code_templates.get(language.lower(), f"// {description}\n// TODO: 实现代码")
    return f"已生成 {language} 代码：\n\n```{language}\n{template}\n```"


async def design_architecture(system_type: str, requirements: str) -> str:
    """
    架构设计工具实现

    Args:
        system_type: 系统类型
        requirements: 系统需求

    Returns:
        架构设计方案
    """
    architecture = f"""
## 系统架构设计

**系统类型**: {system_type}
**需求**: {requirements}

### 核心组件
1. **API 层**: 处理外部请求
2. **业务逻辑层**: 实现核心功能
3. **数据层**: 数据存储和访问

### 技术栈建议
- 后端框架: FastAPI / Express
- 数据库: PostgreSQL / MongoDB
- 缓存: Redis
- 消息队列: RabbitMQ / Kafka

### 数据流
请求 → API Gateway → 业务服务 → 数据库
"""
    return architecture


async def plan_task(task_description: str) -> str:
    """
    任务规划工具实现

    Args:
        task_description: 任务描述

    Returns:
        任务分解步骤
    """
    plan = f"""
## 任务分解计划

**任务**: {task_description}

### 执行步骤
1. **需求分析**: 明确任务目标和约束条件
2. **方案设计**: 设计技术方案和架构
3. **开发实现**: 编写代码实现功能
4. **测试验证**: 进行单元测试和集成测试
5. **部署上线**: 部署到生产环境

### 预期产出
- 详细的技术方案文档
- 可运行的代码实现
- 完整的测试用例
"""
    return plan


def create_code_generator_tool():
    """代码生成工具"""
    return {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "生成指定语言的代码实现",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "编程语言（如 python, javascript, go）",
                    },
                    "description": {
                        "type": "string",
                        "description": "代码功能描述",
                    },
                },
                "required": ["language", "description"],
            },
        },
    }


def create_architecture_tool():
    """架构设计工具"""
    return {
        "type": "function",
        "function": {
            "name": "design_architecture",
            "description": "设计系统架构，包括组件、接口、数据流",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_type": {
                        "type": "string",
                        "description": "系统类型（如 web_api, microservice, data_pipeline）",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "系统需求描述",
                    },
                },
                "required": ["system_type", "requirements"],
            },
        },
    }


def create_task_planner_tool():
    """任务规划工具"""
    return {
        "type": "function",
        "function": {
            "name": "plan_task",
            "description": "将复杂任务分解为可执行的步骤",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "任务描述",
                    },
                },
                "required": ["task_description"],
            },
        },
    }


# ==================== 事件处理器 ====================


class TaskEventProcessor:
    """任务事件处理器 - 处理任务执行事件并更新TUI"""

    def __init__(self, app: "TaskExecutorApp"):
        self.app = app
        self.current_step = ""

    async def on_event(self, task: Task) -> Task:
        """处理事件"""
        # 安全检查：确保 parameters 不为 None
        if task.parameters is None:
            return task

        action = task.action

        if action == "node.planning":
            # 任务规划
            plan = task.parameters.get("plan", {})
            steps = plan.get("steps", [])
            await self.app.show_task_plan(steps)

        elif action == "node.step_start":
            # 步骤开始
            step = task.parameters.get("step", "")
            self.current_step = step
            await self.app.update_current_step(step)

        elif action == "node.tool_call":
            # 工具调用
            tool_name = task.parameters.get("tool_name", "unknown")
            await self.app.add_tool_call(tool_name)

        elif action == "node.code_generated":
            # 代码生成
            code = task.parameters.get("code", "")
            language = task.parameters.get("language", "python")
            await self.app.add_code_block(code, language)

        elif action == "node.solution":
            # 解决方案
            solution = task.parameters.get("solution", "")
            await self.app.add_solution(solution)

        elif action == "node.knowledge_query":
            # 知识库查询
            await self.app.increment_knowledge_queries()

        elif action == "node.task_complete":
            # 任务完成
            await self.app.mark_task_complete()

        return task


# ==================== TUI 组件 ====================


class TaskListPanel(RichLog):
    """任务列表面板 - 显示任务分解和进度"""

    def __init__(self):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self.border_title = "📋 任务列表"


class OutputPanel(RichLog):
    """输出面板 - 显示代码和解决方案"""

    def __init__(self):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self.border_title = "📄 输出"


class ExecutionStatsPanel(Static):
    """执行统计面板"""

    def __init__(self):
        super().__init__()
        self.border_title = "📊 执行统计"
        self.total_tasks = 0
        self.completed_tasks = 0
        self.tool_calls = 0
        self.knowledge_queries = 0
        self.code_blocks = 0

    def update_stats(
        self,
        total_tasks: int,
        completed_tasks: int,
        tool_calls: int,
        knowledge_queries: int,
        code_blocks: int,
    ):
        """更新统计信息"""
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.tool_calls = tool_calls
        self.knowledge_queries = knowledge_queries
        self.code_blocks = code_blocks
        self.update(self._render_stats())

    def _render_stats(self) -> str:
        """渲染统计信息（优化版 - 带进度条和百分比）"""
        # 计算进度百分比
        if self.total_tasks > 0:
            percentage = int((self.completed_tasks / self.total_tasks) * 100)
            progress_text = f"{self.completed_tasks}/{self.total_tasks}"
        else:
            percentage = 0
            progress_text = "0/0"

        # 创建可视化进度条（20个字符宽）
        bar_width = 20
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # 根据进度使用不同颜色
        if percentage == 100:
            progress_color = "green"
        elif percentage >= 50:
            progress_color = "yellow"
        else:
            progress_color = "cyan"

        return f"""
[bold {progress_color}]任务进度:[/bold {progress_color}] {progress_text} ({percentage}%)
[{progress_color}]{bar}[/{progress_color}]

[bold green]工具调用:[/bold green] {self.tool_calls}
[bold yellow]知识查询:[/bold yellow] {self.knowledge_queries}
[bold magenta]代码块:[/bold magenta] {self.code_blocks}
"""


# ==================== 主应用 ====================


class TaskExecutorApp(App):
    """任务执行器 TUI 应用"""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #left-panel {
        width: 1fr;
        layout: vertical;
    }

    #right-panel {
        width: 2fr;
        layout: vertical;
    }

    TaskListPanel {
        height: 1fr;
        border: solid cyan;
    }

    OutputPanel {
        height: 1fr;
        border: solid green;
    }

    ExecutionStatsPanel {
        height: 10;
        border: solid yellow;
    }

    Input {
        dock: bottom;
    }
    """

    def __init__(self, agent: Any):
        super().__init__()
        self.agent = agent
        self.state = TaskExecutionState()
        self.task_list_panel = None
        self.output_panel = None
        self.stats_panel = None

    def compose(self) -> ComposeResult:
        """组合UI"""
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                self.task_list_panel = TaskListPanel()
                yield self.task_list_panel
                self.stats_panel = ExecutionStatsPanel()
                yield self.stats_panel
            with Vertical(id="right-panel"):
                self.output_panel = OutputPanel()
                yield self.output_panel
        yield Input(placeholder="输入任务描述... (输入 'quit' 退出)")
        yield Footer()

    async def on_mount(self):
        """应用启动时"""
        self.task_list_panel.write("[bold green]🚀 任务执行器已启动[/bold green]")
        self.task_list_panel.write("[dim]特性: 任务分解 | 代码生成 | 智能RAG | Skill集成[/dim]")
        self.task_list_panel.write("")
        self.output_panel.write("[bold cyan]📄 输出区域[/bold cyan]")
        self.output_panel.write("[dim]代码和解决方案将在此显示[/dim]")
        self.output_panel.write("")

    async def on_input_submitted(self, event: Input.Submitted):
        """处理用户输入"""
        task_input = event.value.strip()
        if not task_input:
            return

        # 清空输入框
        event.input.value = ""

        # 检查退出命令
        if task_input.lower() in ["quit", "exit", "退出"]:
            self.exit()
            return

        # 显示任务
        self.task_list_panel.write(f"\n[bold cyan]📝 新任务:[/bold cyan] {task_input}")
        self.task_list_panel.write("")

        # 处理任务
        await self._process_task(task_input)

    async def show_task_plan(self, steps: list[str]):
        """显示任务规划（优化版 - 带状态指示器）"""
        self.task_list_panel.write("[bold yellow]📋 任务分解:[/bold yellow]")

        # 初始化任务列表，所有任务初始状态为pending
        self.state.tasks = []
        for i, step in enumerate(steps):
            task = {"step": step, "status": "pending", "index": i}
            self.state.tasks.append(task)

        # 显示任务列表
        await self._refresh_task_list()

        self.state.total_tasks = len(steps)
        self._update_stats()

    async def _refresh_task_list(self):
        """刷新任务列表显示"""
        status_icons = {"pending": "⏳", "in_progress": "▶️", "completed": "✅"}

        for task in self.state.tasks:
            icon = status_icons.get(task["status"], "❓")
            step = task["step"]
            index = task["index"] + 1

            # 根据状态使用不同的颜色
            if task["status"] == "completed":
                self.task_list_panel.write(f"  {icon} [dim]{index}. {step}[/dim]")
            elif task["status"] == "in_progress":
                self.task_list_panel.write(f"  {icon} [bold green]{index}. {step}[/bold green]")
            else:  # pending
                self.task_list_panel.write(f"  {icon} {index}. {step}")

        self.task_list_panel.write("")

    async def update_current_step(self, step: str):
        """更新当前步骤（优化版 - 更新状态）"""
        # 查找匹配的任务并更新状态
        for i, task in enumerate(self.state.tasks):
            if task["step"] == step or step in task["step"]:
                # 将之前的in_progress任务标记为completed
                if self.state.current_task_index >= 0:
                    self.state.tasks[self.state.current_task_index]["status"] = "completed"
                    self.state.completed_tasks += 1

                # 更新当前任务
                task["status"] = "in_progress"
                self.state.current_task_index = i
                self.state.current_task = step

                # 刷新任务列表显示
                self.task_list_panel.clear()
                self.task_list_panel.write("[bold yellow]📋 任务分解:[/bold yellow]")
                await self._refresh_task_list()
                self._update_stats()
                break

    async def add_tool_call(self, tool_name: str):
        """添加工具调用记录"""
        self.state.tool_calls.append((tool_name, {}))
        self.task_list_panel.write(f"  [dim]🔧 调用工具: {tool_name}[/dim]")
        self._update_stats()

    async def add_code_block(self, code: str, language: str, description: str = ""):
        """添加代码块（优化版 - 结构化展示）"""
        block_num = len(self.state.code_blocks) + 1
        self.state.code_blocks.append(
            {"code": code, "language": language, "description": description}
        )

        # 显示代码块头部
        self.output_panel.write(f"\n[bold cyan]{'='*60}[/bold cyan]")
        self.output_panel.write(
            f"[bold cyan]💻 代码块 #{block_num} - {language.upper()}[/bold cyan]"
        )
        if description:
            self.output_panel.write(f"[dim]{description}[/dim]")
        self.output_panel.write(f"[bold cyan]{'='*60}[/bold cyan]")

        # 显示代码（带语法提示）
        self.output_panel.write(f"```{language}")
        self.output_panel.write(code)
        self.output_panel.write("```")

        # 显示代码块尾部
        self.output_panel.write("[dim]提示: 可以复制上述代码用于实现[/dim]")
        self.output_panel.write("")
        self._update_stats()

    async def add_solution(self, solution: str, solution_type: str = "general"):
        """添加解决方案（优化版 - 模板化展示）"""
        solution_num = len(self.state.solutions) + 1
        self.state.solutions.append(solution)

        # 根据类型使用不同的图标和标题
        type_config = {
            "architecture": ("🏗️", "架构设计"),
            "implementation": ("⚙️", "实现方案"),
            "analysis": ("🔍", "问题分析"),
            "general": ("✨", "解决方案"),
        }
        icon, title = type_config.get(solution_type, ("✨", "解决方案"))

        # 显示解决方案头部
        self.output_panel.write(f"\n[bold green]{'='*60}[/bold green]")
        self.output_panel.write(f"[bold green]{icon} {title} #{solution_num}[/bold green]")
        self.output_panel.write(f"[bold green]{'='*60}[/bold green]")

        # 显示解决方案内容
        self.output_panel.write(solution)

        # 显示解决方案尾部
        self.output_panel.write(f"[bold green]{'='*60}[/bold green]")
        self.output_panel.write("")

    async def increment_knowledge_queries(self):
        """增加知识库查询计数"""
        self.state.knowledge_queries += 1
        self.task_list_panel.write("  [dim]📚 查询知识库[/dim]")
        self._update_stats()

    async def mark_task_complete(self):
        """标记任务完成（优化版 - 更新任务状态）"""
        # 如果有当前任务，标记为完成
        if self.state.current_task_index >= 0 and self.state.current_task_index < len(
            self.state.tasks
        ):
            self.state.tasks[self.state.current_task_index]["status"] = "completed"
            self.state.completed_tasks += 1

            # 刷新任务列表显示
            self.task_list_panel.clear()
            self.task_list_panel.write("[bold yellow]📋 任务分解:[/bold yellow]")
            await self._refresh_task_list()

        self.task_list_panel.write("[bold green]✓ 所有任务完成[/bold green]\n")
        self._update_stats()

    def _update_stats(self):
        """更新统计面板"""
        self.stats_panel.update_stats(
            total_tasks=self.state.total_tasks,
            completed_tasks=self.state.completed_tasks,
            tool_calls=len(self.state.tool_calls),
            knowledge_queries=self.state.knowledge_queries,
            code_blocks=len(self.state.code_blocks),
        )

    async def _process_task(self, task_input: str):
        """处理任务"""
        try:
            # 创建任务
            task = Task(
                task_id=f"task-{self.state.total_tasks}",
                action="execute",
                parameters={"content": task_input},
            )

            # 执行任务
            result = await self.agent.execute_task(task)

            # 调试信息：查看返回结果
            self.task_list_panel.write(f"\n[dim]DEBUG - Task Status: {result.status}[/dim]")
            self.task_list_panel.write(f"[dim]DEBUG - Result Type: {type(result.result)}[/dim]")
            self.task_list_panel.write(
                f"[dim]DEBUG - Result Content: {str(result.result)[:200]}...[/dim]"
            )
            if result.error:
                self.task_list_panel.write(f"[dim]DEBUG - Error: {result.error}[/dim]")

            # 显示结果（安全处理）
            if result.result is None:
                self.output_panel.write("\n[bold yellow]⚠️ 任务完成，但没有返回结果[/bold yellow]")
            elif isinstance(result.result, dict):
                for key, value in result.result.items():
                    self.output_panel.write(f"\n[bold yellow]{key}:[/bold yellow]")
                    self.output_panel.write(str(value))
            else:
                self.output_panel.write("\n[bold green]结果:[/bold green]")
                self.output_panel.write(str(result.result))

            self.output_panel.write("")
            await self.mark_task_complete()

        except Exception as e:
            self.output_panel.write(f"\n[bold red]❌ 错误: {e}[/bold red]")
            self.output_panel.write("")


# ==================== 主函数 ====================


async def main():
    """主函数"""
    # 1. 创建EventBus
    event_bus = EventBus()

    # 2. 配置LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return

    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        temperature=0.7,
    )
    llm = OpenAIProvider(llm_config)
    print("✓ LLM已配置")

    # 3. 配置知识库
    knowledge_base = TechnicalKnowledgeBase()
    print(f"✓ 知识库已配置 ({len(knowledge_base.knowledge_data)} 条技术知识)")

    # 4. 创建ToolRegistry并注册工具实现
    tool_registry = ToolRegistry()
    tool_registry.register_function(generate_code)
    tool_registry.register_function(design_architecture)
    tool_registry.register_function(plan_task)
    print("✓ 工具已注册 (generate_code, design_architecture, plan_task)")

    # 5. 创建工具定义列表
    tools = [
        create_code_generator_tool(),
        create_architecture_tool(),
        create_task_planner_tool(),
    ]

    # 6. 集成Skills（暂时禁用，等待 tool_registry 实现）
    print("✓ Skill集成已跳过（等待 tool_registry 实现）")

    # 7. 创建Agent
    system_prompt = """你是一个专业的任务执行器。

你的职责：
- 分析复杂问题并分解为可执行步骤
- 制定详细的解决方案
- 生成高质量的可执行代码
- 提供清晰的实现指导

你可以使用的工具：
- generate_code: 生成代码实现
- design_architecture: 设计系统架构
- plan_task: 分解任务步骤
- code_review: 审查代码质量（COMPILATION skill）

当需要深度分析时，可以使用deep_analysis skill（INSTANTIATION形式）。

请基于技术知识库，产出结构化、高质量的解决方案和代码。"""

    agent = Agent.from_llm(
        llm=llm,
        node_id="task-executor",
        system_prompt=system_prompt,
        tools=tools,
        event_bus=event_bus,
        knowledge_base=knowledge_base,
        knowledge_max_items=3,
        knowledge_relevance_threshold=0.75,
        require_done_tool=False,
        tool_registry=tool_registry,
    )
    print(f"✓ Agent已创建: {agent.node_id}")

    # 8. 创建TUI应用并设置事件处理器
    tui_app = TaskExecutorApp(agent)
    event_processor = TaskEventProcessor(tui_app)
    event_bus.register_handler("*", event_processor.on_event)
    print("✓ 事件处理器已配置")

    # 10. 运行TUI应用
    print("\n启动任务执行器 TUI...")
    print("=" * 60)
    await tui_app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
