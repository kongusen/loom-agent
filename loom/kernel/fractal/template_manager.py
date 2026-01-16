"""
Template Manager - Learn and manage optimal structure templates

Automatically learns structure templates from high-performing structures
and provides intelligent template matching and recommendations.
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from loom.config.fractal import NodeRole
from loom.kernel.optimization import StructureSnapshot

logger = logging.getLogger(__name__)


# ============================================================================
# Template Data Structures
# ============================================================================


@dataclass
class StructureTemplate:
    """Reusable structure template"""

    template_id: str
    name: str
    description: str
    task_categories: list[str]
    """Categories of tasks this template is good for"""

    # Topology specification
    topology_type: str  # "sequential", "parallel", "hierarchical", "mixed"
    node_specs: list[dict[str, Any]]
    """List of node specifications"""

    # Performance guarantees
    avg_fitness: float
    min_fitness: float
    success_rate: float
    usage_count: int = 0

    # Metadata
    created_from: str | None = None  # Source structure ID
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def matches_task(self, task_type: str, task_description: str | None = None) -> float:
        """
        Check if template matches a task

        Returns:
            Match score (0-1)
        """
        score = 0.0

        # Category matching
        task_type_lower = task_type.lower()
        for category in self.task_categories:
            if category.lower() in task_type_lower or task_type_lower in category.lower():
                score += 0.5

        # Tag matching
        if task_description:
            task_words = set(task_description.lower().split())
            tag_words = {word for tag in self.tags for word in tag.lower().split()}
            overlap = len(task_words & tag_words)
            if overlap > 0:
                score += min(0.3, overlap * 0.1)

        # Usage-based boost
        if self.usage_count > 10:
            score += 0.1
        elif self.usage_count > 5:
            score += 0.05

        return min(1.0, score)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "task_categories": self.task_categories,
            "topology_type": self.topology_type,
            "node_specs": self.node_specs,
            "performance": {
                "avg_fitness": self.avg_fitness,
                "min_fitness": self.min_fitness,
                "success_rate": self.success_rate,
                "usage_count": self.usage_count,
            },
            "metadata": {
                "created_from": self.created_from,
                "tags": self.tags,
                "confidence": self.confidence,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructureTemplate":
        """Create from dictionary"""
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            task_categories=data["task_categories"],
            topology_type=data["topology_type"],
            node_specs=data["node_specs"],
            avg_fitness=data["performance"]["avg_fitness"],
            min_fitness=data["performance"]["min_fitness"],
            success_rate=data["performance"]["success_rate"],
            usage_count=data["performance"]["usage_count"],
            created_from=data["metadata"].get("created_from"),
            tags=data["metadata"].get("tags", []),
            confidence=data["metadata"].get("confidence", 0.0),
        )


# ============================================================================
# Template Manager
# ============================================================================


class TemplateManager:
    """
    Manages structure templates

    Responsibilities:
    - Learn templates from high-performing structures
    - Store and retrieve templates
    - Match templates to tasks
    - Recommend optimal templates
    - Track template usage and performance
    """

    def __init__(self, min_fitness_for_template: float = 0.75, min_usage_for_template: int = 3):
        """
        Initialize template manager

        Args:
            min_fitness_for_template: Minimum fitness to create template
            min_usage_for_template: Minimum usage count to create template
        """
        self.min_fitness_for_template = min_fitness_for_template
        self.min_usage_for_template = min_usage_for_template

        # Template storage
        self.templates: dict[str, StructureTemplate] = {}

        # Category index for fast lookup
        self.category_index: dict[str, list[str]] = defaultdict(list)
        # Maps category -> list of template IDs

        # Performance tracking
        self.template_usage: dict[str, list[float]] = defaultdict(list)
        # Maps template_id -> list of fitness scores

    # ========================================================================
    # Template Learning
    # ========================================================================

    def learn_from_snapshots(
        self, snapshots: list[StructureSnapshot], task_type: str
    ) -> StructureTemplate | None:
        """
        Learn template from structure snapshots

        Args:
            snapshots: List of structure snapshots
            task_type: Type of task

        Returns:
            Learned template or None
        """
        # Filter high-performing snapshots
        good_snapshots = [s for s in snapshots if s.fitness_score >= self.min_fitness_for_template]

        if len(good_snapshots) < self.min_usage_for_template:
            logger.info(
                f"Not enough good snapshots for {task_type}: "
                f"{len(good_snapshots)} < {self.min_usage_for_template}"
            )
            return None

        # Extract common pattern
        template = self._extract_template_from_snapshots(good_snapshots, task_type)

        # Add to library
        self.add_template(template)

        logger.info(
            f"Learned template: {template.template_id} from {len(good_snapshots)} snapshots"
        )

        return template

    def _extract_template_from_snapshots(
        self, snapshots: list[StructureSnapshot], task_type: str
    ) -> StructureTemplate:
        """Extract template from snapshots"""
        import numpy as np

        # Aggregate statistics
        avg_fitness = float(np.mean([s.fitness_score for s in snapshots]))
        min_fitness = float(np.min([s.fitness_score for s in snapshots]))
        success_rate = float(np.mean([s.success_rate for s in snapshots]))

        # Determine topology type
        avg_depth = float(np.mean([s.max_depth for s in snapshots]))
        avg_branching = float(np.mean([s.avg_branching for s in snapshots]))

        if avg_branching < 1.5 and avg_depth >= 2:
            topology_type = "sequential"
        elif avg_branching >= 3 and avg_depth <= 2:
            topology_type = "parallel"
        elif avg_depth >= 3:
            topology_type = "hierarchical"
        else:
            topology_type = "mixed"

        # Determine common roles
        role_distribution = self._aggregate_role_distribution(snapshots)

        # Create node specs based on common pattern
        node_specs = self._create_node_specs(
            topology_type,
            int(np.median([s.total_nodes for s in snapshots])),
            int(avg_depth),
            role_distribution,
        )

        # Extract tags from task type
        tags = self._extract_tags(task_type)

        template = StructureTemplate(
            template_id=f"tmpl_{task_type}_{len(self.templates)}",
            name=f"{topology_type.capitalize()} Template for {task_type}",
            description=f"Learned from {len(snapshots)} high-performing structures",
            task_categories=[task_type],
            topology_type=topology_type,
            node_specs=node_specs,
            avg_fitness=avg_fitness,
            min_fitness=min_fitness,
            success_rate=success_rate,
            usage_count=len(snapshots),
            created_from=snapshots[0].structure_id,
            tags=tags,
            confidence=min(1.0, len(snapshots) / 20),
        )

        return template

    def _aggregate_role_distribution(self, snapshots: list[StructureSnapshot]) -> dict[str, float]:
        """Aggregate role distribution across snapshots"""
        role_counts = defaultdict(list)

        for snapshot in snapshots:
            total = snapshot.total_nodes
            for role, count in snapshot.node_roles.items():
                role_counts[role].append(count / total if total > 0 else 0)

        # Return median proportions
        return {role: float(np.median(proportions)) for role, proportions in role_counts.items()}

    def _create_node_specs(
        self,
        topology_type: str,
        total_nodes: int,
        max_depth: int,
        role_distribution: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Create node specifications"""
        specs = []

        # Root node
        specs.append(
            {"role": NodeRole.COORDINATOR.value, "depth": 0, "description": "Root coordinator"}
        )

        # Add children based on topology
        if topology_type == "sequential":
            # Chain of executors
            for i in range(1, total_nodes - 1):
                specs.append(
                    {
                        "role": NodeRole.EXECUTOR.value,
                        "depth": min(i, max_depth),
                        "description": f"Sequential step {i}",
                    }
                )

            # Final aggregator
            specs.append(
                {
                    "role": NodeRole.AGGREGATOR.value,
                    "depth": max_depth,
                    "description": "Final aggregator",
                }
            )

        elif topology_type == "parallel":
            # Multiple specialists in parallel
            num_specialists = total_nodes - 2  # Minus root and aggregator
            for i in range(num_specialists):
                specs.append(
                    {
                        "role": NodeRole.SPECIALIST.value,
                        "depth": 1,
                        "description": f"Parallel specialist {i+1}",
                    }
                )

            # Aggregator
            specs.append(
                {"role": NodeRole.AGGREGATOR.value, "depth": 1, "description": "Result aggregator"}
            )

        else:
            # Generic based on role distribution
            remaining = total_nodes - 1
            for role, proportion in role_distribution.items():
                count = max(1, int(remaining * proportion))
                for i in range(count):
                    specs.append(
                        {
                            "role": role,
                            "depth": min(i // 2 + 1, max_depth),
                            "description": f"{role} node",
                        }
                    )

        return specs[:total_nodes]  # Ensure we don't exceed total

    def _extract_tags(self, task_type: str) -> list[str]:
        """Extract tags from task type"""
        # Simple word extraction
        words = re.findall(r"\w+", task_type.lower())
        # Filter out common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        tags = [w for w in words if w not in common_words and len(w) > 2]
        return tags[:5]  # Limit to 5 tags

    # ========================================================================
    # Template Management
    # ========================================================================

    def add_template(self, template: StructureTemplate):
        """Add template to library"""
        self.templates[template.template_id] = template

        # Update category index
        for category in template.task_categories:
            self.category_index[category.lower()].append(template.template_id)

        logger.info(f"Added template: {template.template_id}")

    def get_template(self, template_id: str) -> StructureTemplate | None:
        """Get template by ID"""
        return self.templates.get(template_id)

    def remove_template(self, template_id: str):
        """Remove template from library"""
        template = self.templates.pop(template_id, None)

        if template:
            # Update index
            for category in template.task_categories:
                if template_id in self.category_index[category.lower()]:
                    self.category_index[category.lower()].remove(template_id)

            logger.info(f"Removed template: {template_id}")

    # ========================================================================
    # Template Matching and Recommendation
    # ========================================================================

    def find_templates(
        self,
        task_type: str,
        task_description: str | None = None,
        min_match_score: float = 0.3,
        limit: int = 5,
    ) -> list[tuple[StructureTemplate, float]]:
        """
        Find matching templates for a task

        Args:
            task_type: Type of task
            task_description: Optional task description
            min_match_score: Minimum match score
            limit: Maximum number of templates to return

        Returns:
            List of (template, match_score) tuples
        """
        # Get candidates from category index
        candidates = set()
        task_type_lower = task_type.lower()

        for category, template_ids in self.category_index.items():
            if category in task_type_lower or task_type_lower in category:
                candidates.update(template_ids)

        # If no category matches, check all templates
        if not candidates:
            candidates = set(self.templates.keys())

        # Score each candidate
        matches = []
        for template_id in candidates:
            template = self.templates[template_id]
            score = template.matches_task(task_type, task_description)

            if score >= min_match_score:
                matches.append((template, score))

        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:limit]

    def recommend_template(
        self,
        task_type: str,
        task_description: str | None = None,
        current_fitness: float | None = None,
    ) -> StructureTemplate | None:
        """
        Recommend best template for a task

        Args:
            task_type: Type of task
            task_description: Optional task description
            current_fitness: Current fitness (if any)

        Returns:
            Best template or None
        """
        matches = self.find_templates(task_type, task_description)

        if not matches:
            return None

        # If current fitness provided, filter for improvements
        if current_fitness is not None:
            matches = [
                (t, s)
                for t, s in matches
                if t.avg_fitness > current_fitness + 0.05  # 5% improvement
            ]

        if not matches:
            return None

        # Return best match weighted by both match score and performance
        best = max(matches, key=lambda x: x[1] * x[0].avg_fitness * x[0].confidence)

        return best[0]

    # ========================================================================
    # Usage Tracking
    # ========================================================================

    def record_usage(self, template_id: str, fitness: float):
        """Record template usage"""
        if template_id in self.templates:
            self.templates[template_id].usage_count += 1
            self.template_usage[template_id].append(fitness)

            logger.debug(f"Recorded usage for {template_id}: fitness={fitness:.2f}")

    def get_template_stats(self, template_id: str) -> dict[str, Any]:
        """Get usage statistics for template"""
        template = self.templates.get(template_id)
        usage_scores = self.template_usage.get(template_id, [])

        if not template:
            return {}

        import numpy as np

        return {
            "template_id": template_id,
            "usage_count": template.usage_count,
            "avg_fitness": template.avg_fitness,
            "recent_avg_fitness": float(np.mean(usage_scores[-10:])) if usage_scores else 0.0,
            "fitness_std": float(np.std(usage_scores)) if usage_scores else 0.0,
            "confidence": template.confidence,
        }

    # ========================================================================
    # Persistence
    # ========================================================================

    def save(self, filepath: str):
        """Save templates to file"""
        data = {
            "templates": {k: v.to_dict() for k, v in self.templates.items()},
            "usage": dict(self.template_usage.items()),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.templates)} templates to {filepath}")

    def load(self, filepath: str):
        """Load templates from file"""
        with open(filepath) as f:
            data = json.load(f)

        self.templates = {k: StructureTemplate.from_dict(v) for k, v in data["templates"].items()}

        self.template_usage = defaultdict(list, data["usage"])

        # Rebuild category index
        self.category_index.clear()
        for template_id, template in self.templates.items():
            for category in template.task_categories:
                self.category_index[category.lower()].append(template_id)

        logger.info(f"Loaded {len(self.templates)} templates from {filepath}")

    # ========================================================================
    # Reporting
    # ========================================================================

    def get_summary(self) -> dict[str, Any]:
        """Get summary of template library"""
        import numpy as np

        if not self.templates:
            return {"total_templates": 0, "total_usage": 0}

        total_usage = sum(t.usage_count for t in self.templates.values())
        avg_fitness = np.mean([t.avg_fitness for t in self.templates.values()])

        # Group by topology type
        topology_counts: defaultdict[str, int] = defaultdict(int)
        for template in self.templates.values():
            topology_counts[template.topology_type] += 1

        return {
            "total_templates": len(self.templates),
            "total_usage": total_usage,
            "avg_template_fitness": float(avg_fitness),
            "topology_types": dict(topology_counts),
            "categories_covered": len(self.category_index),
        }
