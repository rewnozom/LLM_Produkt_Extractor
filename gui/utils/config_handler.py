#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/utils/config_handler.py

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from PySide6.QtCore import QSettings, QObject, Signal


class ConfigHandler(QObject):
    """
    Utility class for managing application configuration.
    
    Provides a unified interface for accessing and modifying configuration
    from different sources (YAML, JSON, QSettings) and propagating changes
    to the application.
    """
    
    # Signal emitted when configuration is changed
    config_changed = Signal(dict)
    
    def __init__(self, app_name: str = "ProductExtractor", config_dir: Optional[str] = None):
        """
        Initialize the configuration handler.
        
        Args:
            app_name: Name of the application (for QSettings)
            config_dir: Directory for config files, defaults to './config'
        """
        super().__init__()
        
        self.app_name = app_name
        self.config_dir = Path(config_dir) if config_dir else Path("./config")
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default config file paths
        self.default_yaml = self.config_dir / "config.yaml"
        self.default_json = self.config_dir / "config.json"
        
        # QSettings for user preferences
        self.settings = QSettings(self.app_name, "LLMProductTool")
        
        # Current configuration
        self._config = {}
        
        # Load configuration
        self.load_configuration()
    
    def load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from all available sources.
        
        Priority:
        1. QSettings (user preferences override)
        2. YAML/JSON config files
        3. Default settings
        
        Returns:
            Dict with merged configuration
        """
        # Start with default configuration
        config = self.get_default_config()
        
        # Try to load from config files
        if self.default_yaml.exists():
            yaml_config = self.load_yaml(self.default_yaml)
            if yaml_config:
                config.update(yaml_config)
        
        elif self.default_json.exists():
            json_config = self.load_json(self.default_json)
            if json_config:
                config.update(json_config)
        
        # Load user preferences from QSettings
        user_config = self.load_from_qsettings()
        if user_config:
            # Nested update to preserve structure
            self._deep_update(config, user_config)
        
        # Store current configuration
        self._config = config
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dict with the current configuration
        """
        return self._config
    
    def get(self, key_path: str, default=None) -> Any:
        """
        Get a configuration value using a dot-separated path.
        
        Args:
            key_path: Dot-separated path to the config value (e.g., 'general.output_dir')
            default: Default value to return if key doesn't exist
            
        Returns:
            Config value or default
        """
        if not key_path:
            return self._config
        
        current = self._config
        parts = key_path.split('.')
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using a dot-separated path.
        
        Args:
            key_path: Dot-separated path to the config value (e.g., 'general.output_dir')
            value: Value to set
        """
        if not key_path:
            return
        
        parts = key_path.split('.')
        current = self._config
        
        # Navigate to the correct location
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
        
        # Save the updated value to QSettings
        self._save_key_to_qsettings(key_path, value)
        
        # Emit signal to notify about the change
        self.config_changed.emit(self._config)
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update multiple configuration values at once.
        
        Args:
            config_dict: Dictionary with config values to update
        """
        self._deep_update(self._config, config_dict)
        
        # Save to QSettings
        self._save_dict_to_qsettings(config_dict)
        
        # Emit signal
        self.config_changed.emit(self._config)
    
    def save_configuration(self, file_path: Optional[Union[str, Path]] = None, format: str = "yaml") -> bool:
        """
        Save the current configuration to a file.
        
        Args:
            file_path: Path to save to, defaults to standard config file
            format: Format to save in ("yaml" or "json")
            
        Returns:
            True if saving was successful, False otherwise
        """
        if not file_path:
            file_path = self.default_yaml if format.lower() == "yaml" else self.default_json
        
        file_path = Path(file_path)
        
        try:
            # Create parent directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "yaml":
                return self.save_yaml(file_path, self._config)
            else:  # json
                return self.save_json(file_path, self._config)
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def load_yaml(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dict with loaded configuration or empty dict on error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except Exception as e:
            print(f"Error loading YAML configuration: {e}")
            return {}
    
    def save_yaml(self, file_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """
        Save configuration to a YAML file.
        
        Args:
            file_path: Path to the YAML file
            config: Configuration to save
            
        Returns:
            True if saving was successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving YAML configuration: {e}")
            return False
    
    def load_json(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dict with loaded configuration or empty dict on error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config if config else {}
        except Exception as e:
            print(f"Error loading JSON configuration: {e}")
            return {}
    
    def save_json(self, file_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """
        Save configuration to a JSON file.
        
        Args:
            file_path: Path to the JSON file
            config: Configuration to save
            
        Returns:
            True if saving was successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving JSON configuration: {e}")
            return False
    
    def load_from_qsettings(self) -> Dict[str, Any]:
        """
        Load configuration from QSettings.
        
        Returns:
            Dict with loaded configuration
        """
        config = {}
        
        # Get all top-level groups
        for top_group in self.settings.childGroups():
            config[top_group] = {}
            
            # Read keys in this group
            self.settings.beginGroup(top_group)
            
            for key in self.settings.childKeys():
                config[top_group][key] = self.settings.value(key)
            
            # Read subgroups (up to 1 level deep for now)
            for sub_group in self.settings.childGroups():
                config[top_group][sub_group] = {}
                
                self.settings.beginGroup(sub_group)
                for key in self.settings.childKeys():
                    config[top_group][sub_group][key] = self.settings.value(key)
                self.settings.endGroup()  # Exit sub_group
            
            self.settings.endGroup()  # Exit top_group
        
        return config
    
    def _save_key_to_qsettings(self, key_path: str, value: Any) -> None:
        """
        Save a single config value to QSettings.
        
        Args:
            key_path: Dot-separated path to the config value
            value: Value to save
        """
        parts = key_path.split('.')
        
        if len(parts) == 1:
            # Top-level key
            self.settings.setValue(parts[0], value)
        elif len(parts) == 2:
            # Group and key
            self.settings.beginGroup(parts[0])
            self.settings.setValue(parts[1], value)
            self.settings.endGroup()
        elif len(parts) == 3:
            # Group, subgroup, and key
            self.settings.beginGroup(parts[0])
            self.settings.beginGroup(parts[1])
            self.settings.setValue(parts[2], value)
            self.settings.endGroup()  # Exit subgroup
            self.settings.endGroup()  # Exit group
    
    def _save_dict_to_qsettings(self, config_dict: Dict[str, Any], prefix: str = "") -> None:
        """
        Recursively save a dictionary to QSettings.
        
        Args:
            config_dict: Dictionary to save
            prefix: Key prefix for recursion
        """
        for key, value in config_dict.items():
            key_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively save dict
                self._save_dict_to_qsettings(value, key_path)
            else:
                # Save value
                self._save_key_to_qsettings(key_path, value)
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively update a nested dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively update nested dictionaries
                self._deep_update(target[key], value)
            else:
                # Set or override value
                target[key] = value
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Dict with default configuration values
        """
        return {
            "general": {
                "output_dir": "./output",
                "file_filter": "*.md;*.txt",
                "auto_save": True,
                "auto_save_interval": 5,
                "load_last_project": True,
                "check_updates": True,
                "startup_tab": "Workflow"
            },
            "appearance": {
                "theme": "System",
                "accent_color": "#3b82f6",
                "ui_font": "",
                "code_font": "Consolas",
                "font_size": 11,
                "line_numbers": True,
                "syntax_highlighting": True,
                "word_wrap": True
            },
            "llm": {
                "provider": "ollama",
                "base_url": "http://localhost:11434/api",
                "model": "llama3",
                "api_key": "",
                "timeout": 60,
                "max_retries": 3,
                "temperature": 0.1,
                "max_tokens": 2048
            },
            "extraction": {
                "compatibility": {
                    "enabled": True,
                    "threshold": 0.7
                },
                "technical": {
                    "enabled": True,
                    "threshold": 0.7
                },
                "faq": {
                    "enabled": False
                },
                "chunk_size": 8000,
                "chunk_overlap": 1000
            },
            "workflow": {
                "batch_size": 10,
                "max_workers": 4
            },
            "cache": {
                "enabled": True,
                "directory": "./cache",
                "max_size": 1000,
                "expiry_days": 30
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
                "log_file": "./logs/app.log"
            },
            "debug": {
                "enabled": False,
                "console": False,
                "save_raw_responses": False
            }
        }
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self._config = self.get_default_config()
        
        # Clear QSettings
        self.settings.clear()
        
        # Emit signal
        self.config_changed.emit(self._config)