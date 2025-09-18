#!/usr/bin/env python3
"""
Lexicon Agent Framework - Basic Usage Example

This example demonstrates the core functionality of the Lexicon Agent Framework,
including agent creation, tool usage, and orchestration.
"""

import asyncio
import os
import sys
sys.path.append('..')

from lexicon_agent.types import Agent, SessionState, ContextRequirements
from lexicon_agent.core.tools.registry import ToolRegistry
from lexicon_agent.core.orchestration.engine import OrchestrationEngine, UserInput, OrchestrationContext


async def example_1_basic_agent():
    """Example 1: Creating and using a basic agent"""
    print("🤖 Example 1: Basic Agent Creation")
    print("-" * 40)
    
    # Create an agent
    agent = Agent(
        agent_id="data_analyst_001",
        name="Data Analysis Agent",
        specialization="data_analysis",
        capabilities=["file_operations", "data_processing", "reporting"],
        status="available",
        configuration={"max_concurrent_tasks": 3}
    )
    
    print(f"✅ Created agent: {agent.name}")
    print(f"   Agent ID: {agent.agent_id}")
    print(f"   Specialization: {agent.specialization}")
    print(f"   Capabilities: {agent.capabilities}")
    print(f"   Status: {agent.status}")
    print()


async def example_2_tool_usage():
    """Example 2: Using built-in tools"""
    print("🔧 Example 2: Tool Usage")
    print("-" * 40)
    
    # Initialize tool registry
    tool_registry = ToolRegistry()
    
    # List available tools
    available_tools = tool_registry.list_tools()
    print(f"📋 Available tools: {available_tools}")
    print()
    
    # Example: File System Tool
    print("📁 File System Tool Example:")
    fs_tool = tool_registry.get_tool("file_system")
    
    # Create a test file
    write_result = await fs_tool.execute({
        "action": "write",
        "path": "example_data.txt",
        "content": "Hello from Lexicon Agent Framework!\nThis is a test file created by the framework."
    })
    
    if write_result.get("success"):
        print(f"   ✅ File created: {write_result['path']}")
        print(f"   📝 Bytes written: {write_result['bytes_written']}")
    
    # Read the file back
    read_result = await fs_tool.execute({
        "action": "read",
        "path": "example_data.txt"
    })
    
    if read_result.get("success"):
        print(f"   📖 File content: {read_result['content'][:50]}...")
        print(f"   📏 File size: {read_result['size']} bytes")
    
    print()
    
    # Example: Knowledge Base Tool
    print("📚 Knowledge Base Tool Example:")
    kb_tool = tool_registry.get_tool("knowledge_base")
    
    # Create a knowledge base
    kb_create_result = await kb_tool.execute({
        "action": "create",
        "kb_name": "example_kb",
        "description": "Example knowledge base for demonstration"
    })
    
    if kb_create_result.get("success"):
        print(f"   ✅ Knowledge base created: {kb_create_result['kb_name']}")
    
    # Add a document
    doc_add_result = await kb_tool.execute({
        "action": "add",
        "kb_name": "example_kb",
        "title": "Framework Overview",
        "text": "Lexicon Agent Framework is a powerful multi-agent orchestration system designed for building intelligent applications.",
        "metadata": {"category": "documentation", "importance": "high"}
    })
    
    if doc_add_result.get("success"):
        print(f"   📄 Document added: {doc_add_result['document_id']}")
        print(f"   📊 Word count: {doc_add_result['word_count']}")
    
    print()


async def example_3_orchestration():
    """Example 3: Agent orchestration"""
    print("🎭 Example 3: Agent Orchestration")
    print("-" * 40)
    
    # Create multiple agents with different specializations
    agents = [
        Agent(
            agent_id="analyst_001",
            name="Data Analyst",
            specialization="data_analysis",
            capabilities=["data_analysis", "file_operations"],
            status="available"
        ),
        Agent(
            agent_id="reporter_001", 
            name="Report Generator",
            specialization="documentation",
            capabilities=["content_creation", "reporting"],
            status="available"
        )
    ]
    
    print(f"👥 Created {len(agents)} specialized agents")
    for agent in agents:
        print(f"   - {agent.name} ({agent.specialization})")
    print()
    
    # Initialize orchestration engine
    engine = OrchestrationEngine()
    
    # Create a complex user input
    user_input = UserInput(
        message="Analyze the example data file and create a comprehensive report with insights and recommendations",
        context={
            "task_type": "data_analysis_and_reporting",
            "output_format": "detailed_report",
            "priority": "high"
        }
    )
    
    print(f"📝 User request: {user_input.message}")
    print(f"🎯 Task context: {user_input.context}")
    print()
    
    # Create orchestration context
    orchestration_context = OrchestrationContext(
        user_input=user_input,
        available_agents=agents,
        session_context={
            "session_id": "example_session_001",
            "user_preferences": {"detail_level": "comprehensive"}
        },
        constraints={
            "max_execution_time": 60,
            "resource_limit": "standard"
        }
    )
    
    # Execute orchestration
    print("🚀 Starting orchestration...")
    result = await engine.orchestrate(user_input, agents, orchestration_context)
    
    # Display results
    print("📊 Orchestration Results:")
    print(f"   ✅ Status: {result.orchestration_metadata.get('status')}")
    print(f"   👥 Participating agents: {len(result.participating_agents)}")
    print(f"   ⏱️  Execution time: {result.orchestration_metadata.get('execution_time', 0):.3f}s")
    print(f"   🎯 Strategy used: {result.orchestration_metadata.get('strategy_used', 'N/A')}")
    
    if result.primary_result:
        print(f"   📋 Result preview: {str(result.primary_result)[:100]}...")
    
    print()


async def cleanup_example():
    """Clean up example files"""
    print("🧹 Cleaning up example files...")
    
    try:
        # Remove test file
        if os.path.exists("example_data.txt"):
            os.remove("example_data.txt")
            print("   ✅ Removed example_data.txt")
        
        # Remove knowledge base directory (if exists)
        import shutil
        if os.path.exists("knowledge_bases"):
            shutil.rmtree("knowledge_bases")
            print("   ✅ Removed knowledge_bases directory")
            
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
    
    print()


async def main():
    """Run all examples"""
    print("🚀 Lexicon Agent Framework - Basic Usage Examples")
    print("=" * 60)
    print()
    
    try:
        # Run examples
        await example_1_basic_agent()
        await example_2_tool_usage()
        await example_3_orchestration()
        
        print("✅ All examples completed successfully!")
        print()
        
        # Clean up
        await cleanup_example()
        
        print("🎉 Basic usage demonstration complete!")
        print("📖 For more advanced usage, see FRAMEWORK_GUIDE.md")
        
    except Exception as e:
        print(f"❌ Error during example execution: {e}")
        print("🔍 Please check your environment and try again")


if __name__ == "__main__":
    asyncio.run(main())