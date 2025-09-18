"""
配置管理器

提供配置的加载、验证、保存和管理功能
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path

from .models import LexiconAgentConfig, LLMConfig, ContextConfig, ToolConfig
from .validator import ConfigValidator
from .loader import ConfigLoader


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.validator = ConfigValidator()
        self.loader = ConfigLoader()
        self._config: Optional[LexiconAgentConfig] = None
        
    def load_config(self, 
                   config_source: Optional[Union[str, Dict[str, Any], LexiconAgentConfig]] = None) -> LexiconAgentConfig:
        """
        加载配置
        
        Args:
            config_source: 配置源（文件路径、字典或配置对象）
            
        Returns:
            LexiconAgentConfig: 配置对象
        """
        if config_source is None:
            # 尝试从默认位置加载
            config_source = self._find_default_config()
        
        if isinstance(config_source, LexiconAgentConfig):
            config = config_source
        elif isinstance(config_source, dict):
            config = LexiconAgentConfig.from_dict(config_source)
        elif isinstance(config_source, str):
            config = self.loader.load_from_file(config_source)
        else:
            # 使用默认配置
            config = LexiconAgentConfig()
        
        # 验证配置
        validation_result = self.validator.validate(config)
        if not validation_result.is_valid:
            raise ValueError(f"配置验证失败: {validation_result.errors}")
        
        self._config = config
        return config
    
    def save_config(self, 
                   config: LexiconAgentConfig, 
                   file_path: str, 
                   format: str = "yaml") -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置对象
            file_path: 文件路径
            format: 文件格式 ("json" 或 "yaml")
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = config.model_dump()
        
        if format.lower() == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        elif format.lower() == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def update_llm_config(self, **kwargs) -> LLMConfig:
        """
        更新LLM配置
        
        Args:
            **kwargs: LLM配置参数
            
        Returns:
            LLMConfig: 更新后的LLM配置
        """
        if self._config is None:
            raise ValueError("请先加载配置")
        
        # 创建新的LLM配置
        current_llm_dict = self._config.llm.model_dump()
        current_llm_dict.update(kwargs)
        
        new_llm_config = LLMConfig(**current_llm_dict)
        self._config.llm = new_llm_config
        
        return new_llm_config
    
    def update_context_config(self, **kwargs) -> ContextConfig:
        """
        更新上下文配置
        
        Args:
            **kwargs: 上下文配置参数
            
        Returns:
            ContextConfig: 更新后的上下文配置
        """
        if self._config is None:
            raise ValueError("请先加载配置")
        
        current_context_dict = self._config.context.model_dump()
        current_context_dict.update(kwargs)
        
        new_context_config = ContextConfig(**current_context_dict)
        self._config.context = new_context_config
        
        return new_context_config
    
    def update_tool_config(self, **kwargs) -> ToolConfig:
        """
        更新工具配置
        
        Args:
            **kwargs: 工具配置参数
            
        Returns:
            ToolConfig: 更新后的工具配置
        """
        if self._config is None:
            raise ValueError("请先加载配置")
        
        current_tool_dict = self._config.tools.model_dump()
        current_tool_dict.update(kwargs)
        
        new_tool_config = ToolConfig(**current_tool_dict)
        self._config.tools = new_tool_config
        
        return new_tool_config
    
    def get_config(self) -> Optional[LexiconAgentConfig]:
        """获取当前配置"""
        return self._config
    
    def get_llm_config(self) -> Optional[LLMConfig]:
        """获取LLM配置"""
        return self._config.llm if self._config else None
    
    def get_context_config(self) -> Optional[ContextConfig]:
        """获取上下文配置"""
        return self._config.context if self._config else None
    
    def get_tool_config(self) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._config.tools if self._config else None
    
    def merge_configs(self, 
                     base_config: LexiconAgentConfig, 
                     override_config: Dict[str, Any]) -> LexiconAgentConfig:
        """
        合并配置
        
        Args:
            base_config: 基础配置
            override_config: 覆盖配置
            
        Returns:
            LexiconAgentConfig: 合并后的配置
        """
        base_dict = base_config.model_dump()
        merged_dict = self._deep_merge(base_dict, override_config)
        return LexiconAgentConfig.from_dict(merged_dict)
    
    def create_config_template(self, 
                             template_type: str = "default", 
                             output_path: Optional[str] = None) -> LexiconAgentConfig:
        """
        创建配置模板
        
        Args:
            template_type: 模板类型 ("default", "development", "production", "minimal")
            output_path: 输出路径（如果提供，会保存到文件）
            
        Returns:
            LexiconAgentConfig: 配置模板
        """
        from .models import (
            create_default_config, 
            create_development_config,
            create_production_config,
            create_minimal_config
        )
        
        template_map = {
            "default": create_default_config,
            "development": create_development_config,
            "production": create_production_config,
            "minimal": create_minimal_config
        }
        
        if template_type not in template_map:
            raise ValueError(f"不支持的模板类型: {template_type}")
        
        config = template_map[template_type]()
        
        if output_path:
            self.save_config(config, output_path)
        
        return config
    
    def _find_default_config(self) -> Optional[str]:
        """查找默认配置文件"""
        possible_paths = [
            "lexicon_agent.yaml",
            "lexicon_agent.yml", 
            "lexicon_agent.json",
            "config/lexicon_agent.yaml",
            "config/lexicon_agent.yml",
            "config/lexicon_agent.json",
            os.path.expanduser("~/.lexicon_agent/config.yaml"),
            "/etc/lexicon_agent/config.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def export_config_schema(self, output_path: str) -> None:
        """导出配置架构"""
        schema = LexiconAgentConfig.schema()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
    
    def validate_config_file(self, file_path: str) -> bool:
        """验证配置文件"""
        try:
            config = self.loader.load_from_file(file_path)
            validation_result = self.validator.validate(config)
            return validation_result.is_valid
        except Exception:
            return False