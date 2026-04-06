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
