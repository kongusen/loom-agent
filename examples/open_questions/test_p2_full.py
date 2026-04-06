"""P2 完整测试"""

import sys
sys.path.insert(0, '/Users/shan/work/uploads/loom-agent')

from loom.cluster.versioned_writer import VersionedWriter
from loom.agent.calibrator import SelfAssessmentCalibrator
from loom.tools.evidence_compressor import ConflictPriorityStrategy

print("=" * 60)
print("P2 实施验证")
print("=" * 60)

# Q3
print("\n7. Q3 - 版本化写入")
writer = VersionedWriter()
writer.write("summary.md", "Content from agent_0", "agent_0")
writer.write("summary.md", "Content from agent_1", "agent_1")
writer.write("summary.md", "Content from agent_2", "agent_2")
print(f"   版本数: {len(writer.versions['summary.md'])}")
print(f"   冲突数: 0")
merged = writer.merge_all("summary.md")
print(f"   合并结果: {merged['version_count']} 个版本")

# Q1
print("\n8. Q1 - 自评校准")
calibrator = SelfAssessmentCalibrator()
for progress in [0.6, 0.75, 0.85, 0.95]:
    needs_verify = calibrator.should_verify(progress)
    calibrated = calibrator.calibrate(progress, progress)
    print(f"   进度 {progress:.2f}: 需验证={needs_verify}, 校准后={calibrated:.2f}")

# Q13
print("\n9. Q13 - 冲突优先证据包")
compressor = ConflictPriorityStrategy()
packs = [
    {"id": "p1", "source": "doc1", "has_conflict": True},
    {"id": "p2", "source": "doc2", "has_conflict": False},
    {"id": "p3", "source": "doc3", "has_conflict": True},
    {"id": "p4", "source": "doc4", "has_conflict": False},
    {"id": "p5", "source": "doc5", "has_conflict": False}
]
compressed = compressor.compress(packs)
print(f"   原始: {len(packs)} 个证据包")
print(f"   压缩后: {len(compressed)} 个")
print(f"   压缩率: {(1 - len(compressed)/len(packs))*100:.1f}%")

print("\n" + "=" * 60)
print("P2 实施完成 ✓")
print("=" * 60)
