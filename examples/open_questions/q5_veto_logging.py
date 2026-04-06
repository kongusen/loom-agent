"""Q5: Veto Logging for Audit

问题: Harness 行使否决权应记录到什么粒度，才能支持审计和参数调整？
观测现象: 系统能阻止危险行为，但缺少结构化 veto 日志
实验设计: 定义 veto log schema，在多类场景下回放分析
证据要求: veto log schema、触发样本、日志完整度评估、调参案例
"""

from loom.safety.veto import VetoLogger

# Veto log schema
VETO_SCHEMA = {
    "timestamp": "ISO8601",
    "agent_id": "string",
    "action_type": "string",
    "action_params": "dict",
    "veto_reason": "string",
    "rule_triggered": "string",
    "context_snapshot": "dict",
    "severity": "low|medium|high|critical"
}

async def experiment_veto_logging():
    logger = VetoLogger(schema=VETO_SCHEMA)

    # 模拟多种 veto 场景
    scenarios = [
        {"action": "file_delete", "path": "/etc/passwd"},
        {"action": "network_request", "url": "http://malicious.com"},
        {"action": "shell_exec", "cmd": "rm -rf /"}
    ]

    for scenario in scenarios:
        veto_log = logger.record_veto(
            action=scenario["action"],
            reason="security_violation",
            severity="critical"
        )

    # 分析日志完整度
    analysis = logger.analyze_logs()
    return {
        "log_samples": logger.get_recent(5),
        "completeness": analysis.completeness_score,
        "tuning_suggestions": analysis.parameter_adjustments
    }
