"""P3 实施测试"""

import sys
sys.path.insert(0, '/Users/shan/work/uploads/loom-agent')

from datetime import datetime
from loom.safety.veto_auditor import VetoAuditor, VetoLog
from loom.runtime.urgency_classifier import HybridUrgencyClassifier
from loom.evolution.dashboard import EvolutionDashboard, EvolutionMetrics

print("=" * 60)
print("P3 实施验证")
print("=" * 60)

# Q5: Veto 审计
print("\n10. Q5 - Veto 审计系统")
auditor = VetoAuditor()
auditor.log_veto(VetoLog(
    timestamp=datetime.now(),
    agent_id="agent_1",
    action_type="file_delete",
    action_params={"path": "/etc/passwd"},
    veto_reason="security_violation",
    rule_triggered="system_file_protection",
    severity="critical"
))
analysis = auditor.analyze()
print(f"   总 veto 数: {analysis['total_vetos']}")
print(f"   严重级别: {analysis['critical_count']}")
print(f"   完整度: {analysis['completeness']:.0%}")

# Q8: 混合分类器
print("\n11. Q8 - 混合分类器")
classifier = HybridUrgencyClassifier()
events = [
    {"type": "error_occurred"},
    {"type": "warning_detected"},
    {"type": "info_message"},
    {"type": "unknown_event"}
]
for event in events:
    urgency = classifier.classify(event)
    print(f"   {event['type']:20s} -> {urgency}")

# Q4: 演化指标面板
print("\n12. Q4 - 演化指标面板")
dashboard = EvolutionDashboard()
dashboard.record(EvolutionMetrics(0.70, 100.0, 0.30, 10))
dashboard.record(EvolutionMetrics(1.00, 90.0, 0.74, 19))
growth = dashboard.analyze_growth()
print(f"   能力增长: {growth['capability_growth']}")
print(f"   成功率提升: {growth['success_delta']:+.2f}")
print(f"   成本降低: {growth['cost_reduction']:.1f}")

print("\n" + "=" * 60)
print("P3 实施完成 ✓")
print("=" * 60)
