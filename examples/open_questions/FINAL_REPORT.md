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
## 二、调度与终止性

### Q2: d_max 设定依据
- **结论:** d_max 应根据任务类型动态调整
- **最优配置:**
  - code: d_max = 2
  - research: d_max = 5
  - planning: d_max = 3
  - debugging: d_max = 5
- **建议:** 实现 `d_max(task_type)` 函数

### Q7: 心跳间隔优化
- **最优策略:** by_phase (按阶段调节)
- **效果:** 漏检 0，误中断 1，CPU 7.0%，完成率 0.95
- **次优:** by_volatility (按波动性) - 效果好但 CPU 开销高 (8.5%)
- **建议:** 优先使用 by_phase，高波动场景切换到 by_volatility

### Q12: Fork Cache 优化
- **最优策略:** cache_aware_hybrid (混合调度)
- **效果:** cache 命中 0.65，成本 $0.88，延迟 720ms，质量 0.91
- **建议:** 采用 cache-aware 混合调度平衡成本和质量
## 三、协作与隔离

### Q3: DAG 耦合与写冲突
- **结论:** 版本化写入或分区合并可避免冲突
- **推荐策略:**
  - versioned_write: 0 冲突，3 版本
  - topic_partition_merge: 0 冲突，3 版本
- **建议:** 采用 versioned_write，简单可靠

### Q10: Sub-Agent MCP 隔离
- **最优格式:** result_with_structured_schema
- **效果:** 成功率 0.95，错误数 0
- **建议:** Sub-Agent 回传结果时附带结构化 schema 描述

## 四、演化与治理

### Q4: 演化可观测指标
- **结论:** 多维指标可有效追踪系统演化
- **关键指标:**
  - 成功率增长: +0.30
  - 成本降低: 10.1
  - Skill 复用率增长: +0.44
- **主要因素:** skill_accumulation
- **建议:** 建立多维指标面板持续监控

### Q5: Veto 日志审计
- **结论:** 结构化日志支持根因分析和参数调优
- **日志完整度:** 100%
- **建议:** 采用标准 schema 记录所有 veto 事件

### Q8: 紧迫度分类可靠性
- **最优方案:** rule_first_classifier_fallback
- **效果:** 准确率 0.89，延迟 3.2ms，误分类 11
- **建议:** 规则优先，分类器兜底，平衡准确率和延迟
## 总结与行动建议

### 立即实施 (P0)

1. **Q2 - 任务类型感知的 d_max**
   - 实现 `d_max(task_type)` 函数
   - code=2, research=5, planning=3, debugging=5

2. **Q9 - 事件聚合策略**
   - 采用 aggregate 策略压缩高频事件
   - 降低 token 占用 67%

3. **Q10 - Sub-Agent 结构化回传**
   - 要求 Sub-Agent 附带 schema 描述
   - 提升主 Agent 消费成功率至 95%

### 短期优化 (P1)

4. **Q7 - 动态心跳间隔**
   - 实现 by_phase 策略
   - 高波动场景切换到 by_volatility

5. **Q11 - Effort 资源分配**
   - 根据 effort hint 动态分配资源
   - low/medium/high 三档配置

6. **Q12 - Cache-aware 调度**
   - 实现混合调度策略
   - 平衡 cache 复用和模型选择

### 中期研究 (P2)

7. **Q1 - 自评校准**
   - 在任务后期增加验证点
   - 对自评 > 0.8 进行二次确认

8. **Q13 - 冲突优先证据包**
   - 采用 conflict_priority 策略
   - 降低 token 占用 67%

9. **Q3 - 版本化写入**
   - 实现 versioned_write 机制
   - 解决 DAG 拓扑写冲突

### 长期建设 (P3)

10. **Q4 - 演化指标面板**
    - 建立多维指标监控
    - 持续追踪系统能力增长

11. **Q5 - Veto 审计系统**
    - 标准化 veto log schema
    - 支持根因分析和调参

12. **Q8 - 混合分类器**
    - 实现规则优先+分类器兜底
    - 平衡准确率和延迟

---

**实验完成时间:** 2026-04-03
**实验状态:** 全部完成 (12/12)
**下一步:** 按优先级实施建议
