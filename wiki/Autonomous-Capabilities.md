# 自主能力 (Autonomous Capabilities)

## 定义

**自主能力**是指 Agent 根据任务自主决定使用哪些能力，无需外部干预。

## 核心思想

传统 Agent 需要外部告诉它"现在使用工具"、"现在调用 API"。

Loom Agent 自己决定：
- 这个任务需要规划吗？→ 用 create_plan
- 这个任务需要协作吗？→ 用 delegate_task
- 这个任务需要工具吗？→ 调用相应工具
- 这个任务只需要思考？→ 直接回答

## LLM 自主决策

```python
system_prompt = """
你是一个自主智能体，具备四种核心能力：
1. 反思能力（Reflection）
2. 工具使用（Tool Use）
3. 规划能力（Planning）
4. 协作能力（Collaboration）

**工作原则**：
- 根据任务复杂度自主决定使用哪些能力
- 不要询问是否可以使用某个能力，直接使用
- 追求高效完成任务
"""
```

## 决策逻辑

### 简单任务

```
User: 什么是 Python？

Agent (判断: 简单，只需思考)
→ 直接回答 (反思)
```

### 中等任务

```
User: 查询北京天气

Agent (判断: 需要外部信息)
→ 调用 weather_tool (工具使用)
```

### 复杂任务

```
User: 实现一个博客系统

Agent (判断: 多步骤，复杂度高)
→ create_plan 制定计划 (规划)
→ 按计划执行 (工具使用)
```

### 超复杂任务

```
User: 研究并开发 AI 产品

Agent (判断: 需要多个专业领域)
→ delegate_task 委派专家 (协作)
→ 整合结果 (反思)
```

## 相关概念

- → [公理系统](Axiomatic-System) (A5: 自主决策公理)
- → [四范式工作](Four-Paradigms)

## 代码位置

- `loom/orchestration/agent.py`

## 反向链接

被引用于: [四范式工作](Four-Paradigms) | [Agent API](API-Agent)
