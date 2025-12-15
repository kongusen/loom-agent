"""
Context Assembler - 智能上下文组装器

基于 Anthropic Context Engineering 最佳实践：
1. Primacy Effect: 关键指令放在开头
2. Recency Effect: 关键指令在结尾重复
3. XML Structure: 使用 XML 标签清晰分隔不同部分
4. Priority Management: 基于优先级智能截断
5. Role/Task Separation: 明确分离角色定义和任务描述

参考：https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import IntEnum
import json

from loom.core.message import Message
from loom.core.context import ContextManager
from loom.interfaces.memory import BaseMemory
from loom.interfaces.compressor import BaseCompressor
from loom.utils.token_counter import estimate_tokens


class ComponentPriority(IntEnum):
    """
    组件优先级

    遵循 Anthropic 最佳实践：
    - CRITICAL: 关键指令（Primacy/Recency）
    - ESSENTIAL: 核心任务和角色
    - HIGH: 重要上下文
    - MEDIUM: 一般上下文
    - LOW: 可选信息
    """
    CRITICAL = 100   # 关键指令（永不截断）
    ESSENTIAL = 90   # 核心任务、角色（高优先保留）
    HIGH = 70        # 重要上下文
    MEDIUM = 50      # 一般上下文
    LOW = 30         # 可选信息（最先截断）


@dataclass
class ContextComponent:
    """
    上下文组件

    每个组件代表上下文的一个部分，带有：
    - name: 组件名称
    - content: 组件内容
    - priority: 优先级
    - xml_tag: XML 标签（可选）
    - truncatable: 是否可截断
    - tokens: 预估 token 数
    """
    name: str
    content: str
    priority: ComponentPriority
    xml_tag: Optional[str] = None
    truncatable: bool = True
    tokens: int = field(init=False)

    def __post_init__(self):
        """计算 token 数"""
        self.tokens = estimate_tokens(self.content)

    def to_xml(self) -> str:
        """转换为 XML 格式"""
        if self.xml_tag:
            return f"<{self.xml_tag}>\n{self.content}\n</{self.xml_tag}>"
        return self.content

    def truncate(self, max_tokens: int) -> "ContextComponent":
        """
        截断组件到指定 token 数

        Args:
            max_tokens: 最大 token 数

        Returns:
            截断后的新组件
        """
        if self.tokens <= max_tokens or not self.truncatable:
            return self

        # 简单的字符级截断（可以改进为更智能的截断）
        ratio = max_tokens / self.tokens
        truncated_length = int(len(self.content) * ratio * 0.9)  # 留 10% buffer
        truncated_content = self.content[:truncated_length] + "\n...[truncated]"

        new_component = ContextComponent(
            name=self.name,
            content=truncated_content,
            priority=self.priority,
            xml_tag=self.xml_tag,
            truncatable=self.truncatable,
        )
        return new_component


class ContextAssembler:
    """
    智能上下文组装器

    基于 Anthropic 最佳实践的智能上下文组装：

    1. **Primacy/Recency Effects**:
       - 关键指令放在开头（Primacy）
       - 关键指令在结尾重复（Recency）

    2. **XML Structure**:
       - 使用 XML 标签清晰分隔各部分
       - 便于 Claude 理解结构

    3. **Priority-Based Assembly**:
       - 按优先级排序组件
       - 智能截断低优先级内容

    4. **Role/Task Separation**:
       - 明确分离角色定义和任务
       - 清晰的职责边界

    5. **Few-Shot Management**:
       - 专门管理示例
       - 支持动态示例选择

    示例：
    ```python
    assembler = ContextAssembler(
        max_tokens=100000,
        use_xml_structure=True,
        enable_primacy_recency=True
    )

    # 添加组件
    assembler.add_critical_instruction("Always be helpful and accurate")
    assembler.add_role("You are a research assistant")
    assembler.add_task("Research the topic of AI safety")
    assembler.add_context("Background information...", priority=ComponentPriority.HIGH)
    assembler.add_few_shot_example("Q: ... A: ...")

    # 组装
    assembled = assembler.assemble()
    ```
    """

    def __init__(
        self,
        max_tokens: int = 100000,
        use_xml_structure: bool = True,
        enable_primacy_recency: bool = True,
        compressor: Optional[BaseCompressor] = None,
        memory: Optional[BaseMemory] = None,
    ):
        """
        初始化 Anthropic Context Assembler

        Args:
            max_tokens: 最大 token 预算
            use_xml_structure: 是否使用 XML 结构
            enable_primacy_recency: 是否启用 Primacy/Recency Effects
            compressor: 压缩器（可选）
            memory: Memory 系统（可选）
        """
        self.max_tokens = max_tokens
        self.use_xml_structure = use_xml_structure
        self.enable_primacy_recency = enable_primacy_recency
        self.compressor = compressor
        self.memory = memory

        # 组件存储
        self.components: List[ContextComponent] = []

        # 特殊组件（按 Anthropic 最佳实践组织）
        self.critical_instructions: List[str] = []
        self.role_definition: Optional[str] = None
        self.task_description: Optional[str] = None
        self.few_shot_examples: List[str] = []
        self.output_format: Optional[str] = None

    def add_component(
        self,
        name: str,
        content: str,
        priority: ComponentPriority = ComponentPriority.MEDIUM,
        xml_tag: Optional[str] = None,
        truncatable: bool = True,
    ) -> None:
        """
        添加上下文组件

        Args:
            name: 组件名称
            content: 组件内容
            priority: 优先级
            xml_tag: XML 标签（可选）
            truncatable: 是否可截断
        """
        component = ContextComponent(
            name=name,
            content=content,
            priority=priority,
            xml_tag=xml_tag,
            truncatable=truncatable,
        )
        self.components.append(component)

    def add_critical_instruction(self, instruction: str) -> None:
        """
        添加关键指令（Primacy/Recency）

        这些指令会在开头和结尾出现，确保模型注意到。

        Args:
            instruction: 关键指令
        """
        self.critical_instructions.append(instruction)

    def add_role(self, role: str) -> None:
        """
        设置角色定义

        Args:
            role: 角色描述
        """
        self.role_definition = role

    def add_task(self, task: str) -> None:
        """
        设置任务描述

        Args:
            task: 任务描述
        """
        self.task_description = task

    def add_few_shot_example(self, example: str) -> None:
        """
        添加 Few-Shot 示例

        Args:
            example: 示例内容
        """
        self.few_shot_examples.append(example)

    def add_output_format(self, format_spec: str) -> None:
        """
        设置输出格式要求

        Args:
            format_spec: 格式说明
        """
        self.output_format = format_spec

    def assemble(self) -> str:
        """
        组装上下文（核心方法）

        遵循 Anthropic 最佳实践：
        1. 关键指令（开头）← Primacy Effect
        2. 角色定义
        3. 任务描述
        4. 上下文数据（按优先级）
        5. Few-Shot 示例
        6. 输出格式
        7. 关键指令重复（结尾）← Recency Effect

        Returns:
            组装后的上下文字符串
        """
        sections: List[str] = []

        # === 1. Primacy: 关键指令（开头） ===
        if self.enable_primacy_recency and self.critical_instructions:
            critical = "\n".join(self.critical_instructions)
            if self.use_xml_structure:
                sections.append(f"<critical_instructions>\n{critical}\n</critical_instructions>")
            else:
                sections.append(f"# Critical Instructions\n\n{critical}")

        # === 2. 角色定义 ===
        if self.role_definition:
            if self.use_xml_structure:
                sections.append(f"<role>\n{self.role_definition}\n</role>")
            else:
                sections.append(f"# Role\n\n{self.role_definition}")

        # === 3. 任务描述 ===
        if self.task_description:
            if self.use_xml_structure:
                sections.append(f"<task>\n{self.task_description}\n</task>")
            else:
                sections.append(f"# Task\n\n{self.task_description}")

        # === 4. 上下文组件（按优先级排序和截断） ===
        if self.components:
            # 计算已使用的 token 数
            used_tokens = sum(estimate_tokens(s) for s in sections)

            # 计算关键指令重复的 token 数（如果启用 Recency）
            recency_tokens = 0
            if self.enable_primacy_recency and self.critical_instructions:
                recency_tokens = estimate_tokens("\n".join(self.critical_instructions)) + 50

            # 计算 Few-Shot 和输出格式的预估 token 数
            fewshot_tokens = sum(estimate_tokens(ex) for ex in self.few_shot_examples)
            output_format_tokens = estimate_tokens(self.output_format) if self.output_format else 0

            # 可用 token 预算
            available_tokens = self.max_tokens - used_tokens - recency_tokens - fewshot_tokens - output_format_tokens - 500  # 500 buffer

            # 按优先级排序
            sorted_components = sorted(self.components, key=lambda c: c.priority, reverse=True)

            # 智能截断和添加
            context_parts = []
            remaining_tokens = available_tokens

            for component in sorted_components:
                if component.priority >= ComponentPriority.ESSENTIAL:
                    # 核心组件：必须保留
                    context_parts.append(component.to_xml() if self.use_xml_structure else component.content)
                    remaining_tokens -= component.tokens
                elif remaining_tokens > 0:
                    # 可选组件：根据 token 预算截断
                    if component.tokens <= remaining_tokens:
                        context_parts.append(component.to_xml() if self.use_xml_structure else component.content)
                        remaining_tokens -= component.tokens
                    elif component.truncatable and remaining_tokens > 500:
                        # 截断组件
                        truncated = component.truncate(remaining_tokens)
                        context_parts.append(truncated.to_xml() if self.use_xml_structure else truncated.content)
                        remaining_tokens = 0

            if context_parts:
                if self.use_xml_structure:
                    sections.append(f"<context>\n{chr(10).join(context_parts)}\n</context>")
                else:
                    sections.append(f"# Context\n\n{chr(10).join(context_parts)}")

        # === 5. Few-Shot 示例 ===
        if self.few_shot_examples:
            examples = "\n\n".join(self.few_shot_examples)
            if self.use_xml_structure:
                sections.append(f"<examples>\n{examples}\n</examples>")
            else:
                sections.append(f"# Examples\n\n{examples}")

        # === 6. 输出格式 ===
        if self.output_format:
            if self.use_xml_structure:
                sections.append(f"<output_format>\n{self.output_format}\n</output_format>")
            else:
                sections.append(f"# Output Format\n\n{self.output_format}")

        # === 7. Recency: 关键指令重复（结尾） ===
        if self.enable_primacy_recency and self.critical_instructions:
            critical = "\n".join(self.critical_instructions)
            if self.use_xml_structure:
                sections.append(f"<reminder>\n{critical}\n</reminder>")
            else:
                sections.append(f"# Important Reminder\n\n{critical}")

        return "\n\n".join(sections)

    def clear(self) -> None:
        """清空所有组件"""
        self.components.clear()
        self.critical_instructions.clear()
        self.role_definition = None
        self.task_description = None
        self.few_shot_examples.clear()
        self.output_format = None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        total_tokens = sum(c.tokens for c in self.components)
        total_tokens += sum(estimate_tokens(i) for i in self.critical_instructions)
        total_tokens += estimate_tokens(self.role_definition or "")
        total_tokens += estimate_tokens(self.task_description or "")
        total_tokens += sum(estimate_tokens(ex) for ex in self.few_shot_examples)
        total_tokens += estimate_tokens(self.output_format or "")

        return {
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": total_tokens / self.max_tokens if self.max_tokens > 0 else 0,
            "num_components": len(self.components),
            "num_critical_instructions": len(self.critical_instructions),
            "num_examples": len(self.few_shot_examples),
            "has_role": self.role_definition is not None,
            "has_task": self.task_description is not None,
            "has_output_format": self.output_format is not None,
        }


class EnhancedContextManager(ContextManager):
    """
    增强的 ContextManager（集成 ContextAssembler）

    向后兼容 ContextManager，但使用 Anthropic 最佳实践组装上下文。

    示例：
    ```python
    from loom.core import EnhancedContextManager

    manager = EnhancedContextManager(
        max_context_tokens=100000,
        use_xml_structure=True,
        enable_primacy_recency=True,
        memory=some_memory
    )

    # 使用方式与 ContextManager 相同
    optimized_message = await manager.prepare(message)
    ```
    """

    def __init__(
        self,
        compressor: Optional[BaseCompressor] = None,
        memory: Optional[BaseMemory] = None,
        max_context_tokens: int = 100000,
        compression_threshold: float = 0.8,
        use_xml_structure: bool = True,
        enable_primacy_recency: bool = True,
    ):
        """
        初始化 Enhanced Context Manager

        Args:
            compressor: 压缩器（可选）
            memory: Memory 系统（可选）
            max_context_tokens: 最大 Context token 数
            compression_threshold: 压缩阈值（比例）
            use_xml_structure: 是否使用 XML 结构
            enable_primacy_recency: 是否启用 Primacy/Recency Effects
        """
        super().__init__(
            compressor=compressor,
            memory=memory,
            max_context_tokens=max_context_tokens,
            compression_threshold=compression_threshold,
        )

        self.use_xml_structure = use_xml_structure
        self.enable_primacy_recency = enable_primacy_recency

        # 创建 ContextAssembler
        self.assembler = ContextAssembler(
            max_tokens=max_context_tokens,
            use_xml_structure=use_xml_structure,
            enable_primacy_recency=enable_primacy_recency,
            compressor=compressor,
            memory=memory,
        )

    async def prepare(self, message: Message) -> Message:
        """
        准备 Context（使用智能组装器）

        流程：
        1. 获取完整历史
        2. 使用 ContextAssembler 组装
        3. 如果有 Memory，加载相关内容
        4. 返回优化后的 Message

        Args:
            message: 输入消息

        Returns:
            优化后的消息
        """
        try:
            # 1. 获取完整历史
            messages = self._get_history(message)

            # 2. 如果需要压缩，先压缩
            if self._need_compression(messages):
                messages = await self._compress(messages)

            # 3. 使用 Anthropic Assembler 组装
            # 清空之前的组件
            self.assembler.clear()

            # 提取系统消息作为角色定义
            system_messages = [m for m in messages if m.role == "system"]
            if system_messages:
                self.assembler.add_role(system_messages[0].content)

            # 4. ⭐ 优先添加 RAG Retrieved Memory（必须在对话历史之前！）
            # 原因：
            # 1. Primacy Effect - LLM 对前面的内容记忆更深刻
            # 2. Anti-Lost-in-Middle - 避免被长对话淹没
            # 3. Knowledge-First - 先获得"知识"，再处理"对话"
            if self.memory:
                try:
                    # 调用 retrieve() 方法（所有 Memory 实现都支持，默认返回空字符串）
                    relevant = await self.memory.retrieve(
                        query=message.content,
                        top_k=5,
                        tier="longterm",  # 优先检索长期记忆
                    )

                    if relevant:
                        # 将检索结果作为 ESSENTIAL 优先级组件插入（高于对话历史！）
                        # Note: relevant 已经是 XML 格式 (<retrieved_memory>)，所以 xml_tag=None
                        self.assembler.add_component(
                            name="retrieved_memory",
                            content=relevant,
                            priority=ComponentPriority.ESSENTIAL,  # 90 - 确保在 Session History 之前
                            xml_tag=None,  # 已包含 XML 标签
                            truncatable=True,  # 允许智能截断（但因为优先级高，不会轻易被截断）
                        )
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to retrieve from memory: {str(e)}")

            # 5. 添加对话历史作为上下文（分层优先级）
            # 策略：
            # - 最近 5 条：HIGH (70) - 保持对话连贯性
            # - 10-20 条：MEDIUM (50) - 一般上下文
            # - 20+ 条：LOW (30) - 早期历史，Token 不足时优先丢弃
            other_messages = [m for m in messages if m.role != "system"]
            total_messages = len(other_messages)

            for i, msg in enumerate(other_messages):
                # 动态分配优先级（基于消息位置）
                if i >= total_messages - 5:
                    # 最近 5 条：高优先级
                    priority = ComponentPriority.HIGH  # 70
                elif i >= total_messages - 20:
                    # 中等历史（6-20 条前）：中优先级
                    priority = ComponentPriority.MEDIUM  # 50
                else:
                    # 早期历史（20+ 条前）：低优先级，优先截断
                    priority = ComponentPriority.LOW  # 30

                self.assembler.add_component(
                    name=f"message_{i}",
                    content=f"[{msg.role}]: {msg.content}",
                    priority=priority,
                    xml_tag="message",
                    truncatable=True,
                )

            # 组装上下文（暂时不使用，保持与原 ContextManager 兼容）
            # assembled_context = self.assembler.assemble()

            # 返回带历史的消息（保持原有行为）
            return message.with_history(messages)

        except Exception as e:
            from loom.core.errors import ContextError
            raise ContextError(f"Failed to prepare context: {str(e)}") from e

    def get_stats(self) -> dict:
        """
        获取 Context 统计信息

        Returns:
            统计信息字典
        """
        base_stats = super().get_stats()
        assembler_stats = self.assembler.get_stats()

        return {
            **base_stats,
            "use_xml_structure": self.use_xml_structure,
            "enable_primacy_recency": self.enable_primacy_recency,
            "assembler_stats": assembler_stats,
        }
