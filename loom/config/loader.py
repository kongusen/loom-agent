"""
配置加载器

从 YAML 文件加载配置并创建 Loom 应用。
"""

import yaml
from pathlib import Path
from typing import Dict, Any

from loom.config.models import LoomConfig, AgentConfig, CrewConfig
from loom.api.main import LoomApp
from loom.weave import create_agent
from loom.node.agent import AgentNode
from loom.node.crew import CrewNode


class ConfigLoader:
    """配置加载器"""

    def __init__(self):
        self.agents: Dict[str, AgentNode] = {}
        self.crews: Dict[str, CrewNode] = {}

    @staticmethod
    def load_yaml(path: str) -> LoomConfig:
        """
        从 YAML 文件加载配置。

        Args:
            path: YAML 文件路径

        Returns:
            解析后的配置对象
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return LoomConfig(**data)

    def _create_agent(self, config: AgentConfig, app: LoomApp) -> AgentNode:
        """
        根据配置创建 Agent。

        Args:
            config: Agent 配置
            app: LoomApp 实例

        Returns:
            创建的 AgentNode
        """
        # 如果指定了预构建类型
        if config.type:
            if config.type == "CoderAgent":
                from loom.stdlib.agents import CoderAgent
                base_dir = config.config.get("base_dir", ".") if config.config else "."
                return CoderAgent(config.name, base_dir=base_dir)
            elif config.type == "AnalystAgent":
                from loom.stdlib.agents import AnalystAgent
                return AnalystAgent(config.name)
            else:
                raise ValueError(f"未知的 Agent 类型: {config.type}")

        # 自定义 Agent
        agent = create_agent(config.name, role=config.role or "Assistant")

        # 注册技能
        if config.skills:
            for skill_name in config.skills:
                if skill_name == "calculator":
                    from loom.stdlib.skills import CalculatorSkill
                    CalculatorSkill().register(agent)
                elif skill_name == "filesystem":
                    from loom.stdlib.skills import FileSystemSkill
                    base_dir = config.config.get("base_dir", ".") if config.config else "."
                    FileSystemSkill(base_dir=base_dir).register(agent)

        return agent

    def _create_crew(self, config: CrewConfig) -> CrewNode:
        """
        根据配置创建 Crew。

        Args:
            config: Crew 配置

        Returns:
            创建的 CrewNode
        """
        # 如果指定了预构建类型
        if config.type:
            if config.type == "DebateCrew":
                from loom.stdlib.crews import DebateCrew
                topic = config.config.get("topic", "未指定主题") if config.config else "未指定主题"
                return DebateCrew(config.name, topic=topic)
            else:
                raise ValueError(f"未知的 Crew 类型: {config.type}")

        # 自定义 Crew
        from loom.weave import create_crew
        agent_list = [self.agents[name] for name in config.agents]
        return create_crew(config.name, agent_list)

    def from_config(self, config: LoomConfig) -> LoomApp:
        """
        从配置创建 LoomApp。

        Args:
            config: Loom 配置

        Returns:
            配置好的 LoomApp 实例
        """
        # 创建 App（带控制配置）
        control_config = {}
        if config.control:
            if config.control.budget:
                control_config["budget"] = config.control.budget
            if config.control.depth:
                control_config["depth"] = config.control.depth
            if config.control.hitl:
                control_config["hitl"] = config.control.hitl

        app = LoomApp(control_config=control_config if control_config else None)

        # 创建所有 Agent
        if config.agents:
            for agent_config in config.agents:
                agent = self._create_agent(agent_config, app)
                self.agents[agent_config.name] = agent

        # 创建所有 Crew
        if config.crews:
            for crew_config in config.crews:
                crew = self._create_crew(crew_config)
                self.crews[crew_config.name] = crew

        return app

    @classmethod
    def from_file(cls, path: str) -> tuple[LoomApp, Dict[str, AgentNode], Dict[str, CrewNode]]:
        """
        从 YAML 文件创建 LoomApp。

        Args:
            path: YAML 文件路径

        Returns:
            (app, agents, crews) 元组
        """
        config = cls.load_yaml(path)
        loader = cls()
        app = loader.from_config(config)
        return app, loader.agents, loader.crews

