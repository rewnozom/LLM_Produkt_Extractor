#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PromptTemplate.py - Basklass för promptmallar med formatering och anpassningsmöjligheter

Denna modul innehåller basklassen PromptTemplate som används för att skapa, formatera och hantera
promptmallar för LLM-baserad informationsextraktion.

Egenskaper:
- Stöd för formatering med platshållare ({variable_name})
- Automatisk versionshantering och historik
- Möjlighet att lägga till exempel och kontext
- Spårning av användning för optimering
"""

import re
import string
import random
import hashlib
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import yaml
from pathlib import Path


class PromptTemplate:
    """
    Basklass för promptmallar som kan fyllas med variabler och anpassas.
    
    Egenskaper:
    - Stöd för formatering med platshållare ({variable_name})
    - Automatisk versionshantering och historik
    - Möjlighet att lägga till exempel och kontext
    - Spårning av användning för optimering
    """
    
    def __init__(self, template: str, name: str = None, description: str = None, 
                 version: str = "1.0", tags: List[str] = None):
        """
        Initierar promptmallen.
        
        Args:
            template: Mall med platshållare som {name}
            name: Namn på promptmallen
            description: Beskrivning av promptmallen
            version: Versionsstring
            tags: Lista med taggar för kategorisering
        """
        self.template = template
        self.name = name or f"prompt_{random.randint(1000, 9999)}"
        self.description = description or "En prompt för LLM-baserad extraktion"
        self.version = version
        self.tags = tags or []
        self.creation_time = datetime.now()
        self.last_modified = self.creation_time
        self.usage_count = 0
        self.usage_history = []
        self.success_rate = 1.0  # Andel lyckade anrop (1.0 = 100%)
        self.average_latency_ms = 0
        
        # Kontrollera om mallen har giltiga platshållare
        self._validate_template()
    
    def _validate_template(self) -> None:
        """
        Validerar att promptmallen har korrekt syntax för platshållare.
        Kastar ValueError om platshållare är ogiltiga.
        """
        # Hitta alla platshållare som {name}
        placeholders = re.findall(r'\{([^{}]*)\}', self.template)
        
        # Kontrollera att platshållarna är giltiga pythonidentifierare
        for placeholder in placeholders:
            if not placeholder.isidentifier() and placeholder != '':
                raise ValueError(f"Ogiltig platshållare: {{{placeholder}}}. Måste vara en giltig Python-identifierare.")
    
    def format(self, **kwargs) -> str:
        """
        Fyller mallen med värden och spårar användning.
        
        Args:
            **kwargs: Nyckelord att ersätta i mallen
            
        Returns:
            str: Den formaterade prompten
            
        Raises:
            ValueError: Om en nödvändig nyckel saknas
        """
        try:
            # Registrera tidpunkt innan formatering
            start_time = datetime.now()
            
            # Formatera mallen
            formatted = self.template.format(**kwargs)
            
            # Beräkna hash för denna specifika formatering
            format_hash = hashlib.md5(formatted.encode()).hexdigest()[:10]
            
            # Uppdatera användningsstatistik
            self.usage_count += 1
            self.usage_history.append({
                'timestamp': start_time.isoformat(),
                'format_hash': format_hash,
                'variables': list(kwargs.keys())
            })
            
            return formatted
            
        except KeyError as e:
            missing_key = str(e).strip("'")
            raise ValueError(f"Saknad nyckelvariabel i promptmallen: {missing_key}")
    
    def add_example(self, example: Union[str, Dict[str, str]]) -> 'PromptTemplate':
        """
        Lägger till ett exempel till promptmallen för few-shot learning.
        
        Args:
            example: Exemplet att lägga till, antingen som sträng eller dictionary
            
        Returns:
            PromptTemplate: Ny promptmall med det tillagda exemplet
        """
        # Skapa exempeltext baserat på indata
        if isinstance(example, dict):
            example_text = f"Input: {example.get('input', '')}\nOutput: {example.get('output', '')}"
        else:
            example_text = str(example)
        
        example_section = "\n\nHär är ett exempel:\n\n```\n{example}\n```"
        
        if "{example}" in self.template:
            # Mallen har redan en plats för exempel, ersätt bara värdet
            new_template = self.template.replace("{example}", example_text)
        else:
            # Lägg till exempel-sektionen i slutet av mallen
            new_template = self.template + example_section.format(example=example_text)
        
        # Skapa en ny promptmall med uppdaterad info
        new_prompt = PromptTemplate(
            template=new_template,
            name=self.name + "_with_example",
            description=self.description + " (med exempel)",
            version=f"{self.version}+ex",
            tags=self.tags + ["with_examples"]
        )
        
        return new_prompt
    
    def add_context(self, context: str) -> 'PromptTemplate':
        """
        Lägger till kontext till promptmallen för bättre förståelse.
        
        Args:
            context: Kontexten att lägga till
            
        Returns:
            PromptTemplate: Ny promptmall med den tillagda kontexten
        """
        context_section = "\n\nYtterligare kontext:\n\n{context}"
        
        if "{context}" in self.template:
            # Mallen har redan en plats för kontext, ersätt bara värdet
            new_template = self.template.replace("{context}", context)
        else:
            # Lägg till kontext-sektionen i början av mallen
            new_template = context_section.format(context=context) + "\n\n" + self.template
        
        # Skapa en ny promptmall med uppdaterad info
        new_prompt = PromptTemplate(
            template=new_template, 
            name=self.name + "_with_context",
            description=self.description + " (med kontext)",
            version=f"{self.version}+ctx",
            tags=self.tags + ["with_context"]
        )
        
        return new_prompt
    
    def with_instruction(self, instruction: str) -> 'PromptTemplate':
        """
        Lägger till en specifik instruktion i prompten.
        
        Args:
            instruction: Instruktionen att lägga till
            
        Returns:
            PromptTemplate: Ny promptmall med den tillagda instruktionen
        """
        instruction_text = f"\n\nVIKTIGT: {instruction}\n\n"
        
        # Hitta lämpligt ställe att lägga in instruktionen (efter inledning, före JSON-exempel)
        json_start = self.template.find("```json")
        
        if json_start > 0:
            # Lägg till instruktionen före JSON-exemplet
            parts = [self.template[:json_start], instruction_text, self.template[json_start:]]
            new_template = "".join(parts)
        else:
            # Lägg till i slutet av inledningen (första stycket)
            paragraphs = self.template.split("\n\n")
            if len(paragraphs) > 1:
                paragraphs[0] += instruction_text
                new_template = "\n\n".join(paragraphs)
            else:
                new_template = self.template + instruction_text
        
        # Skapa en ny promptmall med uppdaterad info
        new_prompt = PromptTemplate(
            template=new_template, 
            name=f"{self.name}_with_instruction",
            description=f"{self.description} (med extra instruktion)",
            version=f"{self.version}+instr",
            tags=self.tags + ["with_instruction"]
        )
        
        return new_prompt
    
    def update_success_rate(self, success: bool) -> None:
        """
        Uppdaterar framgångsfrekvensen baserat på ett användningsresultat.
        
        Args:
            success: Om användningen var framgångsrik
        """
        # Använd ett vägt glidande medelvärde
        weight = min(1.0, 10.0 / max(10.0, self.usage_count))
        
        # Uppdatera framgångsfrekvensen
        self.success_rate = (1 - weight) * self.success_rate + weight * (1.0 if success else 0.0)
    
    def update_latency(self, latency_ms: int) -> None:
        """
        Uppdaterar genomsnittlig svarstid baserat på en användning.
        
        Args:
            latency_ms: Svarstid i millisekunder
        """
        # Använd ett vägt glidande medelvärde
        weight = min(1.0, 10.0 / max(10.0, self.usage_count))
        
        # Uppdatera genomsnittlig svarstid
        self.average_latency_ms = (1 - weight) * self.average_latency_ms + weight * latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterar promptmallen till en ordbok för serialisering.
        
        Returns:
            Dict[str, Any]: Promptmallen som ordbok
        """
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "version": self.version,
            "tags": self.tags,
            "creation_time": self.creation_time.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms
        }
    
    def to_yaml(self) -> str:
        """
        Konverterar promptmallen till YAML-format.
        
        Returns:
            str: Promptmallen som YAML-sträng
        """
        data = self.to_dict()
        return yaml.dump(data, sort_keys=False, allow_unicode=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """
        Skapar en promptmall från en ordbok.
        
        Args:
            data: Ordbok med promptdata
            
        Returns:
            PromptTemplate: Den skapade promptmallen
        """
        template = cls(
            template=data["template"],
            name=data.get("name"),
            description=data.get("description"),
            version=data.get("version", "1.0"),
            tags=data.get("tags", [])
        )
        
        # Ställ in ytterligare attribut om de finns
        if "creation_time" in data:
            template.creation_time = datetime.fromisoformat(data["creation_time"])
        
        if "last_modified" in data:
            template.last_modified = datetime.fromisoformat(data["last_modified"])
        
        if "usage_count" in data:
            template.usage_count = data["usage_count"]
        
        if "success_rate" in data:
            template.success_rate = data["success_rate"]
        
        if "average_latency_ms" in data:
            template.average_latency_ms = data["average_latency_ms"]
        
        return template
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'PromptTemplate':
        """
        Skapar en promptmall från en YAML-sträng.
        
        Args:
            yaml_str: YAML-sträng med promptdata
            
        Returns:
            PromptTemplate: Den skapade promptmallen
        """
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    def save(self, directory: Union[str, Path]) -> Path:
        """
        Sparar promptmallen till fil.
        
        Args:
            directory: Katalog att spara till
            
        Returns:
            Path: Sökväg till den sparade filen
        """
        directory = Path(directory)
        directory.mkdir(exist_ok=True, parents=True)
        
        # Skapa filnamn baserat på namn och version
        safe_name = re.sub(r'[^\w\-_]', '_', self.name)
        filename = f"{safe_name}_v{self.version.replace('.', '_')}.yaml"
        file_path = directory / filename
        
        # Spara till YAML
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_yaml())
        
        return file_path
    
    @classmethod
    def load(cls, file_path: Union[str, Path]) -> 'PromptTemplate':
        """
        Laddar en promptmall från fil.
        
        Args:
            file_path: Sökväg till filen
            
        Returns:
            PromptTemplate: Den laddade promptmallen
            
        Raises:
            FileNotFoundError: Om filen inte hittas
            ValueError: Om filen har ogiltigt format
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Promptmallsfilen {file_path} hittades inte")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_str = f.read()
            
            return cls.from_yaml(yaml_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Filen {file_path} innehåller ogiltig YAML: {str(e)}")
        except KeyError as e:
            raise ValueError(f"Filen {file_path} saknar nödvändigt fält: {e}")
    
    def __str__(self) -> str:
        """Strängrepresentation av mallen."""
        return f"{self.name} v{self.version}: {self.description}"