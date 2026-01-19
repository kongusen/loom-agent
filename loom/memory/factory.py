"""
记忆工厂 (Memory Factory)

提供便捷的记忆系统创建方法，简化初始化过程。

基于 A4 公理：记忆层次公理
"""

from loom.memory.core import LoomMemory


class MemoryFactory:
    """
    记忆工厂

    提供预设配置的记忆系统创建方法
    """

    @staticmethod
    def create_default(node_id: str = "default_memory") -> LoomMemory:
        """
        创建默认配置的记忆系统

        使用标准的四层记忆配置

        Args:
            node_id: 节点ID

        Returns:
            LoomMemory 实例
        """
        return LoomMemory(node_id=node_id)

    @staticmethod
    def create_for_chat(node_id: str = "chat_memory") -> LoomMemory:
        """
        创建适合对话的记忆系统

        优化配置：较小的 L1 缓冲区，适合快速对话

        Args:
            node_id: 节点ID

        Returns:
            LoomMemory 实例
        """
        return LoomMemory(node_id=node_id, max_l1_size=30)

    @staticmethod
    def create_for_task(node_id: str = "task_memory") -> LoomMemory:
        """
        创建适合任务的记忆系统

        优化配置：较大的 L1 缓冲区，适合复杂任务

        Args:
            node_id: 节点ID

        Returns:
            LoomMemory 实例
        """
        return LoomMemory(node_id=node_id, max_l1_size=100)

    @staticmethod
    def create_custom(
        node_id: str,
        max_l1_size: int = 50,
        enable_l4_vectorization: bool = True,
    ) -> LoomMemory:
        """
        创建自定义配置的记忆系统

        Args:
            node_id: 节点ID
            max_l1_size: L1 缓冲区最大大小
            enable_l4_vectorization: 是否启用 L4 向量化

        Returns:
            LoomMemory 实例
        """
        return LoomMemory(
            node_id=node_id,
            max_l1_size=max_l1_size,
            enable_l4_vectorization=enable_l4_vectorization,
        )
