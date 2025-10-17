"""US7: Dynamic System Reminders

Provides contextual hints and reminders to agents based on runtime state.

Examples:
- "Warning: Memory usage is high (15,234 tokens). Consider using more concise responses."
- "Note: 3 stale todos detected. Consider cleaning up completed items."
- "Tip: Multiple file writes detected. Use batch operations for efficiency."
"""

from __future__ import annotations

from typing import List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Reminder:
    """A system reminder."""
    category: str  # "memory", "performance", "todos", "errors"
    severity: str  # "info", "warning", "critical"
    message: str
    metadata: dict


class ReminderRule:
    """Base class for reminder rules."""

    def __init__(self, category: str, severity: str = "info"):
        self.category = category
        self.severity = severity

    def check(self, context: dict) -> Optional[Reminder]:
        """Check if reminder should be triggered.

        Args:
            context: Runtime context dict

        Returns:
            Reminder if triggered, None otherwise
        """
        raise NotImplementedError


class HighMemoryRule(ReminderRule):
    """Remind when memory usage is high."""

    def __init__(self, threshold_tokens: int = 14000):
        super().__init__("memory", "warning")
        self.threshold_tokens = threshold_tokens

    def check(self, context: dict) -> Optional[Reminder]:
        current_tokens = context.get("current_tokens", 0)
        max_tokens = context.get("max_tokens", 16000)

        if current_tokens > self.threshold_tokens:
            percentage = (current_tokens / max_tokens) * 100
            return Reminder(
                category=self.category,
                severity=self.severity,
                message=f"Memory usage is high ({current_tokens:,} tokens, {percentage:.1f}%). Consider using more concise responses or compressing context.",
                metadata={
                    "current_tokens": current_tokens,
                    "max_tokens": max_tokens,
                    "percentage": percentage,
                }
            )
        return None


class StaleTodosRule(ReminderRule):
    """Remind about stale todos."""

    def __init__(self, stale_threshold_hours: int = 24):
        super().__init__("todos", "info")
        self.stale_threshold = timedelta(hours=stale_threshold_hours)

    def check(self, context: dict) -> Optional[Reminder]:
        todos = context.get("todos", [])
        now = datetime.now()

        # Count stale completed todos
        stale_count = 0
        for todo in todos:
            if todo.get("status") == "completed":
                completed_at = todo.get("completed_at")
                if completed_at and isinstance(completed_at, datetime):
                    if now - completed_at > self.stale_threshold:
                        stale_count += 1

        if stale_count > 0:
            return Reminder(
                category=self.category,
                severity=self.severity,
                message=f"{stale_count} stale todo(s) detected (completed >24h ago). Consider cleaning up.",
                metadata={"stale_count": stale_count}
            )
        return None


class HighErrorRateRule(ReminderRule):
    """Remind when error rate is high."""

    def __init__(self, threshold_percentage: float = 20.0):
        super().__init__("errors", "warning")
        self.threshold_percentage = threshold_percentage

    def check(self, context: dict) -> Optional[Reminder]:
        metrics = context.get("metrics", {})
        total_ops = metrics.get("total_operations", 0)
        errors = metrics.get("total_errors", 0)

        if total_ops > 0:
            error_rate = (errors / total_ops) * 100
            if error_rate > self.threshold_percentage:
                return Reminder(
                    category=self.category,
                    severity="critical" if error_rate > 50 else "warning",
                    message=f"High error rate detected: {errors}/{total_ops} operations failed ({error_rate:.1f}%). Check logs for details.",
                    metadata={
                        "error_rate": error_rate,
                        "errors": errors,
                        "total_ops": total_ops,
                    }
                )
        return None


class FrequentCompressionRule(ReminderRule):
    """Remind when compression happens too frequently."""

    def __init__(self, threshold_count: int = 5):
        super().__init__("performance", "info")
        self.threshold_count = threshold_count

    def check(self, context: dict) -> Optional[Reminder]:
        metrics = context.get("metrics", {})
        compressions = metrics.get("compressions", 0)

        if compressions >= self.threshold_count:
            return Reminder(
                category=self.category,
                severity=self.severity,
                message=f"Context compressed {compressions} times. Consider increasing max_context_tokens or using shorter prompts.",
                metadata={"compression_count": compressions}
            )
        return None


class SystemReminderManager:
    """Manages system reminders and dynamic hint injection.

    Example:
        manager = SystemReminderManager()
        manager.add_rule(HighMemoryRule())
        manager.add_rule(HighErrorRateRule())

        # Check for reminders
        context = {
            "current_tokens": 15000,
            "max_tokens": 16000,
            "metrics": {"total_errors": 5, "total_operations": 10}
        }

        reminders = manager.check_all(context)
        if reminders:
            print(manager.format_reminders(reminders))
    """

    def __init__(self):
        """Initialize reminder manager."""
        self.rules: List[ReminderRule] = []
        self._default_rules()

    def _default_rules(self):
        """Add default reminder rules."""
        self.add_rule(HighMemoryRule(threshold_tokens=14000))
        self.add_rule(HighErrorRateRule(threshold_percentage=20.0))
        self.add_rule(FrequentCompressionRule(threshold_count=5))
        # StaleTodosRule disabled by default (requires todo tracking)

    def add_rule(self, rule: ReminderRule) -> None:
        """Add a reminder rule.

        Args:
            rule: ReminderRule instance
        """
        self.rules.append(rule)

    def remove_rule(self, category: str) -> None:
        """Remove all rules for a category.

        Args:
            category: Category to remove
        """
        self.rules = [r for r in self.rules if r.category != category]

    def check_all(self, context: dict) -> List[Reminder]:
        """Check all rules and return triggered reminders.

        Args:
            context: Runtime context

        Returns:
            List of triggered reminders
        """
        reminders = []
        for rule in self.rules:
            try:
                reminder = rule.check(context)
                if reminder:
                    reminders.append(reminder)
            except Exception:
                # Don't fail if a rule raises
                pass

        return reminders

    def format_reminders(self, reminders: List[Reminder]) -> str:
        """Format reminders as human-readable text.

        Args:
            reminders: List of reminders

        Returns:
            Formatted reminder text
        """
        if not reminders:
            return ""

        lines = ["=== System Reminders ==="]

        # Group by severity
        critical = [r for r in reminders if r.severity == "critical"]
        warnings = [r for r in reminders if r.severity == "warning"]
        info = [r for r in reminders if r.severity == "info"]

        for severity_list, prefix in [
            (critical, "🚨 CRITICAL"),
            (warnings, "⚠️  WARNING"),
            (info, "ℹ️  INFO"),
        ]:
            for reminder in severity_list:
                lines.append(f"{prefix}: {reminder.message}")

        return "\n".join(lines)

    def inject_into_context(
        self,
        context: dict,
        existing_system_prompt: str = ""
    ) -> str:
        """Check reminders and inject into system prompt.

        Args:
            context: Runtime context
            existing_system_prompt: Existing system prompt

        Returns:
            System prompt with reminders injected
        """
        reminders = self.check_all(context)

        if not reminders:
            return existing_system_prompt

        reminder_text = self.format_reminders(reminders)

        # Inject at end of system prompt
        if existing_system_prompt:
            return f"{existing_system_prompt}\n\n{reminder_text}"
        else:
            return reminder_text


# Global instance
_default_manager = SystemReminderManager()


def get_reminder_manager() -> SystemReminderManager:
    """Get the global reminder manager."""
    return _default_manager
