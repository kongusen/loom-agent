"""
03_skills_system.py - Skills 系统

演示：
- FilesystemSkillLoader 加载 Skills
- SkillRegistry 管理 Skills
- Agent 集成 Skills
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from loom.agent import Agent
from loom.config.llm import LLMConfig
from loom.providers.llm import OpenAIProvider

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建 LLM Provider（从环境变量获取配置）
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 2. 获取 skills 目录路径
    skills_dir = Path(__file__).parent / "skills"

    # 3. 创建 Agent（使用 skills_dir 参数）
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个代码审查专家。",
        skills_dir=skills_dir,
        skills=["code-review"],  # 启用的 skills
        max_iterations=5,
    )

    # 4. 运行任务
    result = await agent.run("请审查这段代码: def add(a,b): return a+b")
    print(f"结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
