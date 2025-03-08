#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CorrectionPrompt.py - Specialiserad klass för att korrigera felaktiga LLM-svar

Denna modul innehåller klassen CorrectionPrompt, som är en specialiserad prompt
för att hjälpa LLM att korrigera tidigare felaktiga eller ofullständiga svar.

Egenskaper:
- Ordbok med feltyper och beskrivningar
- Förmåga att specificera exakta fel som behöver korrigeras
- Instruktioner för förbättring av specifika delar av svaret
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .PromptTemplate import PromptTemplate


class CorrectionPrompt(PromptTemplate):
    """
    Specialiserad promptmall för att korrigera felaktiga LLM-svar.
    
    Används när ett tidigare svar från LLM inte uppfyller kraven,
    för att ge modellen en chans att korrigera sina misstag.
    """
    
    def __init__(self, template: str, error_types: Dict[str, str], name: str = None, 
                 description: str = None, version: str = "1.0", tags: List[str] = None):
        """
        Initierar korrigeringsprompten.
        
        Args:
            template: Mall med platshållare
            error_types: Ordbok med feltyper och beskrivningar
            name: Namn på promptmallen
            description: Beskrivning av promptmallen
            version: Versionsstring
            tags: Lista med taggar för kategorisering
        """
        tags = tags or []
        if "correction" not in tags:
            tags.append("correction")
            
        super().__init__(template, name, description, version, tags)
        self.error_types = error_types
    
    def format(self, **kwargs) -> str:
        """
        Fyller mallen med värden och lägger till felinformation.
        
        Args:
            **kwargs: Nyckelord att ersätta i mallen
            
        Returns:
            str: Den formaterade prompten med felinformation
        """
        # Lägg till en beskrivning av feltyperna om den inte redan finns
        if 'error_descriptions' not in kwargs:
            error_desc = "\n".join([f"{err_type}: {desc}" for err_type, desc in self.error_types.items()])
            kwargs['error_descriptions'] = error_desc
        
        # Använd baspromptens format-metod
        return super().format(**kwargs)
    
    def for_errors(self, specific_errors: List[str]) -> 'CorrectionPrompt':
        """
        Anpassar prompten för specifika fel som har identifierats.
        
        Args:
            specific_errors: Lista med specifika felmeddelanden
            
        Returns:
            CorrectionPrompt: Ny promptmall anpassad för specifika fel
        """
        # Formatera felmeddelandena som bullet points
        errors_text = "\n".join([f"- {error}" for error in specific_errors])
        
        # Skapa en ny mall med specifika fel
        new_template = self.template.replace(
            "{errors}",
            errors_text
        )
        
        # Skapa en ny promptmall för de specifika felen
        return CorrectionPrompt(
            template=new_template,
            error_types=self.error_types,
            name=f"{self.name}_specific_errors",
            description=f"{self.description} (med {len(specific_errors)} specifika fel)",
            version=f"{self.version}+spec",
            tags=self.tags + ["specific_errors"]
        )
    
    def with_guidance(self, guidance_text: str) -> 'CorrectionPrompt':
        """
        Lägger till extra vägledning för att hjälpa LLM att korrigera felen.
        
        Args:
            guidance_text: Vägledningstext att lägga till
            
        Returns:
            CorrectionPrompt: Ny promptmall med extra vägledning
        """
        # Formatera vägledningen
        guidance_section = f"\n\nFÖR ATT LÖSA DESSA FEL, FÖLJ DESSA STEG:\n{guidance_text}\n\n"
        
        # Hitta lämpligt ställe att infoga vägledningen
        format_section = self.template.find("```json")
        
        if format_section > 0:
            # Lägg till vägledningen före JSON-exemplet
            new_template = self.template[:format_section] + guidance_section + self.template[format_section:]
        else:
            # Lägg till i slutet om inget JSON-exempel hittas
            new_template = self.template + guidance_section
        
        # Skapa en ny promptmall med vägledning
        return CorrectionPrompt(
            template=new_template,
            error_types=self.error_types,
            name=f"{self.name}_with_guidance",
            description=f"{self.description} (med extra vägledning)",
            version=f"{self.version}+guid",
            tags=self.tags + ["with_guidance"]
        )
    
    def with_exemplar_correction(self, original: str, corrected: str, explanation: str = None) -> 'CorrectionPrompt':
        """
        Lägger till ett exempel på hur en korrekt korrigering ser ut.
        
        Args:
            original: Ursprungligt felaktigt svar
            corrected: Korrekt korrigerat svar
            explanation: Förklaring av korrigeringarna (valfritt)
            
        Returns:
            CorrectionPrompt: Ny promptmall med exempelkorrigering
        """
        example_section = "\n\nHÄR ÄR ETT EXEMPEL PÅ EN KORREKT KORRIGERING:\n\n"
        example_section += "ORIGINAL:\n```\n" + original + "\n```\n\n"
        example_section += "KORRIGERAT:\n```\n" + corrected + "\n```\n\n"
        
        if explanation:
            example_section += "FÖRKLARING:\n" + explanation + "\n\n"
        
        # Hitta lämpligt ställe att infoga exemplet
        correction_instructions = self.template.find("Korrigera felen")
        
        if correction_instructions > 0:
            # Lägg till exemplet före korrigeringsinstruktionerna
            new_template = (
                self.template[:correction_instructions] + 
                example_section + 
                self.template[correction_instructions:]
            )
        else:
            # Lägg till i slutet om inga korrigeringsinstruktioner hittas
            new_template = self.template + example_section
        
        # Skapa en ny promptmall med exempelkorrigering
        return CorrectionPrompt(
            template=new_template,
            error_types=self.error_types,
            name=f"{self.name}_with_example_correction",
            description=f"{self.description} (med exempelkorrigering)",
            version=f"{self.version}+excor",
            tags=self.tags + ["with_example_correction"]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterar korrigeringsprompten till en ordbok för serialisering.
        
        Returns:
            Dict[str, Any]: Korrigeringsprompten som ordbok
        """
        data = super().to_dict()
        data["error_types"] = self.error_types
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrectionPrompt':
        """
        Skapar en korrigeringsprompt från en ordbok.
        
        Args:
            data: Ordbok med promptdata
            
        Returns:
            CorrectionPrompt: Den skapade korrigeringsprompten
        """
        # Extrahera feltyper
        error_types = data.pop("error_types", {})
        
        # Skapa korrigeringsprompt
        prompt = cls(
            template=data["template"],
            error_types=error_types,
            name=data.get("name"),
            description=data.get("description"),
            version=data.get("version", "1.0"),
            tags=data.get("tags", [])
        )
        
        # Ställ in ytterligare attribut om de finns
        if "creation_time" in data:
            prompt.creation_time = datetime.fromisoformat(data["creation_time"])
        
        if "last_modified" in data:
            prompt.last_modified = datetime.fromisoformat(data["last_modified"])
        
        if "usage_count" in data:
            prompt.usage_count = data["usage_count"]
        
        if "success_rate" in data:
            prompt.success_rate = data["success_rate"]
        
        if "average_latency_ms" in data:
            prompt.average_latency_ms = data["average_latency_ms"]
        
        return prompt