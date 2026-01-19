"""
Test Assertions Helper

提供针对 Loom 框架的自定义断言函数，简化测试代码。
"""

from typing import Any

from loom.memory import LoomMemory, MemoryUnit
from loom.protocol import Task, TaskStatus


def assert_task_completed(task: Task, expected_result: Any = None):
    """
    断言任务已成功完成

    Args:
        task: 任务对象
        expected_result: 期望的结果（可选）
    """
    assert task.status == TaskStatus.COMPLETED, f"Task status is {task.status}, expected COMPLETED"
    assert task.result is not None, "Task result should not be None"

    if expected_result is not None:
        assert (
            task.result == expected_result
        ), f"Task result is {task.result}, expected {expected_result}"


def assert_task_failed(task: Task, expected_error: str = None):
    """
    断言任务失败

    Args:
        task: 任务对象
        expected_error: 期望的错误信息（可选）
    """
    assert task.status == TaskStatus.FAILED, f"Task status is {task.status}, expected FAILED"
    assert task.error is not None, "Task error should not be None"

    if expected_error is not None:
        assert (
            expected_error in task.error
        ), f"Expected error '{expected_error}' not found in '{task.error}'"


def assert_memory_contains(memory: LoomMemory, content: str):
    """
    断言记忆系统包含指定内容

    Args:
        memory: 记忆系统
        content: 期望的内容
    """
    # 检查所有层级的记忆
    all_content = []

    # L1
    for unit in memory.l1_raw_io:
        all_content.append(unit.content)

    # L2
    for unit in memory.l2_working.values():
        all_content.append(unit.content)

    # L3
    for unit in memory.l3_session:
        all_content.append(unit.content)

    assert any(content in c for c in all_content), f"Content '{content}' not found in memory"


def assert_memory_unit_valid(unit: MemoryUnit):
    """
    断言记忆单元有效

    Args:
        unit: 记忆单元
    """
    assert unit.id is not None, "Memory unit ID should not be None"
    assert unit.content is not None, "Memory unit content should not be None"
    assert unit.tier is not None, "Memory unit tier should not be None"
    assert unit.type is not None, "Memory unit type should not be None"
    assert (
        0.0 <= unit.importance <= 1.0
    ), f"Memory unit importance {unit.importance} should be between 0 and 1"
