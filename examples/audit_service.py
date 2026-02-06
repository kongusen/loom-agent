"""
审计服务 - 基于 Loom v0.5.1 重构

架构设计：
- 每个 chunk 有独立的 EventBus，避免记忆混乱
- 三阶段 Agent 流水线：Scanner → Planner → Verifier
- SSE 流式输出到前端

Run:
  uvicorn examples.audit_service:app --host 0.0.0.0 --port 8009 --reload
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, model_validator
from sse_starlette.sse import EventSourceResponse

# 添加项目根目录到 path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from loom.agent import Agent  # noqa: E402
from loom.config.llm import LLMConfig  # noqa: E402
from loom.events import EventBus  # noqa: E402
from loom.protocol import Task  # noqa: E402
from loom.providers.llm.openai import OpenAIProvider  # noqa: E402
from loom.providers.llm.qwen import QwenProvider  # noqa: E402

# 初始化 FastAPI
app = FastAPI(title="Loom Audit Service", version="0.5.1")


# ============================================================
# 请求模型
# ============================================================


class AuditRequest(BaseModel):
    """审计请求模型"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    fileContent: Any | None = None
    file_content: Any | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_file_content(cls, data: Any):
        if (
            isinstance(data, dict)
            and data.get("fileContent") is None
            and data.get("file_content") is not None
        ):
            merged = dict(data)
            merged["fileContent"] = merged.get("file_content")
            return merged
        return data


# ============================================================
# SSE 事件数据结构
# ============================================================


@dataclass
class SSEEvent:
    """SSE 事件数据"""

    task_id: str
    agent_type: str  # Scanner / Planner / Verifier
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    is_final: bool = False


# ============================================================
# Agent 系统提示词
# ============================================================

SCANNER_PROMPT = """你是一名资深的工程设计文档审查专家 (Scanner)，专注于通信、电力及工业自动化领域的施工图与设计说明审查。

你的任务是仔细阅读工程文档片段，基于工程建设强制性标准和行业规范，敏锐地识别以下风险：
1. **合规性风险**：是否违反国家/行业强制性标准（强条）。
2. **完整性风险**：设计依据是否过期或缺失，关键技术参数是否缺失。
3. **一致性风险**：设计说明与图纸、表格内容是否矛盾。
4. **安全性/可行性**：是否存在明显的施工安全隐患或技术不可行方案。

请列出所有发现的疑点，准确指出问题位置，并简述风险理由。
不要调用工具，只负责发现问题。如果没有发现问题，请明确说明"未发现明显风险"。"""

PLANNER_PROMPT = """你是一名工程审计策划师 (Planner)。你将接收到 Scanner 提交的工程文档疑点列表。

你的核心任务是制定查证计划，并**积极调用工具**获取权威依据：
- 针对设计依据/标准引用问题：调用 `search_knowledge_base` 查询相关标准条款
- 请输出你的调查过程，并提取工具返回的核心条款作为证据

重要：你必须调用 search_knowledge_base 工具来查询相关标准！"""

VERIFIER_PROMPT = """你是一名拥有注册资格的工程合规性审核员 (Verifier)。

你的任务是基于原始设计文档、Scanner 的疑点和 Planner 查证的标准条款，生成最终审计意见。

你的报告必须严谨、客观：
1. **问题确认**：明确问题是否成立。
2. **违规定性**：
   - **严重违规**：违反工程建设强制性条文（需注明"违反强条"）。
   - **一般违规**：不符合一般性标准或公司规定。
   - **建议优化**：技术上可行但有更好方案。
3. **整改依据**：必须引用具体的标准号和条款内容。
4. **整改建议**：给出具体的修改指导。"""


# ============================================================
# ChunkProcessor - 隔离的 chunk 处理器
# ============================================================


class ChunkProcessor:
    """
    单个 chunk 的处理器

    关键设计：每个 ChunkProcessor 有独立的 EventBus，
    确保并行处理时记忆不会混乱。
    """

    def __init__(
        self,
        chunk_index: int,
        chunk_data: dict[str, Any],
        llm: Any,
        sse_queue: asyncio.Queue,
        tools: list[Any] | None = None,
    ):
        self.chunk_index = chunk_index
        self.chunk_data = chunk_data
        self.llm = llm
        self.sse_queue = sse_queue
        self.tools = tools or []

        # 获取原始 ID
        self.task_id = str(chunk_data.get("id", f"task_{chunk_index}"))

        # 关键：每个 chunk 有独立的 EventBus
        self.event_bus = EventBus(debug_mode=True)

        # 当前 agent 类型（用于 SSE 输出）
        self.current_agent_type = "Scanner"

        # 注册事件监听器
        self._register_event_handlers()

    def _register_event_handlers(self):
        """注册事件处理器，将事件转发到 SSE 队列"""

        async def on_thinking(task: Task) -> Task:
            """处理思考事件"""
            content = task.parameters.get("content", "")
            if content:
                await self._emit_sse(content=content)
            return task

        async def on_tool_call(task: Task) -> Task:
            """处理工具调用事件"""
            tool_name = task.parameters.get("tool_name", "")
            tool_args = task.parameters.get("tool_args", {})

            tool_call = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args, ensure_ascii=False, default=str)
                    if isinstance(tool_args, dict)
                    else str(tool_args),
                },
            }
            await self._emit_sse(tool_calls=[tool_call])
            return task

        async def on_complete(task: Task) -> Task:
            """处理完成事件"""
            result = task.parameters.get("result")
            if result:
                content = result.get("content", "") if isinstance(result, dict) else str(result)
                if content:
                    await self._emit_sse(content=content)
            return task

        # 注册到独立的 EventBus
        self.event_bus.register_handler("node.thinking", on_thinking)
        self.event_bus.register_handler("node.tool_call", on_tool_call)
        self.event_bus.register_handler("tool.call", on_tool_call)
        self.event_bus.register_handler("node.complete", on_complete)

    async def _emit_sse(
        self,
        content: str = "",
        tool_calls: list[dict] | None = None,
        is_final: bool = False,
    ):
        """发送 SSE 事件到队列"""
        event = SSEEvent(
            task_id=self.task_id,
            agent_type=self.current_agent_type,
            content=content,
            tool_calls=tool_calls or [],
            is_final=is_final,
        )

        # 转换为 JSON 格式
        data = {
            "taskid": event.task_id,
            "agentid": f"{event.task_id}_{event.agent_type}",
            "agent": event.agent_type,
            "chunk": event.content,
            "tool_calls": event.tool_calls,
            "seglist": [event.task_id],
            "is_final": event.is_final,
        }

        await self.sse_queue.put(json.dumps(data, ensure_ascii=False, default=str))

    async def process(self) -> dict[str, Any] | None:
        """
        执行三阶段 Agent 流水线

        Scanner → Planner → Verifier
        每个阶段的结果显式传递给下一阶段
        """
        chunk_text = self.chunk_data.get("text", "")
        if not chunk_text.strip():
            return None

        # ========== 阶段 1: Scanner ==========
        self.current_agent_type = "Scanner"
        await self._emit_sse(content="\n[Scanner] 开始扫描文档片段...\n")

        scanner = Agent.create(
            self.llm,
            event_bus=self.event_bus,
            node_id=f"{self.task_id}_scanner",
            system_prompt=SCANNER_PROMPT,
            max_iterations=5,
            require_done_tool=True,
        )

        scan_result = await scanner.run(f"请扫描以下文档段落，找出风险点：\n\n{chunk_text}")

        # 检查是否有发现
        scan_text = self._extract_result(scan_result)
        if "未发现" in scan_text and len(scan_text) < 100:
            await self._emit_sse(
                content="\n[系统] 未发现明显风险，跳过后续步骤。\n",
                is_final=True,
            )
            return {"status": "no_issues", "scan_result": scan_text}

        # ========== 阶段 2: Planner ==========
        self.current_agent_type = "Planner"
        await self._emit_sse(content="\n[Planner] 开始查证标准...\n")

        planner = Agent.create(
            self.llm,
            event_bus=self.event_bus,
            node_id=f"{self.task_id}_planner",
            system_prompt=PLANNER_PROMPT,
            tools=self.tools,  # 传入知识库查询工具
            max_iterations=10,
            require_done_tool=True,
        )

        plan_input = f"基于以下发现的问题，请调用工具查证相关标准：\n\n{scan_text}"
        plan_result = await planner.run(plan_input)
        plan_text = self._extract_result(plan_result)

        # ========== 阶段 3: Verifier ==========
        self.current_agent_type = "Verifier"
        await self._emit_sse(content="\n[Verifier] 生成审计报告...\n")

        verifier = Agent.create(
            self.llm,
            event_bus=self.event_bus,
            node_id=f"{self.task_id}_verifier",
            system_prompt=VERIFIER_PROMPT,
            max_iterations=5,
            require_done_tool=True,
        )

        verify_input = f"""请生成本片段的审计报告。

【原始文档片段】：
{chunk_text}

【扫描发现】：
{scan_text}

【工具查证结果】：
{plan_text}
"""
        verify_result = await verifier.run(verify_input)
        verify_text = self._extract_result(verify_result)

        # 发送最终结果
        await self._emit_sse(content=verify_text, is_final=True)

        return {
            "status": "completed",
            "scan_result": scan_text,
            "plan_result": plan_text,
            "verify_result": verify_text,
        }

    def _extract_result(self, result: Any) -> str:
        """从 Agent 结果中提取文本"""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("content", str(result))
        if hasattr(result, "result"):
            r = result.result
            if isinstance(r, dict):
                return r.get("content", str(r))
            return str(r) if r else ""
        return str(result)


# ============================================================
# 工具函数
# ============================================================


async def search_knowledge_base(query: str) -> str:
    """
    查询知识库获取相关标准和规范信息

    这是一个示例实现，实际使用时替换为真实的知识库查询
    """
    print(f"\n[工具执行] 正在查询知识库: Query='{query}'...")

    # 示例：模拟知识库查询结果
    # 实际使用时，替换为真实的 kb_search_func 调用
    try:
        # 如果有真实的知识库，取消下面的注释
        # from tools.kb_search import kb_search_func
        # result = await kb_search_func(query=query)
        # return str(result)

        # 模拟返回
        return f"[知识库查询结果] 查询: {query}\n相关标准条款：（示例数据）"
    except Exception as e:
        return f"查询失败: {str(e)}"


def create_llm_provider():
    """创建 LLM Provider"""
    provider = os.getenv("LLM_PROVIDER", "qwen").lower()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("请设置 OPENAI_API_KEY 环境变量")

        config = LLMConfig(
            provider="openai",
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=temperature,
        )
        return OpenAIProvider(config=config)
    else:
        config = LLMConfig(
            provider="qwen",
            api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY") or "123",
            base_url=os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "111",
            model=os.getenv("LLM_MODEL") or "Qwen",
            temperature=temperature,
        )
        return QwenProvider(config=config)


def chunk_content(raw_data: Any) -> list[dict[str, Any]]:
    """
    切分文档内容

    支持多种输入格式：
    - JSON 字符串
    - dict 包含 file_content/fileContent
    - list 直接的结构化数据
    """
    content_to_parse = raw_data

    try:
        # 尝试从 dict 中提取
        if isinstance(raw_data, dict):
            if "file_content" in raw_data:
                content_to_parse = raw_data["file_content"]
            elif "fileContent" in raw_data:
                content_to_parse = raw_data["fileContent"]

        # 尝试解析 JSON 字符串
        if isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
                if isinstance(parsed, dict):
                    if "file_content" in parsed:
                        content_to_parse = parsed["file_content"]
                    elif "fileContent" in parsed:
                        content_to_parse = parsed["fileContent"]
                elif isinstance(parsed, list):
                    content_to_parse = parsed
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"[Service] 预解析失败: {e}")

    # 如果有真实的解析器，使用它
    # from apps.auditing.utils.structure_parser import (
    #     parse_snapshot_structure,
    #     flatten_tree_to_chunks,
    # )
    # tree = parse_snapshot_structure(content_to_parse)
    # return flatten_tree_to_chunks(tree)

    # 示例：简单切分
    if isinstance(content_to_parse, list):
        return [
            {"id": item.get("id", i), "text": item.get("text", str(item))}
            for i, item in enumerate(content_to_parse)
        ]

    # 按段落切分文本
    if isinstance(content_to_parse, str):
        paragraphs = content_to_parse.split("\n\n")
        return [
            {"id": f"para_{i}", "text": p.strip()} for i, p in enumerate(paragraphs) if p.strip()
        ]

    return [{"id": "0", "text": str(content_to_parse)}]


# ============================================================
# FastAPI 端点
# ============================================================


@app.post("/audit")
async def audit_endpoint(request: AuditRequest):
    """
    审计端点 - SSE 流式输出

    处理流程：
    1. 切分文档
    2. 并行处理每个 chunk（每个有独立 EventBus）
    3. SSE 流式输出结果
    """
    # 1. 解析请求内容
    raw_content = request.fileContent
    print("[Service] 收到审计请求")

    # 2. 切分文档
    chunks = chunk_content(raw_content)
    print(f"[Service] 文档已切分为 {len(chunks)} 个片段")

    # 限制处理数量（可配置）
    max_chunks = int(os.getenv("MAX_CHUNKS", "5"))
    chunks = chunks[:max_chunks]

    # 3. 创建 LLM Provider
    llm = create_llm_provider()

    # 4. 创建工具列表
    tools = [search_knowledge_base]

    # 5. 创建 SSE 队列
    sse_queue: asyncio.Queue = asyncio.Queue()

    # 6. 并发控制
    semaphore = asyncio.Semaphore(int(os.getenv("CONCURRENCY", "3")))

    async def process_single_chunk(index: int, chunk: dict):
        """处理单个 chunk（带并发控制）"""
        async with semaphore:
            processor = ChunkProcessor(
                chunk_index=index,
                chunk_data=chunk,
                llm=llm,
                sse_queue=sse_queue,
                tools=tools,
            )
            try:
                await processor.process()
            except Exception as e:
                # 发送错误信息
                error_data = {
                    "taskid": str(chunk.get("id", index)),
                    "agent": "Error",
                    "chunk": f"处理失败: {str(e)}",
                    "tool_calls": [],
                    "is_final": True,
                }
                await sse_queue.put(json.dumps(error_data, ensure_ascii=False))

    async def run_all_tasks():
        """并行运行所有 chunk 处理任务"""
        tasks = [process_single_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        await asyncio.gather(*tasks, return_exceptions=True)
        # 发送结束信号
        await sse_queue.put(None)

    # 启动后台任务
    asyncio.create_task(run_all_tasks())

    async def event_generator():
        """SSE 事件生成器"""
        while True:
            try:
                data = await asyncio.wait_for(sse_queue.get(), timeout=600.0)
                if data is None:
                    # 结束信号
                    break
                yield data
            except TimeoutError:
                # 超时，继续等待
                continue
            except Exception as e:
                print(f"[Service] SSE 错误: {e}")
                break

    return EventSourceResponse(event_generator())


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "version": "0.5.1"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Loom Audit Service",
        "version": "0.5.1",
        "endpoints": {
            "/audit": "POST - 审计文档（SSE 流式输出）",
            "/health": "GET - 健康检查",
        },
    }


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8009")),
    )
