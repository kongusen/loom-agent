"""
Complete Code Review Agent Example - loom-agent v0.1.1

Demonstrates:
- Real-world agent application
- Streaming execution with progress updates
- Tool integration (ReadFile, Glob, Grep)
- Structured result collection
- Error handling

Usage:
    python code_review_agent.py /path/to/project --verbose
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from loom import agent
from loom.builtin.tools import ReadFileTool, GlobTool, GrepTool
from loom.core.events import AgentEventType


@dataclass
class ReviewResult:
    """Code review findings"""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    files_reviewed: int = 0
    total_lines: int = 0
    summary: str = ""


class CodeReviewAgent:
    """Complete code review system with streaming support.

    Features:
    - Automatic file discovery
    - Pattern-based issue detection
    - Streaming progress updates (optional)
    - Structured result collection
    """

    def __init__(self, project_dir: str, verbose: bool = False):
        """Initialize code review agent.

        Args:
            project_dir: Path to project directory
            verbose: Enable real-time streaming output
        """
        self.project_dir = Path(project_dir)
        self.verbose = verbose
        self.results = ReviewResult()

        # Initialize agent with code review tools
        self.agent = agent(
            provider="openai",
            model="gpt-4",
            tools=[
                ReadFileTool(),
                GlobTool(),
                GrepTool()
            ],
            system_instructions=self._get_system_instructions(),
            max_iterations=30
        )

    def _get_system_instructions(self) -> str:
        """Get system instructions for code review."""
        return f"""You are an expert code reviewer. Your task is to review the codebase at {self.project_dir}.

Review Guidelines:
1. Find potential bugs, security issues, and performance problems
2. Check code style and best practices
3. Identify TODO comments and incomplete implementations
4. Suggest improvements for readability and maintainability

Available Tools:
- glob: Find files by pattern (e.g., "**/*.py")
- grep: Search for patterns in files
- read_file: Read file contents

Process:
1. Use glob to discover Python files
2. Use grep to find patterns (TODO, FIXME, XXX, security issues)
3. Read suspicious files for detailed review
4. Summarize findings with severity levels

Output Format:
## Issues Found
- [HIGH/MEDIUM/LOW] Description (file:line)

## Suggestions
- Description

## Summary
Overall code quality assessment
"""

    async def review(self) -> Dict:
        """Execute code review with optional streaming.

        Returns:
            Dictionary with review results
        """
        prompt = f"""Review the codebase at {self.project_dir}:

1. Find all Python files
2. Check for common issues:
   - TODO/FIXME comments
   - Security vulnerabilities (eval, exec, shell injection)
   - Exception handling issues
   - Potential bugs
3. Read key files for detailed review
4. Provide structured findings

Be thorough but concise."""

        if self.verbose:
            # Real-time streaming output
            print(f"🔍 Starting code review: {self.project_dir}\n")

            async for event in self.agent.execute(prompt):
                if event.type == AgentEventType.LLM_DELTA:
                    # Print LLM response in real-time
                    print(event.content, end="", flush=True)

                elif event.type == AgentEventType.TOOL_EXECUTION_START:
                    tool_name = event.metadata.get('tool_name', 'unknown')
                    print(f"\n🔧 Using tool: {tool_name}")

                elif event.type == AgentEventType.TOOL_RESULT:
                    # Track files reviewed
                    if event.tool_result and not event.tool_result.is_error:
                        self.results.files_reviewed += 1

                elif event.type == AgentEventType.ITERATION_START:
                    iteration = event.metadata.get('iteration', 0)
                    print(f"\n🔄 Iteration {iteration}")

                elif event.type == AgentEventType.AGENT_FINISH:
                    self.results.summary = event.content or ""
                    print(f"\n\n✅ Review complete!")

        else:
            # Simple mode - just get final result
            result = await self.agent.run(prompt)
            self.results.summary = result

        return {
            "files_reviewed": self.results.files_reviewed,
            "summary": self.results.summary,
            "project_dir": str(self.project_dir)
        }


async def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Code Review Agent")
    parser.add_argument("project_dir", help="Project directory to review")
    parser.add_argument("--verbose", action="store_true", help="Show streaming output")
    args = parser.parse_args()

    # Create and run reviewer
    reviewer = CodeReviewAgent(
        project_dir=args.project_dir,
        verbose=args.verbose
    )

    results = await reviewer.review()

    # Print summary
    print("\n" + "="*60)
    print(f"📊 Review Summary")
    print("="*60)
    print(f"Files Reviewed: {results['files_reviewed']}")
    print(f"Project: {results['project_dir']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
