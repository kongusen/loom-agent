# A1: 统一接口公理 (Uniform Interface Axiom)

> **公理陈述**: ∀x ∈ System: x implements NodeProtocol

## 设计理念

A1层定义了框架的核心协议，确保所有节点实现统一的接口。
本实现符合**Google A2A协议标准**（2025），支持跨框架的agent互操作。

## 核心组件

### 1. NodeProtocol (`node.py`)
所有节点必须实现的统一接口：
- `node_id`: 节点唯一标识
- `source_uri`: 节点URI
- `agent_card`: A2A能力声明
- `process()`: 处理事件（符合A2公理）
- `execute_task()`: 执行A2A任务
- `get_capabilities()`: 获取能力声明

### 2. AgentCard (`agent_card.py`)
A2A协议的能力声明卡片：
- 支持能力发现机制
- 基于A6四范式（Reflection/Tool/Planning/MultiAgent）
- JSON格式序列化

### 3. Task (`task.py`)
A2A协议的任务模型：
- 任务生命周期管理
- 状态跟踪（pending/running/completed/failed）
- 支持长时间运行的任务

## 与公理系统的关系

- **A1（统一接口）**: NodeProtocol是核心实现
- **A2（事件主权）**: process()方法处理CloudEvent
- **A6（四范式）**: AgentCapability枚举定义四种能力

## A2A协议兼容性

✓ Agent Card能力声明
✓ 基于任务的通信
✓ JSON-RPC 2.0兼容
✓ 框架无关性
✓ 企业级安全支持（待实现）
