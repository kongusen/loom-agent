"""
工具安全管理器

实现工具安全策略、权限控制和风险评估
"""

import time
import hashlib
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ...types import ToolCall, ToolSafetyLevel


class SecurityAction(Enum):
    """安全动作"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    SANDBOX = "sandbox"


@dataclass
class SecurityPolicy:
    """安全策略"""
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    
    # 策略适用范围
    applicable_tools: Set[str] = field(default_factory=set)
    applicable_users: Set[str] = field(default_factory=set)
    
    # 策略行为
    default_action: SecurityAction = SecurityAction.ALLOW
    violation_action: SecurityAction = SecurityAction.DENY


@dataclass
class SecurityContext:
    """安全上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_origin: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 权限信息
    user_permissions: Set[str] = field(default_factory=set)
    role: str = "user"
    trust_level: float = 0.5  # 0.0 - 1.0
    
    # 会话信息
    session_duration: timedelta = field(default_factory=timedelta)
    previous_actions: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """风险评估"""
    tool_name: str
    risk_level: float  # 0.0 - 1.0
    risk_factors: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)
    assessment_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityViolation:
    """安全违规"""
    violation_id: str
    tool_call: ToolCall
    policy_violated: str
    violation_type: str
    severity: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: SecurityContext = field(default_factory=SecurityContext)
    action_taken: SecurityAction = SecurityAction.DENY


class RiskAnalyzer:
    """风险分析器"""
    
    def __init__(self):
        # 工具风险数据库
        self.tool_risk_profiles = {
            "file_system": {
                "base_risk": 0.6,
                "risk_factors": {
                    "write": 0.3,
                    "delete": 0.8,
                    "system_paths": 0.9
                }
            },
            "code_interpreter": {
                "base_risk": 0.8,
                "risk_factors": {
                    "system_commands": 1.0,
                    "network_access": 0.7,
                    "file_access": 0.5
                }
            },
            "web_search": {
                "base_risk": 0.2,
                "risk_factors": {
                    "data_collection": 0.3
                }
            },
            "knowledge_base": {
                "base_risk": 0.1,
                "risk_factors": {
                    "write_operations": 0.4
                }
            }
        }
        
        # 风险阈值
        self.risk_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.9
        }
    
    def assess_tool_risk(self, tool_call: ToolCall, 
                        context: SecurityContext) -> RiskAssessment:
        """评估工具调用风险"""
        
        tool_profile = self.tool_risk_profiles.get(tool_call.tool_name, {})
        base_risk = tool_profile.get("base_risk", 0.5)
        
        risk_factors = []
        risk_adjustments = 0.0
        
        # 1. 基于工具参数的风险评估
        if tool_call.input_data:
            param_risk = self._assess_parameter_risk(tool_call, tool_profile)
            risk_adjustments += param_risk["adjustment"]
            risk_factors.extend(param_risk["factors"])
        
        # 2. 基于用户上下文的风险评估
        context_risk = self._assess_context_risk(context)
        risk_adjustments += context_risk["adjustment"]
        risk_factors.extend(context_risk["factors"])
        
        # 3. 基于历史行为的风险评估
        behavior_risk = self._assess_behavior_risk(context)
        risk_adjustments += behavior_risk["adjustment"]
        risk_factors.extend(behavior_risk["factors"])
        
        # 计算最终风险分数
        final_risk = min(1.0, max(0.0, base_risk + risk_adjustments))
        
        # 生成缓解建议
        mitigation_suggestions = self._generate_mitigation_suggestions(
            tool_call, final_risk, risk_factors
        )
        
        return RiskAssessment(
            tool_name=tool_call.tool_name,
            risk_level=final_risk,
            risk_factors=risk_factors,
            mitigation_suggestions=mitigation_suggestions
        )
    
    def _assess_parameter_risk(self, tool_call: ToolCall, 
                              tool_profile: Dict[str, Any]) -> Dict[str, Any]:
        """评估参数风险"""
        
        risk_factors = tool_profile.get("risk_factors", {})
        adjustment = 0.0
        factors = []
        
        for param, value in tool_call.input_data.items():
            if param in risk_factors:
                adjustment += risk_factors[param]
                factors.append(f"Parameter {param} increases risk")
            
            # 特殊参数检查
            if param == "path" and isinstance(value, str):
                if any(dangerous in value.lower() for dangerous in ["/system", "/windows", "c:\\"]):
                    adjustment += 0.4
                    factors.append("System path access detected")
            
            if param == "code" and isinstance(value, str):
                if any(dangerous in value.lower() for dangerous in ["import os", "subprocess", "eval"]):
                    adjustment += 0.3
                    factors.append("Potentially dangerous code detected")
        
        return {"adjustment": adjustment, "factors": factors}
    
    def _assess_context_risk(self, context: SecurityContext) -> Dict[str, Any]:
        """评估上下文风险"""
        
        adjustment = 0.0
        factors = []
        
        # 信任级别影响
        if context.trust_level < 0.3:
            adjustment += 0.2
            factors.append("Low user trust level")
        elif context.trust_level < 0.6:
            adjustment += 0.1
            factors.append("Medium user trust level")
        
        # 会话持续时间影响
        if context.session_duration > timedelta(hours=2):
            adjustment += 0.1
            factors.append("Long session duration")
        
        # 角色权限影响
        if context.role == "guest":
            adjustment += 0.3
            factors.append("Guest user role")
        elif context.role == "user":
            adjustment += 0.1
            factors.append("Regular user role")
        
        return {"adjustment": adjustment, "factors": factors}
    
    def _assess_behavior_risk(self, context: SecurityContext) -> Dict[str, Any]:
        """评估行为风险"""
        
        adjustment = 0.0
        factors = []
        
        # 检查最近的行为模式
        recent_actions = context.previous_actions[-10:]  # 最近10个动作
        
        # 频繁的高风险操作
        high_risk_actions = [action for action in recent_actions 
                           if any(risk_term in action for risk_term in ["delete", "execute", "system"])]
        
        if len(high_risk_actions) > 3:
            adjustment += 0.2
            factors.append("Frequent high-risk operations")
        
        # 异常行为模式检测
        if len(recent_actions) > 5:
            unique_actions = len(set(recent_actions))
            if unique_actions / len(recent_actions) < 0.3:  # 重复性太高
                adjustment += 0.1
                factors.append("Repetitive behavior pattern")
        
        return {"adjustment": adjustment, "factors": factors}
    
    def _generate_mitigation_suggestions(self, tool_call: ToolCall, 
                                       risk_level: float,
                                       risk_factors: List[str]) -> List[str]:
        """生成缓解建议"""
        
        suggestions = []
        
        if risk_level > self.risk_thresholds["high"]:
            suggestions.append("Consider requiring administrator approval")
            suggestions.append("Enable detailed logging for this operation")
            suggestions.append("Run in sandboxed environment")
        elif risk_level > self.risk_thresholds["medium"]:
            suggestions.append("Enable additional monitoring")
            suggestions.append("Require user confirmation")
        elif risk_level > self.risk_thresholds["low"]:
            suggestions.append("Log operation for audit trail")
        
        # 基于特定风险因素的建议
        for factor in risk_factors:
            if "system path" in factor.lower():
                suggestions.append("Restrict access to system directories")
            elif "dangerous code" in factor.lower():
                suggestions.append("Use code analysis tools before execution")
            elif "low trust" in factor.lower():
                suggestions.append("Increase authentication requirements")
        
        return list(set(suggestions))  # 去重


class PolicyEngine:
    """策略引擎"""
    
    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {}
        self.policy_cache: Dict[str, Dict[str, Any]] = {}
        
        # 加载默认策略
        self._load_default_policies()
    
    def _load_default_policies(self):
        """加载默认安全策略"""
        
        # 文件系统安全策略
        file_system_policy = SecurityPolicy(
            name="file_system_security",
            description="文件系统操作安全策略",
            rules=[
                {
                    "condition": {"tool_name": "file_system", "action": "delete"},
                    "action": SecurityAction.REQUIRE_APPROVAL,
                    "reason": "Delete operations require approval"
                },
                {
                    "condition": {"tool_name": "file_system", "path_contains": "/system"},
                    "action": SecurityAction.DENY,
                    "reason": "System path access denied"
                }
            ],
            applicable_tools={"file_system"}
        )
        
        # 代码执行安全策略
        code_execution_policy = SecurityPolicy(
            name="code_execution_security",
            description="代码执行安全策略",
            rules=[
                {
                    "condition": {"tool_name": "code_interpreter", "code_contains": ["os.", "subprocess"]},
                    "action": SecurityAction.SANDBOX,
                    "reason": "System calls require sandboxing"
                },
                {
                    "condition": {"tool_name": "code_interpreter", "language": "bash"},
                    "action": SecurityAction.REQUIRE_APPROVAL,
                    "reason": "Shell execution requires approval"
                }
            ],
            applicable_tools={"code_interpreter"}
        )
        
        # 用户权限策略
        user_permission_policy = SecurityPolicy(
            name="user_permission_control",
            description="用户权限控制策略",
            rules=[
                {
                    "condition": {"user_role": "guest"},
                    "action": SecurityAction.DENY,
                    "applicable_tools": {"file_system", "code_interpreter"},
                    "reason": "Guest users cannot access sensitive tools"
                },
                {
                    "condition": {"trust_level": {"<": 0.3}},
                    "action": SecurityAction.REQUIRE_APPROVAL,
                    "reason": "Low trust users require approval"
                }
            ]
        )
        
        self.add_policy(file_system_policy)
        self.add_policy(code_execution_policy)
        self.add_policy(user_permission_policy)
    
    def add_policy(self, policy: SecurityPolicy):
        """添加安全策略"""
        self.policies[policy.name] = policy
        
        # 清除相关缓存
        self.policy_cache.clear()
    
    def remove_policy(self, policy_name: str) -> bool:
        """移除安全策略"""
        if policy_name in self.policies:
            del self.policies[policy_name]
            self.policy_cache.clear()
            return True
        return False
    
    def evaluate_policies(self, tool_call: ToolCall, 
                         context: SecurityContext) -> Dict[str, Any]:
        """评估安全策略"""
        
        # 生成缓存键
        cache_key = self._generate_cache_key(tool_call, context)
        if cache_key in self.policy_cache:
            return self.policy_cache[cache_key]
        
        evaluation_result = {
            "final_action": SecurityAction.ALLOW,
            "applicable_policies": [],
            "violations": [],
            "warnings": [],
            "requirements": []
        }
        
        # 按优先级排序策略
        sorted_policies = sorted(
            self.policies.values(),
            key=lambda p: p.priority,
            reverse=True
        )
        
        for policy in sorted_policies:
            if not policy.enabled:
                continue
            
            # 检查策略是否适用
            if not self._is_policy_applicable(policy, tool_call, context):
                continue
            
            evaluation_result["applicable_policies"].append(policy.name)
            
            # 评估策略规则
            policy_result = self._evaluate_policy_rules(policy, tool_call, context)
            
            # 合并结果
            if policy_result["action"] == SecurityAction.DENY:
                evaluation_result["final_action"] = SecurityAction.DENY
                evaluation_result["violations"].append({
                    "policy": policy.name,
                    "reason": policy_result["reason"]
                })
                break  # DENY是最高优先级，直接退出
            elif policy_result["action"] == SecurityAction.REQUIRE_APPROVAL:
                if evaluation_result["final_action"] != SecurityAction.DENY:
                    evaluation_result["final_action"] = SecurityAction.REQUIRE_APPROVAL
                evaluation_result["requirements"].append({
                    "policy": policy.name,
                    "reason": policy_result["reason"]
                })
            elif policy_result["action"] == SecurityAction.WARN:
                evaluation_result["warnings"].append({
                    "policy": policy.name,
                    "reason": policy_result["reason"]
                })
            elif policy_result["action"] == SecurityAction.SANDBOX:
                if evaluation_result["final_action"] not in [SecurityAction.DENY, SecurityAction.REQUIRE_APPROVAL]:
                    evaluation_result["final_action"] = SecurityAction.SANDBOX
                evaluation_result["requirements"].append({
                    "policy": policy.name,
                    "reason": policy_result["reason"],
                    "requirement": "sandbox"
                })
        
        # 缓存结果
        self.policy_cache[cache_key] = evaluation_result
        
        return evaluation_result
    
    def _is_policy_applicable(self, policy: SecurityPolicy, 
                            tool_call: ToolCall, context: SecurityContext) -> bool:
        """检查策略是否适用"""
        
        # 检查工具适用性
        if policy.applicable_tools and tool_call.tool_name not in policy.applicable_tools:
            return False
        
        # 检查用户适用性
        if policy.applicable_users and context.user_id not in policy.applicable_users:
            return False
        
        return True
    
    def _evaluate_policy_rules(self, policy: SecurityPolicy, 
                             tool_call: ToolCall, context: SecurityContext) -> Dict[str, Any]:
        """评估策略规则"""
        
        for rule in policy.rules:
            condition = rule.get("condition", {})
            
            # 评估条件
            if self._evaluate_condition(condition, tool_call, context):
                return {
                    "action": rule.get("action", policy.default_action),
                    "reason": rule.get("reason", "Policy rule matched")
                }
        
        return {
            "action": policy.default_action,
            "reason": "Default policy action"
        }
    
    def _evaluate_condition(self, condition: Dict[str, Any], 
                          tool_call: ToolCall, context: SecurityContext) -> bool:
        """评估条件"""
        
        for key, value in condition.items():
            if key == "tool_name":
                if tool_call.tool_name != value:
                    return False
            elif key == "action":
                if tool_call.input_data.get("action") != value:
                    return False
            elif key == "path_contains":
                path = tool_call.input_data.get("path", "")
                if value not in path:
                    return False
            elif key == "code_contains":
                code = tool_call.input_data.get("code", "")
                if isinstance(value, list):
                    if not any(term in code for term in value):
                        return False
                else:
                    if value not in code:
                        return False
            elif key == "user_role":
                if context.role != value:
                    return False
            elif key == "trust_level":
                if isinstance(value, dict):
                    for op, threshold in value.items():
                        if op == "<" and context.trust_level >= threshold:
                            return False
                        elif op == ">" and context.trust_level <= threshold:
                            return False
                        elif op == "==" and context.trust_level != threshold:
                            return False
                else:
                    if context.trust_level != value:
                        return False
        
        return True
    
    def _generate_cache_key(self, tool_call: ToolCall, context: SecurityContext) -> str:
        """生成缓存键"""
        
        # 创建一个包含关键信息的字符串
        key_data = f"{tool_call.tool_name}:{tool_call.safety_level.value}:{context.role}:{context.trust_level}"
        
        # 添加重要的输入参数
        for key, value in sorted(tool_call.input_data.items()):
            if key in ["action", "path", "language"]:  # 只包含安全相关的参数
                key_data += f":{key}={value}"
        
        # 生成哈希
        return hashlib.md5(key_data.encode()).hexdigest()[:16]


class ToolSafetyManager:
    """工具安全管理器"""
    
    def __init__(self):
        self.risk_analyzer = RiskAnalyzer()
        self.policy_engine = PolicyEngine()
        
        # 安全违规记录
        self.violations: List[SecurityViolation] = []
        self.violation_thresholds = {
            "user_violation_limit": 5,  # 用户违规次数限制
            "session_violation_limit": 3,  # 会话违规次数限制
            "time_window_minutes": 60  # 违规时间窗口
        }
        
        # 安全统计
        self.security_stats = {
            "total_validations": 0,
            "allowed_calls": 0,
            "denied_calls": 0,
            "approval_required_calls": 0,
            "sandboxed_calls": 0,
            "violations_detected": 0
        }
    
    async def validate_tool_call(self, tool_call: ToolCall,
                                context: Optional[SecurityContext] = None) -> Dict[str, Any]:
        """验证工具调用安全性"""
        
        self.security_stats["total_validations"] += 1
        
        if context is None:
            context = SecurityContext()
        
        validation_result = {
            "allowed": True,
            "action": SecurityAction.ALLOW,
            "reason": "No security concerns detected",
            "risk_assessment": None,
            "policy_evaluation": None,
            "requirements": [],
            "warnings": []
        }
        
        try:
            # 1. 风险评估
            risk_assessment = self.risk_analyzer.assess_tool_risk(tool_call, context)
            validation_result["risk_assessment"] = risk_assessment
            
            # 2. 策略评估
            policy_evaluation = self.policy_engine.evaluate_policies(tool_call, context)
            validation_result["policy_evaluation"] = policy_evaluation
            
            # 3. 违规历史检查
            violation_check = self._check_violation_history(context)
            
            # 4. 最终决策
            final_action = self._make_final_decision(
                risk_assessment, policy_evaluation, violation_check
            )
            
            validation_result["action"] = final_action
            validation_result["allowed"] = (final_action != SecurityAction.DENY)
            
            # 5. 收集要求和警告
            if policy_evaluation["requirements"]:
                validation_result["requirements"] = policy_evaluation["requirements"]
            
            if policy_evaluation["warnings"]:
                validation_result["warnings"] = policy_evaluation["warnings"]
            
            # 6. 记录违规（如果有）
            if not validation_result["allowed"]:
                self._record_violation(tool_call, context, policy_evaluation, final_action)
            
            # 7. 更新统计
            self._update_security_stats(final_action)
            
            return validation_result
            
        except Exception as e:
            validation_result.update({
                "allowed": False,
                "action": SecurityAction.DENY,
                "reason": f"Security validation error: {str(e)}",
                "error": str(e)
            })
            
            self.security_stats["denied_calls"] += 1
            return validation_result
    
    def _check_violation_history(self, context: SecurityContext) -> Dict[str, Any]:
        """检查违规历史"""
        
        now = datetime.now()
        time_window = timedelta(minutes=self.violation_thresholds["time_window_minutes"])
        recent_violations = [
            v for v in self.violations
            if v.timestamp > (now - time_window)
        ]
        
        # 按用户统计
        user_violations = [
            v for v in recent_violations
            if v.context.user_id == context.user_id
        ] if context.user_id else []
        
        # 按会话统计
        session_violations = [
            v for v in recent_violations
            if v.context.session_id == context.session_id
        ] if context.session_id else []
        
        return {
            "total_recent_violations": len(recent_violations),
            "user_violations": len(user_violations),
            "session_violations": len(session_violations),
            "exceeds_user_limit": len(user_violations) >= self.violation_thresholds["user_violation_limit"],
            "exceeds_session_limit": len(session_violations) >= self.violation_thresholds["session_violation_limit"]
        }
    
    def _make_final_decision(self, risk_assessment: RiskAssessment,
                           policy_evaluation: Dict[str, Any],
                           violation_check: Dict[str, Any]) -> SecurityAction:
        """做出最终安全决策"""
        
        # 策略评估的结果具有最高优先级
        policy_action = policy_evaluation["final_action"]
        
        # 违规历史检查
        if violation_check["exceeds_user_limit"] or violation_check["exceeds_session_limit"]:
            return SecurityAction.DENY
        
        # 风险级别检查
        if risk_assessment.risk_level > 0.9:
            if policy_action == SecurityAction.ALLOW:
                return SecurityAction.REQUIRE_APPROVAL
        elif risk_assessment.risk_level > 0.7:
            if policy_action == SecurityAction.ALLOW:
                return SecurityAction.WARN
        
        return policy_action
    
    def _record_violation(self, tool_call: ToolCall, context: SecurityContext,
                         policy_evaluation: Dict[str, Any], action: SecurityAction):
        """记录安全违规"""
        
        violation_id = f"violation_{int(time.time())}_{len(self.violations)}"
        
        # 确定违规类型和严重性
        violation_type = "policy_violation"
        severity = "medium"
        
        if action == SecurityAction.DENY:
            severity = "high"
        
        if policy_evaluation["violations"]:
            violation_type = "policy_denial"
            severity = "high"
        
        violation = SecurityViolation(
            violation_id=violation_id,
            tool_call=tool_call,
            policy_violated=policy_evaluation["applicable_policies"][0] if policy_evaluation["applicable_policies"] else "unknown",
            violation_type=violation_type,
            severity=severity,
            context=context,
            action_taken=action
        )
        
        self.violations.append(violation)
        
        # 限制违规记录数量
        if len(self.violations) > 1000:
            self.violations = self.violations[-1000:]
        
        self.security_stats["violations_detected"] += 1
    
    def _update_security_stats(self, action: SecurityAction):
        """更新安全统计"""
        
        if action == SecurityAction.ALLOW:
            self.security_stats["allowed_calls"] += 1
        elif action == SecurityAction.DENY:
            self.security_stats["denied_calls"] += 1
        elif action == SecurityAction.REQUIRE_APPROVAL:
            self.security_stats["approval_required_calls"] += 1
        elif action == SecurityAction.SANDBOX:
            self.security_stats["sandboxed_calls"] += 1
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        
        total_calls = self.security_stats["total_validations"]
        
        return {
            "security_stats": self.security_stats,
            "approval_rate": (
                self.security_stats["allowed_calls"] / total_calls
            ) if total_calls > 0 else 0,
            "denial_rate": (
                self.security_stats["denied_calls"] / total_calls
            ) if total_calls > 0 else 0,
            "recent_violations": len(self.violations[-50:]),  # 最近50个违规
            "active_policies": len(self.policy_engine.policies),
            "cache_size": len(self.policy_engine.policy_cache)
        }
    
    def get_violation_report(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取违规报告"""
        
        recent_violations = self.violations[-limit:]
        
        return [
            {
                "violation_id": v.violation_id,
                "tool_name": v.tool_call.tool_name,
                "policy_violated": v.policy_violated,
                "violation_type": v.violation_type,
                "severity": v.severity,
                "timestamp": v.timestamp.isoformat(),
                "user_id": v.context.user_id,
                "session_id": v.context.session_id,
                "action_taken": v.action_taken.value
            }
            for v in recent_violations
        ]
    
    def add_security_policy(self, policy: SecurityPolicy) -> bool:
        """添加安全策略"""
        try:
            self.policy_engine.add_policy(policy)
            return True
        except Exception:
            return False
    
    def remove_security_policy(self, policy_name: str) -> bool:
        """移除安全策略"""
        return self.policy_engine.remove_policy(policy_name)
    
    def update_risk_profile(self, tool_name: str, risk_profile: Dict[str, Any]):
        """更新工具风险配置"""
        self.risk_analyzer.tool_risk_profiles[tool_name] = risk_profile