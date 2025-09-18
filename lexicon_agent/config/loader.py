"""
配置加载器

支持从多种格式和来源加载配置
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from .models import LexiconAgentConfig


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        """初始化配置加载器"""
        pass
    
    def load_from_file(self, file_path: str) -> LexiconAgentConfig:
        """
        从文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            LexiconAgentConfig: 配置对象
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in ['.yaml', '.yml']:
            return self._load_yaml(file_path)
        elif file_extension == '.json':
            return self._load_json(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> LexiconAgentConfig:
        """
        从字典加载配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            LexiconAgentConfig: 配置对象
        """
        return LexiconAgentConfig.from_dict(config_dict)
    
    def load_from_env(self, prefix: str = "LEXICON_AGENT") -> Dict[str, Any]:
        """
        从环境变量加载配置
        
        Args:
            prefix: 环境变量前缀
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        config = {}
        
        # 扫描环境变量
        for key, value in os.environ.items():
            if key.startswith(prefix + "_"):
                # 移除前缀并转换为小写
                config_key = key[len(prefix) + 1:].lower()
                
                # 解析嵌套键
                keys = config_key.split("_")
                current = config
                
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # 尝试解析值类型
                current[keys[-1]] = self._parse_env_value(value)
        
        return config
    
    def load_from_multiple_sources(self, 
                                 file_path: Optional[str] = None,
                                 env_prefix: str = "LEXICON_AGENT",
                                 override_dict: Optional[Dict[str, Any]] = None) -> LexiconAgentConfig:
        """
        从多个来源加载配置（按优先级合并）
        
        Args:
            file_path: 配置文件路径
            env_prefix: 环境变量前缀
            override_dict: 覆盖配置字典
            
        Returns:
            LexiconAgentConfig: 合并后的配置对象
        """
        # 1. 从文件加载基础配置
        if file_path and os.path.exists(file_path):
            base_config = self.load_from_file(file_path).to_dict()
        else:
            base_config = LexiconAgentConfig().to_dict()
        
        # 2. 从环境变量加载配置并合并
        env_config = self.load_from_env(env_prefix)
        merged_config = self._deep_merge(base_config, env_config)
        
        # 3. 应用覆盖配置
        if override_dict:
            merged_config = self._deep_merge(merged_config, override_dict)
        
        return LexiconAgentConfig.from_dict(merged_config)
    
    def _load_yaml(self, file_path: str) -> LexiconAgentConfig:
        """加载YAML配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return LexiconAgentConfig.from_dict(data or {})
        except yaml.YAMLError as e:
            raise ValueError(f"YAML格式错误: {e}")
        except Exception as e:
            raise ValueError(f"加载YAML文件失败: {e}")
    
    def _load_json(self, file_path: str) -> LexiconAgentConfig:
        """加载JSON配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return LexiconAgentConfig.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {e}")
        except Exception as e:
            raise ValueError(f"加载JSON文件失败: {e}")
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值的类型"""
        # 尝试解析为布尔值
        if value.lower() in ['true', 'yes', '1', 'on']:
            return True
        elif value.lower() in ['false', 'no', '0', 'off']:
            return False
        
        # 尝试解析为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # 返回字符串
        return value
    
    def _deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result