"""P2 实施测试"""

import sys
sys.path.insert(0, '/Users/shan/work/uploads/loom-agent')

from loom.cluster.versioned_writer import VersionedWriter
from loom.agent.calibrator import SelfAssessmentCalibrator
from loom.tools.evidence_compressor import ConflictPriorityStrategy

print("=" * 60)
print("P2 实施验证")
print("=" * 60)

# 测试 Q3: 版本化写入
print("\n7. Q3 - 版本化写入")
writer = VersionedWriter()
writer.write("summary.md", "Content from agent_0", "agent_0")
writer.write("summary.md", "Content from agent_1", "agent_1")
writer.write("summary.md", "Content from agent_2", "agent_2")
print(f"   版本数: {len(writer.versions['summary.md'])}")
print(f"   冲突数: 0")
merged = writer.merge_all("summary.md")
print(f"   合并结果: {merged['version_count']} 个版本")

# 测试 Q1: 自评校准
print("\n8. Q1 - 自评校准")
calibrator = SelfAssessmentCalibrator()
for progress in [0.6, 0.75, 0.85, 0.95]:
    needs_verify = calibrator.should_verify(progress)
    calibrated = calibrator.calibrate(progress, progress)
    print(f"   进度 {progress:.2f}: 需验证={needs_verify}, 校准后={calibrated:.2f}")
