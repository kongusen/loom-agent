# Chapter 10 开放问题实验报告

## 实验概述

本报告总结了 hernss Agent 框架第 10 章开放问题的实验结果。

## 一、认知可靠性

### Q1: LLM 自我感知可靠性
- **后期平均偏差:** +0.092
- **结论:** 自评较准确，但在 70% 完成度后存在轻微高估
- **建议:** 在任务后期增加客观验证点

### Q9: 心跳事件 Token 压力
- **最优策略:** aggregate (聚合摘要)
- **效果:** 事件数降至 10，token 800，完成率 0.90
- **建议:** 采用聚合摘要策略压缩高频事件

### Q11: Skill Effort Hints 量化
- **结论:** effort hint 与资源消耗呈正相关
- **建议配置:**
  - low: 30s / 1000 tokens
  - medium: 60s / 3000 tokens
  - high: 120s / 8000 tokens

### Q13: Knowledge Surface Token 压力
- **最优策略:** conflict_priority (冲突优先)
- **效果:** tokens 2800，引用准确率 0.92，质量 0.90
- **建议:** 采用冲突优先策略平衡 token 和质量
