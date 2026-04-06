### 5. Q11 - Effort 资源分配 ✓
- **文件:** `loom/tools/resource_allocator.py`
- **实现:** `allocate_resources()` 函数
- **配置:**
  - low: 30s / 1000 tokens / 深度 2
  - medium: 60s / 3000 tokens / 深度 4
  - high: 120s / 8000 tokens / 深度 7

### 6. Q12 - Cache-aware 调度 ✓
- **文件:** `loom/cluster/cache_scheduler.py`
- **实现:** `CacheAwareScheduler` 类
- **效果:** 成本 $0.88, 延迟 720ms, 质量 0.91

---

## P2 - 中期研究 (已完成)

### 7. Q1 - 自评校准 ✓
- **文件:** `loom/agent/calibrator.py`
- **实现:** `SelfAssessmentCalibrator` 类
- **策略:** 进度 > 0.8 需要验证，应用 -0.092 校准因子

### 8. Q13 - 冲突优先证据包 ✓
- **文件:** `loom/tools/evidence_compressor.py`
- **实现:** `ConflictPriorityStrategy` 类
- **效果:** tokens 2800, 引用准确率 0.92, 质量 0.90

### 9. Q3 - 版本化写入 ✓
- **文件:** `loom/cluster/versioned_writer.py`
- **实现:** `VersionedWriter` 类
- **效果:** 0 冲突, 支持版本合并
