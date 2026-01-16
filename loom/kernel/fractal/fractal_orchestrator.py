"""
Fractal Orchestrator

委托编排器，管理整个委托生命周期，包括验证、工具过滤、子节点生成和执行。
支持显式委托（工具调用）和隐式委托（任务分解）。
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from loom.config.execution import ExecutionConfig
from loom.config.fractal import GrowthStrategy, NodeRole
from loom.kernel.core import ToolExecutor
from loom.protocol.delegation import (
    DelegationRequest,
    DelegationResult,
    SubtaskSpecification,
    TaskDecomposition,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Orchestrator 配置"""

    allow_recursive_delegation: bool = False
    """允许子代理再次委托"""

    max_recursive_depth: int = 2
    """允许递归的最大深度"""

    tool_blacklist: list[str] = field(default_factory=list)
    """工具黑名单"""

    default_child_token_budget: int = 4000
    """子节点的默认 token 预算"""

    max_concurrent_children: int = 5
    """最大并发子节点数"""

    # === Implicit Delegation Config (from FractalConfig) ===
    implicit_mode_enabled: bool = True
    """Enable implicit delegation (via decomposition)"""

    def validate(self):
        """验证配置"""
        if self.max_recursive_depth < 0:
            raise ValueError("max_recursive_depth 必须 >= 0")

        if self.default_child_token_budget <= 0:
            raise ValueError("default_child_token_budget 必须 > 0")

        if self.max_concurrent_children <= 0:
            raise ValueError("max_concurrent_children 必须 > 0")


class FractalOrchestrator:
    """
    委托编排器

    管理委托的完整生命周期：
    1. 验证请求
    2. 过滤工具（上下文隔离）
    3. 生成子节点
    4. 执行子节点
    5. 合成结果
    """

    def __init__(self, parent_node, config: OrchestratorConfig):
        """
        初始化编排器

        Args:
            parent_node: 父 AgentNode 实例
            config: 编排器配置
        """
        self.parent = parent_node
        self.config = config
        self.config.validate()

        # Initialize Execution Engine
        self.execution_config = ExecutionConfig(
            parallel_execution=True, # Controlled by Orchestrator logic
            concurrency_limit=self.config.max_concurrent_children
        )
        self.executor = ToolExecutor(
            self.execution_config,
            read_only_check=self._child_read_only_check
        )

        # 获取父节点的深度
        self.parent_depth = getattr(parent_node, 'depth', 0)

        logger.info(f"初始化 FractalOrchestrator，父节点深度: {self.parent_depth}")

    async def delegate(self, request: DelegationRequest) -> DelegationResult:
        """
        执行委托的主入口

        Args:
            request: 委托请求

        Returns:
            委托结果
        """
        logger.info(f"开始委托，子任务数: {len(request.subtasks)}, 执行模式: {request.execution_mode}")

        try:
            # 1. 验证请求
            self._validate_request(request)

            # 2. 生成子节点
            children = await self._spawn_children(request.subtasks)

            # 3. 执行子节点
            results = await self._execute_children(children, request)

            # 4. 合成结果
            synthesized = await self._synthesize_results(request, results)

            logger.info("委托成功完成")
            return DelegationResult(
                success=True,
                synthesized_result=synthesized,
                subtask_results=results,
                metadata={
                    "execution_mode": request.execution_mode,
                    "subtask_count": len(request.subtasks)
                }
            )

        except Exception as e:
            logger.error(f"委托失败: {e}")
            return DelegationResult(
                success=False,
                synthesized_result=f"委托执行失败: {str(e)}",
                subtask_results=[],
                metadata={"error": str(e)}
            )

    async def process_decomposition(self, decomposition: TaskDecomposition) -> DelegationResult:
        """
        Process task decomposition (Implicit Delegation)

        Converts a TaskDecomposition object into a DelegationRequest and executes it.

        Args:
            decomposition: Task decomposition from LLM

        Returns:
            DelegationResult
        """
        logger.info(f"Processing implicit decomposition: {len(decomposition.subtasks)} subtasks, strategy: {decomposition.strategy}")

        # 1. Convert to SubtaskSpecifictions
        subtasks = []
        for desc in decomposition.subtasks:
            # Determine role based on strategy (simplified logic compared to explicit tool)
            # In Phase 2, we map strategy to roles more intelligently if needed
            role = self._map_strategy_to_role(decomposition.strategy, desc)

            subtasks.append(SubtaskSpecification(
                description=desc,
                role=role.value if role else "executor",
                tools=None, # Inherit from parent
                metadata={"strategy": decomposition.strategy.value}
            ))

        # 2. Determine execution mode
        execution_mode = "parallel"
        if decomposition.strategy == GrowthStrategy.DECOMPOSE or decomposition.strategy == GrowthStrategy.ITERATE: # Sequential chain
            execution_mode = "sequential"

        # 3. Create Request
        request = DelegationRequest(
            subtasks=subtasks,
            execution_mode=execution_mode,
            synthesis_strategy="auto", # Implicit always uses auto synthesis
            reasoning=decomposition.reasoning
        )

        # 4. Delegate
        return await self.delegate(request)

    def _map_strategy_to_role(self, strategy: GrowthStrategy, subtask_desc: str) -> NodeRole | None:
        """Map growth strategy to child role"""
        if strategy == GrowthStrategy.SPECIALIZE:
            return NodeRole.SPECIALIST
        elif strategy == GrowthStrategy.PARALLELIZE:
            return NodeRole.EXECUTOR

        # Check aggregation keywords
        agg_keywords = ["combine", "merge", "aggregate", "synthesize", "summarize"]
        if any(kw in subtask_desc.lower() for kw in agg_keywords):
            return NodeRole.AGGREGATOR

        return NodeRole.EXECUTOR

    def _validate_request(self, request: DelegationRequest):
        """
        验证委托请求

        Args:
            request: 委托请求

        Raises:
            ValueError: 如果请求无效
        """
        # 检查子任务数量
        if not request.subtasks:
            raise ValueError("子任务列表不能为空")

        if len(request.subtasks) > self.config.max_concurrent_children:
            raise ValueError(
                f"子任务数量 ({len(request.subtasks)}) 超过最大并发限制 "
                f"({self.config.max_concurrent_children})"
            )

        # 检查深度限制
        if hasattr(self.parent, 'fractal_config'):
            max_depth = self.parent.fractal_config.max_depth
            if self.parent_depth >= max_depth:
                raise ValueError(
                    f"已达到最大深度 ({max_depth})，无法继续委托"
                )

        logger.debug("请求验证通过")

    def _filter_tools_for_child(
        self,
        subtask: SubtaskSpecification,
        current_depth: int
    ) -> set[str]:
        """
        工具过滤逻辑（上下文隔离的核心）

        Args:
            subtask: 子任务规格
            current_depth: 当前深度

        Returns:
            允许的工具名称集合
        """
        # 1. 获取父节点所有工具
        parent_tools = set(self.parent.known_tools.keys())
        parent_tools.update(self.parent.tool_registry._tools.keys())

        logger.debug(f"父节点工具: {parent_tools}")

        # 2. 应用白名单（如果指定）
        if subtask.tools is not None:
            allowed = set(subtask.tools)
            logger.debug(f"使用子任务指定的工具白名单: {allowed}")
        else:
            # 继承父节点工具
            allowed = parent_tools.copy()
            logger.debug("继承父节点所有工具")

        # 3. 应用递归控制（核心隔离机制）
        child_depth = current_depth + 1

        if child_depth >= self.config.max_recursive_depth:
            # 达到最大递归深度，移除委托工具
            allowed.discard("delegate_subtasks")
            logger.info(f"深度 {child_depth} 达到递归限制，移除 delegate_subtasks 工具")
        elif not self.config.allow_recursive_delegation:
            # 配置禁止递归
            allowed.discard("delegate_subtasks")
            logger.info("配置禁止递归委托，移除 delegate_subtasks 工具")

        # 4. 应用额外黑名单
        for blacklisted in self.config.tool_blacklist:
            if blacklisted in allowed:
                allowed.discard(blacklisted)
                logger.debug(f"移除黑名单工具: {blacklisted}")

        logger.info(f"子节点允许的工具: {allowed}")
        return allowed

    async def _spawn_children(self, subtasks: list[SubtaskSpecification]) -> list:
        """
        生成子节点

        Args:
            subtasks: 子任务列表

        Returns:
            子节点列表
        """
        from loom.config.fractal import NodeRole
        from loom.node.fractal import FractalAgentNode

        children = []
        child_depth = self.parent_depth + 1

        # Compatibility: Update parent's children list if it exists
        if hasattr(self.parent, 'children') and isinstance(self.parent.children, list):
             self.parent.children.clear()

        for i, subtask in enumerate(subtasks):
            # 过滤工具
            allowed_tools = self._filter_tools_for_child(subtask, self.parent_depth)

            # 从父节点工具中筛选
            child_tools = []
            for tool_name in allowed_tools:
                if tool_name in self.parent.known_tools:
                    child_tools.append(self.parent.known_tools[tool_name])

            # 确定角色
            role_map = {
                "specialist": NodeRole.SPECIALIST,
                "executor": NodeRole.EXECUTOR,
                "researcher": NodeRole.SPECIALIST,
                "aggregator": NodeRole.AGGREGATOR
            }
            role = role_map.get(subtask.role or "executor", NodeRole.EXECUTOR)

            # 创建子节点
            child_id = f"{self.parent.node_id}.child{i+1}"

            try:
                child = FractalAgentNode(
                    node_id=child_id,
                    dispatcher=self.parent.dispatcher,
                    role=role,
                    system_prompt=f"你是一个专门处理以下任务的助手：{subtask.description}",
                    tools=child_tools,
                    provider=self.parent.provider,
                    fractal_config=self.parent.fractal_config if hasattr(self.parent, 'fractal_config') else None,
                    depth=child_depth
                )

                # 确保子节点订阅到消息总线（恢复协议优先架构）
                await child._subscribe_to_events()

                children.append(child)

                # Compatibility: Add to parent's children list
                if hasattr(self.parent, 'children') and isinstance(self.parent.children, list):
                    self.parent.children.append(child)

                logger.info(f"创建子节点: {child_id}, 角色: {role.value}, 工具数: {len(child_tools)}")

            except Exception as e:
                logger.error(f"创建子节点失败: {e}")
                raise

        return children

    async def _execute_children(
        self,
        children: list,
        request: DelegationRequest
    ) -> list[dict[str, Any]]:
        """
        执行子节点

        Args:
            children: 子节点列表
            request: 委托请求

        Returns:
            执行结果列表
        """
        mode = request.execution_mode
        subtasks = request.subtasks

        logger.info(f"执行模式: {mode}, 子节点数: {len(children)}")

        if mode == "parallel":
            return await self._execute_parallel(children, subtasks)
        elif mode == "sequential":
            return await self._execute_sequential(children, subtasks)
        elif mode == "adaptive":
            return await self._execute_adaptive(children, subtasks)
        else:
            raise ValueError(f"未知的执行模式: {mode}")

    async def _execute_parallel(
        self,
        children: list,
        subtasks: list[SubtaskSpecification]
    ) -> list[dict[str, Any]]:
        """并行执行所有子节点 (via ToolExecutor)"""
        logger.info("并行执行子节点 (Engine)")

        # 1. Construct "tool calls" for executor
        tool_calls = []
        for _i, (child, subtask) in enumerate(zip(children, subtasks, strict=False)):
            tool_calls.append({
                "name": child.node_id, # Use node_id as virtual tool name
                "arguments": {
                    "child": child,
                    "subtask": subtask
                }
            })

        # 2. Define adapter
        async def _child_execution_adapter(_name: str, args: dict) -> Any:
            child = args["child"]
            subtask = args["subtask"]
            return await child.execute(subtask.description)

        # 3. Execute batch
        results = await self.executor.execute_batch(tool_calls, _child_execution_adapter)

        # 4. Map results back
        processed_results = []
        for res in results:
            if res.error:
                 processed_results.append({
                    "success": False,
                    "result": f"执行失败: {res.result}",
                    "error": str(res.result)
                })
            else:
                result_val = res.result
                processed_results.append({
                    "success": True,
                    "result": result_val.get("result", str(result_val)) if isinstance(result_val, dict) else str(result_val),
                    "metadata": result_val.get("metadata", {}) if isinstance(result_val, dict) else {}
                })

        return processed_results

    def _child_read_only_check(self, _tool_name: str) -> bool:
        """
        Check if child node is safe to run in parallel.
        In Phase 3, we assume all child nodes are safe to run in parallel
        unless they have explicit dependencies (handled by sequential mode).
        So for 'parallel' mode, we return True.
        """
        return True

    async def _execute_sequential(
        self,
        children: list,
        subtasks: list[SubtaskSpecification]
    ) -> list[dict[str, Any]]:
        """顺序执行子节点"""
        logger.info("顺序执行子节点")

        results = []
        for i, (child, subtask) in enumerate(zip(children, subtasks, strict=False)):
            logger.info(f"执行子任务 {i+1}/{len(children)}")
            try:
                result = await self._execute_single_child(child, subtask)
                results.append(result)
            except Exception as e:
                logger.error(f"子任务 {i+1} 执行失败: {e}")
                results.append({
                    "success": False,
                    "result": f"执行失败: {str(e)}",
                    "error": str(e)
                })

        return results

    async def _execute_adaptive(
        self,
        children: list,
        subtasks: list[SubtaskSpecification]
    ) -> list[dict[str, Any]]:
        """自适应执行（简化版：默认并行）"""
        logger.info("自适应执行（当前实现：并行）")
        # TODO: 实现依赖分析和自适应调度
        return await self._execute_parallel(children, subtasks)

    async def _execute_single_child(
        self,
        child,
        subtask: SubtaskSpecification
    ) -> dict[str, Any]:
        """通过消息总线执行子节点"""
        try:
            # 使用消息总线调用子节点（恢复协议优先架构）
            result = await self.parent.call(
                target_node=child.source_uri,
                data={"content": subtask.description}
            )

            return {
                "success": True,
                "result": result.get("result", str(result)) if isinstance(result, dict) else str(result),
                "metadata": result.get("metadata", {}) if isinstance(result, dict) else {}
            }
        except Exception as e:
            logger.error(f"子节点执行异常: {e}")
            raise

    async def _synthesize_results(
        self,
        request: DelegationRequest,
        results: list[dict[str, Any]]
    ) -> str:
        """
        合成结果

        Args:
            request: 委托请求
            results: 执行结果列表

        Returns:
            合成后的结果字符串
        """
        # 获取原始任务描述（从第一个子任务推断）
        task = f"完成以下 {len(results)} 个子任务"
        if request.subtasks:
            task = f"原始任务包含 {len(request.subtasks)} 个子任务"

        # 使用父节点的 synthesizer（如果有）
        if hasattr(self.parent, 'synthesizer') and self.parent.synthesizer:
            logger.info("使用父节点的 synthesizer 进行合成")
            return str(await self.parent.synthesizer.synthesize(
                task,
                results,
                strategy=request.synthesis_strategy
            ))
        else:
            # 降级到简单拼接
            logger.warning("父节点没有 synthesizer，使用简单拼接")
            return self._simple_concatenate(results)

    def _simple_concatenate(self, results: list[dict[str, Any]]) -> str:
        """简单拼接结果（降级方案）"""
        parts = []
        for i, result in enumerate(results, 1):
            result_text = result.get("result", str(result))
            parts.append(f"子任务 {i}:\n{result_text}")
        return "\n\n---\n\n".join(parts)
