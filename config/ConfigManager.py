#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ./config/ConfigManager.py

"""
Konfigurationshanterare för LLM-baserad Produktinformationsextraktor

Denna klass hanterar konfigurationen för hela applikationen inklusive:
1. Inläsning av konfigurationsfiler (YAML/JSON)
2. Validering av konfigurationsvärden
3. Tillhandahåller en enkel åtkomst till konfigurationsvärden
4. Dynamisk uppdatering av konfiguration
5. Fallback till standardvärden när konfiguration saknas
"""

import os
import sys
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

# Standardkonfigurationen som används om ingen annan konfiguration anges
DEFAULT_CONFIG = {
    "general": {
        "data_dir": "./data",
        "output_dir": "./output",
        "log_dir": "./logs",
        "max_workers": 4,
        "debug_mode": False,
        "visualization": {
            "enabled": True,
            "colors": {
                "prompt": "blue",
                "llm_response": "green",
                "workflow": "cyan",
                "report": "magenta",
                "error": "red",
                "warning": "yellow",
                "retry": "bright_red"
            }
        }
    },
    "llm": {
        "provider": "ollama",
        "base_url": "http://localhost:11434/api",
        "model": "llama3",
        "max_tokens": 2048,
        "temperature": 0.1,
        "timeout": 60,
        "max_retries": 3,
        "retry_delay": 2,
        "context_size": 20000,
        "fallback_provider": "lmstudio",
        "fallback_base_url": "http://localhost:1234/v1"
    },
    "extraction": {
        "compatibility": {
            "enabled": True,
            "threshold": 0.7,
            "max_context_length": 150,
            "required_fields": ["relation_type", "related_product", "context"],
            "extra_context_enabled": True,
            "extra_context_size": 3  # Meningar före/efter
        },
        "technical": {
            "enabled": True,
            "threshold": 0.7,
            "max_context_length": 150,
            "required_fields": ["category", "name", "raw_value"],
            "unit_normalization": True
        },
        "chunk_size": 15000,  # Tecken per del
        "chunk_overlap": 2000,  # Överlappning mellan delar
        "max_file_size": 5000000  # Max 5MB per fil
    },
    "workflow": {
        "queue_size": 1000,
        "batch_size": 10,
        "timeout": 3600,  # 1 timme max per batch
        "priority_levels": 3,
        "throttling": {
            "enabled": True,
            "requests_per_minute": 30
        }
    },
    "reporting": {
        "live_updates": True,
        "update_interval": 5,  # Sekunder
        "detailed_metrics": True,
        "save_formats": ["json", "markdown", "csv"],
        "notification": {
            "enabled": False,
            "email": "",
            "slack_webhook": ""
        }
    },
    "providers": {
        "ollama": {
            "base_url": "http://localhost:11434/api",
            "models": ["llama3", "mistral", "vicuna"],
            "api_parameters": {
                "generate_endpoint": "/generate",
                "response_key": "response"
            }
        },
        "lmstudio": {
            "base_url": "http://localhost:1234/v1",
            "models": ["local-model"],
            "api_parameters": {
                "generate_endpoint": "/completions",
                "response_key": "choices[0].text"
            }
        },
        "oobabooga": {
            "base_url": "http://localhost:5000/v1",
            "models": ["local-model"],
            "api_parameters": {
                "generate_endpoint": "/completions",
                "response_key": "choices[0].text"
            }
        }
    }
}


@dataclass
class ValidationError:
    """Klass för att representera validationsfel i konfigurationen"""
    path: str
    message: str
    value: Any = None


class ConfigManager:
    """Hanterare för applikationskonfiguration"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None,
                 env_prefix: str = "LLMEXTRACT_"):
        """
        Initialiserar konfigurationshanteraren
        
        Args:
            config_path: Sökväg till konfigurationsfil (YAML/JSON)
            env_prefix: Prefix för miljövariabler som kan åsidosätta konfigurationen
        """
        self.logger = logging.getLogger(__name__)
        self.config = DEFAULT_CONFIG.copy()
        self.env_prefix = env_prefix
        self.validation_errors = []
        
        # Ladda konfigurationsfil om angiven
        if config_path:
            self.load_config(config_path)
            
        # Åsidosätt med miljövariabler
        self._override_from_env()
        
        # Validera konfigurationen
        self.validate()
        
        # Logga validationsfel
        if self.validation_errors:
            self.logger.warning(f"Konfigurationsvalidering resulterade i {len(self.validation_errors)} fel:")
            for error in self.validation_errors:
                self.logger.warning(f"  - {error.path}: {error.message}")
    
    def load_config(self, config_path: Union[str, Path]) -> bool:
        """
        Laddar konfiguration från fil
        
        Args:
            config_path: Sökväg till konfigurationsfil (YAML/JSON)
            
        Returns:
            bool: True om lyckad, False annars
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            self.logger.error(f"Konfigurationsfil hittades inte: {config_path}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    loaded_config = yaml.safe_load(f)
                elif config_path.suffix == '.json':
                    loaded_config = json.load(f)
                else:
                    self.logger.error(f"Okänd konfigurationsfiltyp: {config_path.suffix}")
                    return False
            
            # Uppdatera konfigurationen rekursivt
            self._update_dict_recursive(self.config, loaded_config)
            self.logger.info(f"Konfiguration laddad från {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fel vid inläsning av konfigurationsfil {config_path}: {str(e)}")
            return False
    
    def _update_dict_recursive(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Uppdaterar målordboken rekursivt med värden från källordboken
        
        Args:
            target: Målordboken att uppdatera
            source: Källordboken med nya värden
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_dict_recursive(target[key], value)
            else:
                target[key] = value
    
    def _override_from_env(self) -> None:
        """Åsidosätter konfigurationsvärden med motsvarande miljövariabler"""
        for env_name, env_value in os.environ.items():
            if not env_name.startswith(self.env_prefix):
                continue
                
            # Ta bort prefixet och dela upp resten i delar
            config_path = env_name[len(self.env_prefix):].lower().split('_')
            
            # Navigera genom konfigurationen
            current = self.config
            for part in config_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Sätt värdet med lämplig typkonvertering
            last_key = config_path[-1]
            if env_value.lower() in ['true', 'yes', '1']:
                current[last_key] = True
            elif env_value.lower() in ['false', 'no', '0']:
                current[last_key] = False
            elif env_value.isdigit():
                current[last_key] = int(env_value)
            elif env_value.replace('.', '', 1).isdigit() and env_value.count('.') <= 1:
                current[last_key] = float(env_value)
            else:
                current[last_key] = env_value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Hämtar ett konfigurationsvärde från angiven sökväg
        
        Args:
            key_path: Sökväg till konfigurationsvärdet (t.ex. "llm.model")
            default: Standardvärde att returnera om värdet inte finns
            
        Returns:
            Konfigurationsvärdet eller standardvärdet
        """
        parts = key_path.split('.')
        current = self.config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Sätter ett konfigurationsvärde på angiven sökväg
        
        Args:
            key_path: Sökväg till konfigurationsvärdet (t.ex. "llm.model")
            value: Värdet att sätta
        """
        parts = key_path.split('.')
        current = self.config
        
        # Navigera till det sista segmentet
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Sätt värdet
        current[parts[-1]] = value
    
    def validate(self) -> List[ValidationError]:
        """
        Validerar konfigurationen
        
        Returns:
            Lista med valideringsfel
        """
        self.validation_errors = []
        
        # Kontrollera LLM-konfiguration
        if not self.get("llm.provider"):
            self._add_validation_error("llm.provider", "Ingen LLM-leverantör angiven")
        
        provider = self.get("llm.provider")
        if provider and provider not in self.get("providers", {}):
            self._add_validation_error("llm.provider", f"Okänd LLM-leverantör: {provider}")
        
        # Kontrollera att baskonfiguration finns
        required_paths = [
            "general.data_dir", 
            "general.output_dir",
            "llm.model",
            "llm.max_tokens",
            "extraction.chunk_size"
        ]
        
        for path in required_paths:
            if self.get(path) is None:
                self._add_validation_error(path, f"Saknar obligatoriskt konfigurationsvärde")
        
        # Validera numeriska värden
        numeric_ranges = {
            "llm.max_tokens": (1, 32000),
            "llm.temperature": (0.0, 1.0),
            "llm.timeout": (1, 3600),
            "llm.max_retries": (0, 10),
            "workflow.queue_size": (1, 10000),
            "extraction.chunk_size": (1000, 50000)
        }
        
        for path, (min_val, max_val) in numeric_ranges.items():
            value = self.get(path)
            if value is not None:
                try:
                    num_value = float(value)
                    if num_value < min_val or num_value > max_val:
                        self._add_validation_error(
                            path, 
                            f"Värdet {num_value} är utanför tillåtet intervall [{min_val}, {max_val}]",
                            value
                        )
                except (ValueError, TypeError):
                    self._add_validation_error(
                        path, 
                        f"Värdet {value} är inte ett giltigt nummer",
                        value
                    )
        
        # Validera sökvägar
        path_keys = ["general.data_dir", "general.output_dir", "general.log_dir"]
        for path_key in path_keys:
            dir_path = self.get(path_key)
            if dir_path:
                try:
                    Path(dir_path)
                except Exception:
                    self._add_validation_error(
                        path_key,
                        f"Ogiltig sökväg: {dir_path}",
                        dir_path
                    )
        
        return self.validation_errors
    
    def _add_validation_error(self, path: str, message: str, value: Any = None) -> None:
        """
        Lägger till ett valideringsfel
        
        Args:
            path: Sökvägen till det konfigurationsvärde som orsakade felet
            message: Felmeddelande
            value: Det värde som orsakade felet
        """
        self.validation_errors.append(ValidationError(path=path, message=message, value=value))
    
    def ensure_directories(self) -> None:
        """Skapar alla nödvändiga kataloger som anges i konfigurationen"""
        directories = [
            self.get("general.data_dir"),
            self.get("general.output_dir"),
            self.get("general.log_dir")
        ]
        
        for dir_path in directories:
            if dir_path:
                try:
                    Path(dir_path).mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Skapade katalog: {dir_path}")
                except Exception as e:
                    self.logger.error(f"Kunde inte skapa katalog {dir_path}: {str(e)}")
    
    def save_config(self, file_path: Union[str, Path]) -> bool:
        """
        Sparar den nuvarande konfigurationen till fil
        
        Args:
            file_path: Sökväg till filen där konfigurationen ska sparas
            
        Returns:
            bool: True om lyckad, False annars
        """
        file_path = Path(file_path)
        
        try:
            # Skapa föräldrakataloger om de inte finns
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
                elif file_path.suffix == '.json':
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                else:
                    self.logger.error(f"Okänd filtyp för konfiguration: {file_path.suffix}")
                    return False
            
            self.logger.info(f"Konfiguration sparad till {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fel vid sparande av konfiguration till {file_path}: {str(e)}")
            return False
    
    def print_config(self, section: Optional[str] = None) -> None:
        """
        Skriver ut konfigurationen till konsolen
        
        Args:
            section: Specifik sektion att skriva ut, eller None för att skriva ut allt
        """
        if section:
            config_part = self.get(section, {})
            print(f"Konfiguration för {section}:")
            print(json.dumps(config_part, ensure_ascii=False, indent=2))
        else:
            print("Fullständig konfiguration:")
            print(json.dumps(self.config, ensure_ascii=False, indent=2))




