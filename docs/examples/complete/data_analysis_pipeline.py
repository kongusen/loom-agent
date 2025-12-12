"""
Data Analysis Pipeline with Crew - loom-agent v0.1.1

Demonstrates:
- Multi-agent collaboration using Crew
- Sequential task dependencies
- Role specialization
- Streaming progress updates
- Shared state management

Usage:
    python data_analysis_pipeline.py data.csv --output report.md
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from loom import agent
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode
from loom.builtin.tools import ReadFileTool, WriteFileTool
from loom.builtin.llms import OpenAILLM
from loom.core.events import AgentEventType


class DataAnalysisPipeline:
    """Multi-agent data analysis pipeline using Crew.

    Roles:
    - Data Collector: Load and inspect data
    - Data Cleaner: Validate and clean data
    - Data Analyst: Extract insights and patterns
    - Report Writer: Generate final report
    """

    def __init__(self, data_file: str, output_file: str, verbose: bool = True):
        """Initialize pipeline.

        Args:
            data_file: Input data file (CSV)
            output_file: Output report file (Markdown)
            verbose: Show streaming progress
        """
        self.data_file = Path(data_file)
        self.output_file = Path(output_file)
        self.verbose = verbose

        # Shared LLM for all agents
        self.llm = OpenAILLM(model="gpt-4")

        # Define specialized roles
        self.roles = [
            Role(
                name="data_collector",
                goal="Load and inspect the data file",
                backstory="You are an expert at reading and understanding data files. "
                         "You can quickly identify file formats, column names, and basic statistics.",
                tools=[ReadFileTool()],
                allow_delegation=True
            ),
            Role(
                name="data_cleaner",
                goal="Clean and validate data quality",
                backstory="You are a data quality expert. You identify missing values, "
                         "outliers, inconsistencies, and data type issues.",
                tools=[ReadFileTool()],
                allow_delegation=False
            ),
            Role(
                name="data_analyst",
                goal="Analyze data and extract insights",
                backstory="You are a senior data analyst. You find patterns, correlations, "
                         "trends, and actionable insights in data.",
                tools=[],
                allow_delegation=False
            ),
            Role(
                name="report_writer",
                goal="Generate comprehensive analysis report",
                backstory="You are a technical writer who creates clear, well-structured "
                         "reports with visualizations and recommendations.",
                tools=[WriteFileTool()],
                allow_delegation=False
            )
        ]

        # Create crew
        self.crew = Crew(
            roles=self.roles,
            llm=self.llm,
            process=OrchestrationMode.SEQUENTIAL,
            verbose=self.verbose
        )

    def _create_tasks(self) -> List[Task]:
        """Create task dependency graph."""
        tasks = [
            Task(
                id="collect",
                description=f"Load and inspect the data file: {self.data_file}. "
                           f"Report: file format, columns, row count, data types.",
                expected_output="Data summary with column names, types, and basic statistics",
                assigned_role="data_collector",
                dependencies=[]
            ),
            Task(
                id="clean",
                description="Analyze data quality. Identify: missing values, outliers, "
                           "duplicates, type inconsistencies. Suggest cleaning steps.",
                expected_output="Data quality report with issues and recommendations",
                assigned_role="data_cleaner",
                dependencies=["collect"]
            ),
            Task(
                id="analyze",
                description="Perform statistical analysis. Find: patterns, correlations, "
                           "trends, anomalies. Extract key insights.",
                expected_output="Analysis findings with statistics and insights",
                assigned_role="data_analyst",
                dependencies=["clean"]
            ),
            Task(
                id="report",
                description=f"Write comprehensive analysis report to {self.output_file}. "
                           f"Include: executive summary, data quality findings, key insights, "
                           f"visualizations (ASCII tables), recommendations.",
                expected_output="Markdown report saved to file",
                assigned_role="report_writer",
                dependencies=["analyze"]
            )
        ]
        return tasks

    async def run(self) -> Dict:
        """Execute the full pipeline with streaming.

        Returns:
            Pipeline execution results
        """
        # Create orchestration plan
        tasks = self._create_tasks()
        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.SEQUENTIAL
        )

        if self.verbose:
            print(f"🚀 Starting Data Analysis Pipeline")
            print(f"📂 Input: {self.data_file}")
            print(f"📄 Output: {self.output_file}")
            print(f"👥 Roles: {len(self.roles)}")
            print(f"📋 Tasks: {len(tasks)}\n")

        # Execute with streaming
        task_results = {}

        async for event in self.crew.kickoff_stream(plan):
            if event.type == AgentEventType.CREW_TASK_START:
                task_id = event.metadata.get('task_id', 'unknown')
                role = event.metadata.get('assigned_role', 'unknown')
                print(f"\n🔹 Task: {task_id} (Role: {role})")

            elif event.type == AgentEventType.CREW_TASK_COMPLETE:
                task_id = event.metadata.get('task_id', 'unknown')
                result = event.metadata.get('result', '')
                task_results[task_id] = result
                print(f"✅ Task {task_id} complete")

            elif event.type == AgentEventType.LLM_DELTA and self.verbose:
                # Show agent thinking in real-time
                print(event.content, end="", flush=True)

            elif event.type == AgentEventType.CREW_COMPLETE:
                print(f"\n\n🎉 Pipeline complete!")

        return {
            "status": "completed",
            "data_file": str(self.data_file),
            "output_file": str(self.output_file),
            "tasks_completed": len(task_results),
            "results": task_results
        }


async def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Data Analysis Pipeline")
    parser.add_argument("data_file", help="Input CSV file")
    parser.add_argument("--output", default="analysis_report.md", help="Output report file")
    parser.add_argument("--quiet", action="store_true", help="Disable verbose output")
    args = parser.parse_args()

    # Create and run pipeline
    pipeline = DataAnalysisPipeline(
        data_file=args.data_file,
        output_file=args.output,
        verbose=not args.quiet
    )

    results = await pipeline.run()

    # Print summary
    print("\n" + "="*60)
    print(f"📊 Pipeline Summary")
    print("="*60)
    print(f"Status: {results['status']}")
    print(f"Tasks Completed: {results['tasks_completed']}")
    print(f"Report: {results['output_file']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
